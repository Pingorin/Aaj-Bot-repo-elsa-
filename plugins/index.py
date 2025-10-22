import logging
import asyncio
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait
from pyrogram.errors.exceptions.bad_request_400 import ChannelInvalid, ChatAdminRequired, UsernameInvalid, UsernameNotModified
from info import ADMINS, LOG_CHANNEL, CHANNELS
from database.ia_filterdb import save_file
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils import temp, get_readable_time
import re, time

lock = asyncio.Lock()

# --- 1. Callback Handler for Database Selection (Unchanged) ---

@Client.on_callback_query(filters.regex(r'^index_db'))
async def select_db_and_confirm(bot, query):
    # Data format: index_db#<db_name>#<chat_id>#<lst_msg_id>#<skip>
    _, db_name, chat_id, lst_msg_id, skip = query.data.split("#")
    
    try:
        chat = await bot.get_chat(int(chat_id) if str(chat_id).lstrip('-').isnumeric() else chat_id)
    except Exception as e:
        await query.message.edit(f"Error fetching chat details: {e}")
        return

    buttons = [[
        InlineKeyboardButton('YES', callback_data=f'index#yes#{db_name}#{chat_id}#{lst_msg_id}#{skip}')
    ], [
        InlineKeyboardButton('CLOSE', callback_data='close_data'),
    ]]
    reply_markup = InlineKeyboardMarkup(buttons)
    
    await query.message.edit(
        f'**Confirmation:**\nDo you want to index files from {chat.title} into the **{db_name.upper()} Database**?\nTotal Messages: <code>{lst_msg_id}</code>', 
        reply_markup=reply_markup,
        parse_mode=enums.ParseMode.HTML
    )

# --- 2. Main Callback Handler for Indexing (Unchanged) ---

@Client.on_callback_query(filters.regex(r'^index'))
async def index_files(bot, query):
    data = query.data.split("#")
    ident = data[1]
    
    if ident == 'yes':
        try:
            db_name = data[2]
            chat = data[3]
            lst_msg_id = data[4]
            skip = data[5]
        except IndexError:
            await query.message.edit("Indexing Error: Corrupted callback data. Please restart the /index command.")
            return

        msg = query.message
        await msg.edit(f"<b>Indexing started for {db_name.upper()} DB... This will take time.</b>")
        try:
            chat_id = int(chat)
        except ValueError:
            chat_id = chat
            
        await index_files_to_db(int(lst_msg_id), chat_id, msg, bot, int(skip), db_name)
        
    elif ident == 'cancel':
        temp.CANCEL = True
        await query.message.edit("Trying to cancel Indexing...")

# --- 3. MODIFIED /index Command ---

@Client.on_message(filters.command('index') & filters.private & filters.incoming & filters.user(ADMINS))
async def send_for_index(bot, message):
    if lock.locked():
        return await message.reply('Wait until the previous process completes.')
    i = await message.reply("Forward the last message from the channel or send its link.")
    
    try:
        # MODIFIED: Replaced bot.listen with bot.wait_for_message
        msg = await bot.wait_for_message(
            chat_id=message.chat.id, 
            filters=filters.user(message.from_user.id), 
            timeout=300
        )
    except asyncio.TimeoutError:
        await i.delete()
        await message.reply("Timeout: No message received. Please try again.")
        return
    
    await i.delete()
        
    if msg.text and msg.text.startswith("https://t.me"):
        try:
            msg_link = msg.text.split("/")
            last_msg_id = int(msg_link[-1])
            if 'c' in msg_link[-2]:
                chat_id = int("-100" + msg_link[-2].split('c/')[-1])
            else:
                chat_id = msg_link[-2]
        except (ValueError, IndexError):
            await message.reply('Invalid message link!')
            return
    
    # MODIFIED: Replaced deprecated attributes with `msg.forward_origin`
    elif msg.forward_origin and msg.forward_origin.type == enums.MessageOriginType.CHANNEL:
        last_msg_id = msg.forward_origin.message_id
        chat_id = msg.forward_origin.sender_chat.username or msg.forward_origin.sender_chat.id
    
    else:
        await message.reply('This is not a forwarded message or a valid channel link.')
        return
        
    try:
        chat = await bot.get_chat(chat_id)
    except Exception as e:
        return await message.reply(f'An error occurred: {e}')
        
    if chat.type != enums.ChatType.CHANNEL:
        return await message.reply("I can only index channels.")
        
    s = await message.reply("Enter the number of messages to skip (e.g., `0` to start from the beginning).")
    
    try:
        # MODIFIED: Replaced bot.listen with bot.wait_for_message
        msg = await bot.wait_for_message(
            chat_id=message.chat.id, 
            filters=filters.user(message.from_user.id), 
            timeout=300
        )
    except asyncio.TimeoutError:
        await s.delete()
        await message.reply("Timeout: No skip number received. Please try again.")
        return

    await s.delete()
    
    try:
        skip = int(msg.text)
    except ValueError:
        return await message.reply("The number of messages to skip must be an integer.")
        
    db_buttons = [[
        InlineKeyboardButton('PRIMARY DB', callback_data=f'index_db#primary#{chat_id}#{last_msg_id}#{skip}'),
        InlineKeyboardButton('SECONDARY DB', callback_data=f'index_db#secondary#{chat_id}#{last_msg_id}#{skip}')
    ],[
        InlineKeyboardButton('CLOSE', callback_data='close_data'),
    ]]
    
    await message.reply(
        f'You are about to index files from: **{chat.title}**\nTotal Messages to process: <code>{last_msg_id}</code>\n\n**Please select the target database for saving the files:**', 
        reply_markup=InlineKeyboardMarkup(db_buttons),
        parse_mode=enums.ParseMode.HTML
    )


# --- 4. channel_info Command (Unchanged) ---

@Client.on_message(filters.command('channel'))
async def channel_info(bot, message):
    if message.from_user.id not in ADMINS:
        await message.reply('ᴏɴʟʏ ᴛʜᴇ ʙᴏᴛ ᴏᴡɴᴇʀ ᴄᴀɴ ᴜsᴇ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ... 😑')
        return
    ids = CHANNELS
    if not ids:
        return await message.reply("Not set CHANNELS")
    text = '**Indexed Channels:**\n\n'
    for id in ids:
        chat = await bot.get_chat(id)
        text += f'{chat.title}\n'
    text += f'\n**Total:** {len(ids)}'
    await message.reply(text)

# --- 5. Core Indexing Function (Unchanged) ---

async def index_files_to_db(lst_msg_id, chat, msg, bot, skip, db_name='primary'):
    start_time = time.time()
    total_files = 0
    duplicate = 0
    errors = 0
    deleted = 0
    no_media = 0
    unsupported = 0
    current = skip
    
    async with lock:
        try:
            async for message in bot.iter_messages(chat, lst_msg_id, skip):
                time_taken = get_readable_time(time.time()-start_time)
                
                if temp.CANCEL:
                    temp.CANCEL = False
                    await msg.edit(f"Successfully Cancelled!\nCompleted in {time_taken}\n\nSaved <code>{total_files}</code> files to {db_name.upper()} Database!\nDuplicate Files Skipped: <code>{duplicate}</code>\nDeleted Messages Skipped: <code>{deleted}</code>\nNon-Media messages skipped: <code>{no_media + unsupported}</code>\nUnsupported Media: <code>{unsupported}</code>\nErrors Occurred: <code>{errors}</code>")
                    return
                
                current += 1
                
                if current % 20 == 0:
                    btn = [[
                        InlineKeyboardButton('CANCEL', callback_data=f'index#cancel#{chat}#{lst_msg_id}#{skip}')
                    ]]
                    text = (f"Indexing in progress for **{db_name.upper()} DB**...\n\n"
                            f"Total messages scanned: <code>{current}</code>\n"
                            f"Total files saved: <code>{total_files}</code>\n"
                            f"Duplicate files skipped: <code>{duplicate}</code>\n"
                            f"Deleted messages skipped: <code>{deleted}</code>\n"
                            f"Non-Media messages skipped: <code>{no_media + unsupported}</code>\n"
                            f"Unsupported Media Types: <code>{unsupported}</code>\n"
                            f"Errors: <code>{errors}</code>")
                    try:
                        await msg.edit_text(text=text, reply_markup=InlineKeyboardMarkup(btn))
                    except FloodWait as e:
                        await asyncio.sleep(e.value)

                if message.empty:
                    deleted += 1
                    continue
                elif not message.media:
                    no_media += 1
                    continue
                elif message.media not in [enums.MessageMediaType.VIDEO, enums.MessageMediaType.DOCUMENT]:
                    unsupported += 1
                    continue
                    
                media = getattr(message, message.media.value, None)
                if not media:
                    unsupported += 1
                    continue
                
                media.caption = message.caption
                
                sts = await save_file(media, db_name=db_name)
                
                if sts == 'suc':
                    total_files += 1
                elif sts == 'dup':
                    duplicate += 1
                elif sts == 'err':
                    errors += 1
                    
        except Exception as e:
            logging.error(f'Index canceled for {db_name.upper()} DB due to Error: {e}', exc_info=True)
            await msg.reply(f'Index process stopped due to an error: {e}')
        else:
            time_taken = get_readable_time(time.time()-start_time)
            await msg.edit(f'Successfully saved <code>{total_files}</code> files to **{db_name.upper()} Database**!\nCompleted in {time_taken}\n\nDuplicate Files Skipped: <code>{duplicate}</code>\nDeleted Messages Skipped: <code>{deleted}</code>\nNon-Media messages skipped: <code>{no_media + unsupported}</code>\nUnsupported Media: <code>{unsupported}</code>\nErrors Occurred: <code>{errors}</code>')
            