from pyrogram import Client, filters, enums
from pyrogram.types import ChatJoinRequest
from database.users_chats_db import db
from info import ADMINS, REQ_SUB_CHANNEL_1, REQ_SUB_CHANNEL_2  # <-- Naye channels import karein

# Dono channels ki IDs ki ek list banayein
# Agar koi channel set nahi hai (None ya 0 hai) toh usey ignore kar dein
JOIN_REQ_CHANNELS = [chat_id for chat_id in [REQ_SUB_CHANNEL_1, REQ_SUB_CHANNEL_2] if chat_id]

@Client.on_chat_join_request(filters.chat(JOIN_REQ_CHANNELS))
async def join_reqs(client, message: ChatJoinRequest):
  """
  Jab bhi koi user JOIN_REQ_CHANNELS list wale channel par request bhejta hai,
  toh yeh function uski user_id aur channel_id ko database mein log karta hai.
  """
  if not await db.find_join_req(message.from_user.id, message.chat.id):
      await db.add_join_req(
          user_id=message.from_user.id, 
          chat_id=message.chat.id
      )

@Client.on_message(filters.command("delreq") & filters.private & filters.user(ADMINS))
async def del_requests(client, message):
    """
    Database se sabhi join request logs ko clear karta hai.
    """
    await db.del_join_req()    
    await message.reply("<b>⚙ ꜱᴜᴄᴄᴇꜱꜱғᴜʟʟʏ ꜱᴀʙʜɪ ᴊᴏɪɴ ʀᴇQᴜᴇꜱᴛ ʟᴏɢꜱ ᴅᴇʟᴇᴛᴇ ᴋᴀʀ ᴅɪʏᴇ ɢᴀʏᴇ.</b>")
