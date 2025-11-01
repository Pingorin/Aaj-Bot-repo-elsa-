from pyrogram import Client, filters, enums
from pyrogram.types import (
    ChatJoinRequest, ChatMemberUpdated, 
    InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
)
from pyrogram.errors import UserNotParticipant
from info import (
    AUTH_CHANNEL_1, AUTH_CHANNEL_2, 
    CHANNEL_1_NAME, CHANNEL_2_NAME, 
    CHANNEL_1_LINK, CHANNEL_2_LINK
)
from database.users_chats_db import db
from database.ia_filterdb import get_file_details
from utils import get_size
from info import FILE_CAPTION # Default caption

# --- Part 1: Join Request Handler ---
@Client.on_chat_join_request(filters.chat([AUTH_CHANNEL_1, AUTH_CHANNEL_2]))
async def handle_join_request(client: Client, request: ChatJoinRequest):
    """Jab user 'Request to Join' button dabata hai, use 'pending' DB mein add karein."""
    await db.add_pending_request(request.from_user.id, request.chat.id)

# --- Part 2: Member Update Handler ---
@Client.on_chat_member_updated(filters.chat([AUTH_CHANNEL_1, AUTH_CHANNEL_2]))
async def handle_member_update(client: Client, update: ChatMemberUpdated):
    """
    Jab user ka status badalta hai (approve, decline, cancel), 
    use 'pending' DB se remove karein.
    """
    
    # Sirf tabhi process karein jab new_chat_member available ho
    if not update.new_chat_member:
        return

    user_id = update.new_chat_member.user.id
    channel_id = update.chat.id
    
    # Agar naya status 'pending' NAHI hai, toh woh pending list se hat jayega
    if update.new_chat_member.status != enums.ChatMemberStatus.PENDING:
        await db.remove_pending_request(user_id, channel_id)

# --- Part 3: Fsub Check Logic (Helper Functions) ---

async def get_user_status(client: Client, user_id: int, channel_id: int):
    """
    User ka status check karein:
    1. Member hai? -> "MEMBER"
    2. Member nahi, par pending hai? -> "PENDING"
    3. Dono nahi? -> "NOT_JOINED"
    """
    try:
        member = await client.get_chat_member(channel_id, user_id)
        if member.status in [
            enums.ChatMemberStatus.MEMBER,
            enums.ChatMemberStatus.ADMINISTRATOR,
            enums.ChatMemberStatus.OWNER,
            enums.ChatMemberStatus.RESTRICTED
        ]:
            return "MEMBER"
        else:
            return "NOT_JOINED"
    except UserNotParticipant:
        if await db.is_user_pending(user_id, channel_id):
            return "PENDING"
        else:
            return "NOT_JOINED"
    except Exception as e:
        print(f"Error checking status for {user_id} in {channel_id}: {e}")
        return "NOT_JOINED"

async def build_fsub_check(client: Client, user_id: int, file_id: str):
    """
    Aapke "Mera Goal" waala core logic.
    Yeh function check karega aur 3 cheezein return karega:
    (status_code, message_text, buttons_markup)
    """
    
    status_c1 = await get_user_status(client, user_id, AUTH_CHANNEL_1)
    status_c2 = await get_user_status(client, user_id, AUTH_CHANNEL_2)

    failed_channels = []
    if status_c1 == "NOT_JOINED":
        failed_channels.append({
            "name": CHANNEL_1_NAME, 
            "link": CHANNEL_1_LINK
        })
        
    if status_c2 == "NOT_JOINED":
        failed_channels.append({
            "name": CHANNEL_2_NAME, 
            "link": CHANNEL_2_LINK
        })

    if not failed_channels:
        if status_c1 == "PENDING" or status_c2 == "PENDING":
            msg = "Aapki request mil gayi hai. Admin ke approve karte hi aapko channel mein add kar liya jayega. **Yeh rahi aapki file...**"
        else:
            msg = "Aap pehle se hi dono channels ke member hain. **Yeh rahi aapki file...**"
            
        return ("PASS", msg, None)
    
    else:
        buttons = []
        msg = "File lene ke liye, pehle inn channels ko join karne ki request karein:\n\n"
        
        for i, channel in enumerate(failed_channels, 1):
            msg += f"**{i}. {channel['name']}**\n"
            buttons.append(
                [InlineKeyboardButton(f"Request to Join {channel['name']}", url=channel['link'])]
            )
        
        msg += "\nRequest bhej kar 'Try Again' button dabayein."
        buttons.append(
            [InlineKeyboardButton("Try Again ♻️", callback_data=f"check_fsub#{file_id}")]
        )
        
        return ("FAIL", msg, InlineKeyboardMarkup(buttons))

# --- Part 4: Callback Handler (Issi file mein add kar dein) ---

@Client.on_callback_query(filters.regex(r"^check_fsub#"))
async def check_fsub_callback(client: Client, query: CallbackQuery):
    """
    'Try Again' button ka handler.
    """
    _, file_id = query.data.split("#")
    
    fsub_status, fsub_message, fsub_buttons = await build_fsub_check(
        client, query.from_user.id, file_id
    )

    if fsub_status == "FAIL":
        await query.answer("Aap abhi bhi channels se nahi jude hain.", show_alert=True)
        try:
            await query.message.edit_text(fsub_message, reply_markup=fsub_buttons)
        except:
            pass # Message not modified
        return

    # --- FSUB PASS - Ab file bhej do ---
    await query.answer("Success! File bhej raha hoon...", show_alert=True)
    
    files_ = await get_file_details(file_id)
    if not files_:
        await query.message.edit_text("Error: File not found.")
        return
        
    files = files_[0]
    
    f_caption = FILE_CAPTION.format(
        file_name = files.file_name,
        file_size = get_size(files.file_size),
        file_caption=files.caption
    )
    final_caption = f"**{fsub_message}**\n\n{f_caption}"
    
    btn = [[
        InlineKeyboardButton("✛ ᴡᴀᴛᴄʜ & ᴅᴏᴡɴʟᴏᴀᴅ ✛", callback_data=f'stream#{file_id}')
    ]]

    try:
        await client.send_cached_media(
            chat_id=query.from_user.id,
            file_id=file_id,
            caption=final_caption,
            protect_content=False, # Yahan default use kar rahe hain
            reply_markup=InlineKeyboardMarkup(btn)
        )
        # Purana "Try Again" message delete kar dein
        await query.message.delete()
    except Exception as e:
        print(e)
        await query.answer("Ek error aa gaya! Dobara try karein.", show_alert=True)
