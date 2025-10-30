from pyrogram import Client, filters, enums
from pyrogram.types import ChatJoinRequest
from database.users_chats_db import db
# REQ_AUTH_CHANNEL ko bhi import karein
from info import ADMINS, AUTH_CHANNEL, REQ_AUTH_CHANNEL 

# Bot ko batayein ki dono channels par nazar rakhe
@Client.on_chat_join_request(filters.chat([AUTH_CHANNEL, REQ_AUTH_CHANNEL]))
async def join_reqs(client, message: ChatJoinRequest):
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    # Request ko database mein log karein (naye function ke saath)
    try:
        await db.add_join_req(user_id, chat_id)
    except Exception as e:
        print(f"Join request log error: {e}")
    
    # Hum request ko approve ya decline nahi kar rahe hain
    # Taaki woh admin ke paas pending rahe

@Client.on_message(filters.command("delreq") & filters.private & filters.user(ADMINS))
async def del_requests(client, message):
    await db.del_join_req()    
    await message.reply("<b>⚙ ꜱᴜᴄᴄᴇꜱꜱғᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ ᴀʟʟ ᴊᴏɪɴ ʀᴇǫᴜᴇꜱᴛ ʟᴏɢꜱ</b>")
