import logging
from pyrogram.types import ChatMemberUpdated
from info import ADMINS, AUTH_CHANNEL, REFERRAL_GROUP_ID, REFERRAL_TARGET
from utils import temp
from Script import script
from pyrogram import Client, filters, enums
from pyrogram.types import ChatJoinRequest
from database.users_chats_db import db
from info import ADMINS, AUTH_CHANNEL

@Client.on_chat_join_request(filters.chat(AUTH_CHANNEL))
async def join_reqs(client, message: ChatJoinRequest):
  if not await db.find_join_req(message.from_user.id):
    await db.add_join_req(message.from_user.id)

@Client.on_message(filters.command("delreq") & filters.private & filters.user(ADMINS))
async def del_requests(client, message):
    await db.del_join_req()    
    await message.reply("<b>⚙ ꜱᴜᴄᴄᴇꜱꜱғᴜʟʟʏ ᴄʜᴀɴɴᴇʟ ʟᴇғᴛ ᴜꜱᴇʀꜱ ᴅᴇʟᴇᴛᴇᴅ</b>")

@Client.on_chat_member_updated(filters.chat(REFERRAL_GROUP_ID))
async def handle_group_join(client, update: ChatMemberUpdated):
    # We only care about users who JOINED
    if not update.new_chat_member or not update.invite_link:
        return

    new_user = update.new_chat_member.user

    # Ignore the bot itself
    if new_user.is_bot:
        return

    # Find the referrer by the invite link
    used_link = update.invite_link.invite_link
    referrer_data = await db.get_referrer_by_link(used_link)

    # Not one of our referral links
    if not referrer_data:
        return

    referrer_id = referrer_data['id']

    # User can't refer themselves
    if referrer_id == new_user.id:
        return

    try:
        # Check if the new user is *actually* new
        new_user_data = await db.get_user_data(new_user.id)

        if not new_user_data:
            # Brand new user, add them to DB with the referrer
            await db.add_user(new_user.id, new_user.first_name, referred_by=referrer_id)
        elif new_user_data.get('referred_by'):
            # User is already in DB and was *already* referred by someone
            # We don't give a point for this
            logging.info(f"{new_user.id} joined via {referrer_id} but was already referred.")
            return
        else:
            # User was in DB, but had no referrer. Let's assign the referrer.
            await db.col.update_one({'id': new_user.id}, {'$set': {'referred_by': referrer_id}})

        # If we are here, a valid referral happened. Increment count.
        new_count = await db.increment_referral_count(referrer_id)

        # Check if referrer reached the target
        if new_count >= REFERRAL_TARGET and not referrer_data.get('referral_access'):
            await db.grant_referral_access(referrer_id)
            await client.send_message(referrer_id, script.REFERRAL_TARGET_REACHED_MESSAGE.format(target=REFERRAL_TARGET))

        # Notify referrer
        elif not referrer_data.get('referral_access'):
            await client.send_message(referrer_id, script.REFERRAL_SUCCESS_MESSAGE.format(
                user_name=new_user.first_name,
                count=new_count,
                target=REFERRAL_TARGET
            ))

    except Exception as e:
        logging.error(f"Error handling group join referral: {e}")
      
