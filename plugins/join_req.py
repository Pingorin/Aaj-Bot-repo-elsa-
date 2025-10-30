from pyrogram import Client, filters, enums
from pyrogram.types import ChatJoinRequest
from database.users_chats_db import db
from info import ADMINS, AUTH_CHANNEL

@Client.on_chat_join_request(filters.chat(AUTH_CHANNEL))
async def join_reqs(client, message: ChatJoinRequest):
    user_id = message.from_user.id
    try:
        # Check karein ki user ne bot ko start kiya hai ya nahi
        if await db.is_user_exist(user_id):
            # Agar user database mein hai, to approve karein
            await message.approve()
        else:
            # Agar user ne bot start nahi kiya, to decline karein
            await message.decline()
    except Exception as e:
        print(f"Error handling join request for {user_id}: {e}")

@Client.on_message(filters.command("delreq") & filters.private & filters.user(ADMINS))
async def del_requests(client, message):
    # Yeh command abhi bhi purane logs ko clear karega
    await db.del_join_req()    
    
    # FIX: Reply message ko theek kiya gaya hai
    await message.reply("<b>⚙ ꜱᴜᴄᴄᴇꜱꜱғᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ ᴀʟʟ ᴘᴇɴᴅɪɴɢ ᴊᴏɪɴ ʀᴇǫᴜᴇꜱᴛ ʟᴏɢꜱ</b>")
