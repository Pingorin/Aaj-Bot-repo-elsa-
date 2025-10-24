from pyrogram import Client, filters, enums
from pyrogram.types import ChatJoinRequest, ChatMemberUpdated # Added ChatMemberUpdated
from database.users_chats_db import db
from info import ADMINS, AUTH_CHANNEL, AUTH_CHANNEL_2, REFERRAL_GROUP_ID, REFERRAL_TARGET # Added AUTH_CHANNEL_2, REFERRAL_GROUP_ID, REFERRAL_TARGET
import logging # Added logging
from utils import temp # Added temp
from Script import script # Added script

# Handler for the FIRST Auth Channel
@Client.on_chat_join_request(filters.chat(AUTH_CHANNEL) if AUTH_CHANNEL else filters.none)
async def join_reqs1(client, message: ChatJoinRequest):
  if not await db.has_requested_join(message.from_user.id):
    # Add user to the FIRST requests collection
    await db.req.insert_one({'id': message.from_user.id})
    logger.info(f"User {message.from_user.id} added to requests for AUTH_CHANNEL {AUTH_CHANNEL}")

# --- ADD HANDLER FOR THE SECOND AUTH CHANNEL ---
@Client.on_chat_join_request(filters.chat(AUTH_CHANNEL_2) if AUTH_CHANNEL_2 else filters.none)
async def join_reqs2(client, message: ChatJoinRequest):
  if not await db.has_requested_join_2(message.from_user.id):
    # Add user to the SECOND requests collection
    await db.req2.insert_one({'id': message.from_user.id})
    logger.info(f"User {message.from_user.id} added to requests2 for AUTH_CHANNEL_2 {AUTH_CHANNEL_2}")
# ---------------------------------------------

# Command to clear the FIRST requests collection
@Client.on_message(filters.command("delreq") & filters.private & filters.user(ADMINS))
async def del_requests1(client, message):
    count = await db.req.count_documents({})
    await db.req.drop()
    await message.reply(f"<b>✅ Successfully cleared {count} join requests for Channel 1.</b>")

# --- ADD COMMAND TO CLEAR SECOND REQUESTS ---
@Client.on_message(filters.command("delreq2") & filters.private & filters.user(ADMINS))
async def del_requests2(client, message):
    count = await db.req2.count_documents({})
    await db.req2.drop()
    await message.reply(f"<b>✅ Successfully cleared {count} join requests for Channel 2.</b>")
# --------------------------------------------

# --- ADDED REFERRAL GROUP JOIN HANDLER ---
@Client.on_chat_member_updated(filters.chat(REFERRAL_GROUP_ID) if REFERRAL_GROUP_ID else filters.none)
async def handle_group_join(client, update: ChatMemberUpdated):
    # We only care about users who JOINED via an invite link
    if not (update.new_chat_member and
            update.new_chat_member.status == enums.ChatMemberStatus.MEMBER and
            update.invite_link):
        return

    new_user = update.new_chat_member.user

    # Ignore bots
    if new_user.is_bot:
        return

    # Find the referrer by the invite link
    used_link = update.invite_link.invite_link
    referrer_data = await db.get_referrer_by_link(used_link)

    # Not one of our referral links
    if not referrer_data:
        logger.debug(f"User {new_user.id} joined group {REFERRAL_GROUP_ID} with non-referral link: {used_link}")
        return

    referrer_id = referrer_data['id']

    # User can't refer themselves
    if referrer_id == new_user.id:
        logger.info(f"User {new_user.id} tried to refer themselves.")
        return

    try:
        new_user_data = await db.get_user_data(new_user.id)

        referral_counted = False
        if not new_user_data:
            # Brand new user, add them to DB with the referrer
            await db.add_user(new_user.id, new_user.first_name, referred_by=referrer_id)
            referral_counted = True
        elif new_user_data.get('referred_by'):
            # User is already in DB and was *already* referred by someone
            logger.info(f"{new_user.id} joined via {referrer_id} but was already referred by {new_user_data.get('referred_by')}.")
            referral_counted = False # Don't give a point
        else:
            # User was in DB, but had no referrer. Assign the referrer.
            await db.col.update_one({'id': new_user.id}, {'$set': {'referred_by': referrer_id}})
            referral_counted = True

        # If a valid referral happened, increment count and notify.
        if referral_counted:
            new_count = await db.increment_referral_count(referrer_id)
            logger.info(f"Referral successful: {new_user.id} referred by {referrer_id}. New count: {new_count}")

            # Check if referrer reached the target and doesn't already have referral access flag set
            if new_count >= REFERRAL_TARGET and not referrer_data.get('referral_access'):
                await db.grant_referral_access(referrer_id) # Grants premium, sets flag
                await client.send_message(referrer_id, script.REFERRAL_TARGET_REACHED_MESSAGE.format(target=REFERRAL_TARGET))

            # Notify referrer if they haven't reached target yet
            elif not referrer_data.get('referral_access'): # Only notify if they dont have access yet
                await client.send_message(referrer_id, script.REFERRAL_SUCCESS_MESSAGE.format(
                    user_name=new_user.first_name,
                    count=new_count,
                    target=REFERRAL_TARGET
                ))

    except Exception as e:
        logging.error(f"Error handling group join referral for user {new_user.id} by {referrer_id}: {e}")
# ---------------------------------------------
