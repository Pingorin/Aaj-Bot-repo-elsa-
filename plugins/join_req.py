from pyrogram import Client, filters, enums
from pyrogram.types import ChatJoinRequest, ChatMemberUpdated
from database.users_chats_db import db
from info import ADMINS, AUTH_CHANNEL, AUTH_CHANNEL_2 # Dono channel import karein

import logging
logger = logging.getLogger(__name__)

# Component 1: Dono channels ke liye Join Requests ko log karein
@Client.on_chat_join_request(filters.chat([AUTH_CHANNEL, AUTH_CHANNEL_2]))
async def join_reqs(client, message: ChatJoinRequest):
    try:
        user_id = message.from_user.id
        chat_id = message.chat.id
        
        # Check karein (DB function ab chat_id bhi lega)
        if not await db.find_join_req(user_id, chat_id):
            # Add karein (DB function ab chat_id bhi lega)
            await db.add_join_req(user_id, chat_id)
            
    except Exception as e:
        logger.error(f"Error in join_reqs: {e}")

# Component 2: Dono channels par status update (Approve/Decline/Leave) par user ko DB se remove karein
@Client.on_chat_member_updated(filters.chat([AUTH_CHANNEL, AUTH_CHANNEL_2]))
async def member_update_handler(client, member: ChatMemberUpdated):
    try:
        user_id = member.from_user.id
        chat_id = member.chat.id

        # Agar user ka purana status PENDING tha
        if member.old_chat_member and member.old_chat_member.status == enums.ChatMemberStatus.PENDING:
            
            # Aur naya status PENDING *nahi* hai (matlab approve/decline/cancel hua)
            if member.new_chat_member.status != enums.ChatMemberStatus.PENDING:
                # User ko pending list se remove karein
                await db.remove_join_req(user_id, chat_id)
    
    except Exception as e:
        logger.error(f"Error in member_update_handler: {e}")


# Admin command (ab naye DB logic ke saath kaam karega)
@Client.on_message(filters.command("delreq") & filters.private & filters.user(ADMINS))
async def del_requests(client, message):
    await db.del_join_req()    
    # Text ko update kar diya hai
    await message.reply("<b>✅ ꜱᴜᴄᴄᴇꜱꜱғᴜʟʟʏ ᴄʟᴇᴀʀᴇD ᴛʜᴇ ᴘᴇɴᴅɪɴɢ ᴊᴏɪɴ ʀᴇǫᴜᴇꜱᴛ ʟᴏɢ.</b>")
