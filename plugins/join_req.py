from pyrogram import Client, filters, enums
from pyrogram.types import ChatJoinRequest, ChatMemberUpdated
from database.users_chats_db import db
from info import ADMINS, AUTH_CHANNEL, AUTH_CHANNEL_2  # <-- FIX: AUTH_CHANNEL_2 ko import karein
import asyncio
import logging  # <-- FIX: Logging import karein

logger = logging.getLogger(__name__)  # <-- FIX: Logger add karein

# --- FIX: Dono channels ki list banayein ---
# Yeh un channels ko filter kar dega jo info.py mein set nahi hain (None hain)
FSUB_CHANNELS = [ch for ch in [AUTH_CHANNEL, AUTH_CHANNEL_2] if ch]
# --- END FIX ---

@Client.on_chat_join_request(filters.chat(FSUB_CHANNELS))  # <-- FIX: List ka istemaal karein
async def join_reqs_handler(client: Client, message: ChatJoinRequest):
    """
    Component 1: Jab user join request bhejta hai,
    use database mein 'pending' list mein add kar do.
    """
    try:
        # Naya function istemaal karein jo user_id aur chat_id dono save karta hai
        await db.add_join_request(message.from_user.id, message.chat.id)
    except Exception as e:
        logger.error(f"Error saving join request: {e}")  # Print ko logger se badlein


@Client.on_chat_member_updated(filters.chat(FSUB_CHANNELS))  # <-- FIX: List ka istemaal karein
async def chat_member_update_handler(client: Client, message: ChatMemberUpdated):
    """
    Component 2: Database cleanup.
    Jab user ka status badle (approve, decline, cancel),
    use 'pending' list se remove kar do.
    """
    if not message.new_chat_member:
        return

    user_id = message.new_chat_member.user.id
    chat_id = message.chat.id

    try:
        # Jaise hi koi status update aaye, user ko pending list se hata do.
        # Kyunki ab woh ya toh member hai (approved) ya left (declined/cancelled).
        await db.remove_join_request(user_id, chat_id)
    except Exception as e:
        logger.error(f"Error cleaning up join request: {e}")  # Print ko logger se badlein


@Client.on_message(filters.command("delreq") & filters.private & filters.user(ADMINS))
async def del_requests(client, message):
    """
    Admin command: Pending list ko poori tarah clear karne ke liye.
    """
    await db.del_join_req()    
    await message.reply("<b>⚙️ ꜱᴜᴄᴄᴇꜱꜱғᴜʟʟʏ ᴘᴇɴᴅɪɴɢ ᴊᴏɪɴ ʀᴇQᴜᴇꜱᴛ ʟᴏɢꜱ ᴅᴇʟᴇᴛᴇᴅ</b>")
