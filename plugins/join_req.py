from pyrogram import Client, filters, enums
from pyrogram.types import ChatJoinRequest, ChatMemberUpdated # ChatMemberUpdated import karein
from database.users_chats_db import db
from info import ADMINS, AUTH_CHANNEL, REQ_AUTH_CHANNEL # Dono channel import karein

# Bot ko batayein ki dono channels par nazar rakhe
CHANNELS = [AUTH_CHANNEL, REQ_AUTH_CHANNEL]
if not CHANNELS:
    CHANNELS = []

@Client.on_chat_join_request(filters.chat(CHANNELS))
async def join_reqs(client, message: ChatJoinRequest):
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    # Request ko database mein log karein
    try:
        await db.add_join_req(user_id, chat_id)
    except Exception as e:
        print(f"Join request log error: {e}")
    
    # Hum request ko approve ya decline nahi kar rahe hain

@Client.on_message(filters.command("delreq") & filters.private & filters.user(ADMINS))
async def del_requests(client, message):
    await db.del_join_req()    
    await message.reply("<b>⚙ ꜱᴜᴄᴄᴇꜱꜱғᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ ᴀʟʟ ᴊᴏɪɴ ʀᴇǫᴜᴇꜱᴛ ʟᴏɢꜱ</b>")


# --- YEH HANDLER USER KE LEAVE KARNE PAR LOG DELETE KARTA HAI ---
@Client.on_chat_member_updated(filters.chat(CHANNELS))
async def member_update_handler(client, message: ChatMemberUpdated):
    user_id = message.from_user.id
    chat_id = message.chat.id

    try:
        # Check karein agar user ne leave kiya ya ban hua
        new_status = getattr(message.new_chat_member, "status", None)

        if new_status in [enums.ChatMemberStatus.LEFT, enums.ChatMemberStatus.BANNED]:
            # Database se uss user ka join request log delete karein
            await db.delete_specific_join_req(user_id, chat_id)
            
    except Exception as e:
        print(f"Error handling member update: {e}")
