from pyrogram import Client, filters, enums
from pyrogram.types import ChatJoinRequest, ChatMemberUpdated
from database.users_chats_db import db
# --- FIX: AUTH_CHANNEL_2 ko import kiya gaya ---
from info import ADMINS, AUTH_CHANNEL, AUTH_CHANNEL_2
import asyncio

# --- FIX: Dono channels ki ek list banayi gayi ---
# Yeh list unn sabhi channels ko include karegi jo None nahi hain
FSUB_CHANNELS = [ch for ch in [AUTH_CHANNEL, AUTH_CHANNEL_2] if ch]

@Client.on_chat_join_request(filters.chat(FSUB_CHANNELS))
async def join_reqs_handler(client: Client, message: ChatJoinRequest):
    """
    Component 1: Jab user kisi bhi Fsub channel par request bhejta hai,
    use database mein 'pending' list mein add kar do.
    """
    try:
        # Function pehle se hi message.chat.id ka istemaal kar raha hai,
        # isliye yeh multiple channels ke liye perfect kaam karega.
        await db.add_join_request(message.from_user.id, message.chat.id)
    except Exception as e:
        print(f"Error saving join request: {e}")


@Client.on_chat_member_updated(filters.chat(FSUB_CHANNELS))
async def chat_member_update_handler(client: Client, message: ChatMemberUpdated):
    """
    Component 2: Database cleanup.
    Jab user ka status kisi bhi Fsub channel par badalta hai,
    use 'pending' list se remove kar do.
    """
    if not message.new_chat_member:
        return

    user_id = message.new_chat_member.user.id
    chat_id = message.chat.id

    try:
        # Yeh bhi message.chat.id ka istemaal kar raha hai,
        # isliye yeh multiple channels ke liye sahi kaam karega.
        await db.remove_join_request(user_id, chat_id)
    except Exception as e:
        print(f"Error cleaning up join request: {e}")


@Client.on_message(filters.command("delreq") & filters.private & filters.user(ADMINS))
async def del_requests(client, message):
    """
    Admin command: Pending list ko poori tarah clear karne ke liye.
    (Yeh db.del_join_req() ko call karta hai, jo 'join_requests' collection ko clear karta hai)
    """
    await db.del_join_req()    
    await message.reply("<b>⚙️ ꜱᴜᴄᴄᴇꜱꜱғᴜʟʟʏ ᴘᴇɴᴅɪɴɢ ᴊᴏɪɴ ʀᴇQᴜᴇꜱᴛ ʟᴏɢꜱ ᴅᴇʟᴇᴛᴇᴅ</b>")

