import asyncio
import logging
import pytz
import re, time
import ast
import math
import string
import random
from datetime import datetime, timedelta
from pyrogram.errors.exceptions.bad_request_400 import MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty
from Script import script
import pyrogram
from info import (MAX_BTN, BIN_CHANNEL, USERNAME, URL, ADMINS, LANGUAGES, AUTH_CHANNEL,
                  SUPPORT_GROUP, IMDB, IMDB_TEMPLATE, LOG_CHANNEL, LOG_VR_CHANNEL, TUTORIAL,
                  FILE_CAPTION, SHORTENER_WEBSITE, SHORTENER_API, SHORTENER_WEBSITE2,
                  SHORTENER_API2, IS_PM_SEARCH, QR_CODE, DELETE_TIME, REFERRAL_TARGET,
                  REFERRAL_GROUP_ID, QUALITIES) # Added QUALITIES
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, InputMediaPhoto, ChatPermissions
from pyrogram import Client, filters, enums
from pyrogram.errors import (FloodWait, UserIsBlocked, MessageNotModified, PeerIdInvalid,
                           ChatAdminRequired) # Added MessageNotModified, ChatAdminRequired
from utils import temp, get_settings, is_check_admin, get_status, get_hash, get_name, get_size, save_group_settings, is_req_subscribed, get_poster, get_readable_time # Simplified get_status import
from database.users_chats_db import db
from database.ia_filterdb import Media, get_search_results, get_bad_files, get_file_details

lock = asyncio.Lock()

BUTTONS = {}
FILES_ID = {}
CAP = {}

@Client.on_message(filters.private & filters.text & filters.incoming)
async def pm_search(client, message):
    if IS_PM_SEARCH:
        # Simplified language check
        lang_keywords = LANGUAGES + ['english', 'gujarati'] # Ensure all languages are checked
        if any(lang in message.text.lower() for lang in lang_keywords):
            return await auto_filter(client, message)
        await auto_filter(client, message) # Filter anyway if no lang detected
    else:
        await message.reply_text("<b>⚠️ ꜱᴏʀʀʏ ɪ ᴄᴀɴ'ᴛ ᴡᴏʀᴋ ɪɴ ᴘᴍ</b>")

@Client.on_message(filters.group & filters.text & filters.incoming)
async def group_search(client, message):
    user_id = message.from_user.id if message.from_user else None
    chat_id = message.chat.id
    settings = await get_settings(chat_id)
    if settings["auto_filter"]:
        if not user_id:
            await message.reply("<b>🚨 ɪ'ᴍ ɴᴏᴛ ᴡᴏʀᴋɪɴɢ ғᴏʀ ᴀɴᴏɴʏᴍᴏᴜꜱ ᴀᴅᴍɪɴ!</b>")
            return

        lang_keywords = LANGUAGES + ['english', 'gujarati'] # Ensure all languages are checked
        if any(lang in message.text.lower() for lang in lang_keywords):
            return await auto_filter(client, message)

        if message.text.startswith("/"):
            return

        elif re.findall(r'https?://\S+|www\.\S+|t\.me/\S+', message.text):
            if await is_check_admin(client, message.chat.id, message.from_user.id):
                return
            try: # Try to delete user message first
                await message.delete()
            except ChatAdminRequired:
                pass # Bot is not admin, can't delete
            return await message.reply('<b>‼️ ᴡʜʏ ʏᴏᴜ ꜱᴇɴᴅ ʜᴇʀᴇ ʟɪɴᴋ\nʟɪɴᴋ ɴᴏᴛ ᴀʟʟᴏᴡᴇᴅ ʜᴇʀᴇ 🚫</b>')

        elif '@admin' in message.text.lower() or '@admins' in message.text.lower():
            if await is_check_admin(client, message.chat.id, message.from_user.id):
                return # Admins don't need to report
            admins = []
            owner_id = None
            async for member in client.get_chat_members(chat_id=message.chat.id, filter=enums.ChatMembersFilter.ADMINISTRATORS):
                if not member.user.is_bot:
                    admins.append(member.user.id)
                    if member.status == enums.ChatMemberStatus.OWNER:
                        owner_id = member.user.id # Store owner ID

            # Forward message only to the owner if found
            target_user_id = owner_id if owner_id else (admins[0] if admins else None)

            if target_user_id:
                forward_text = f"#Attention\n★ User: {message.from_user.mention}\n★ Group: {message.chat.title}\n\n"
                if message.reply_to_message:
                    try:
                        sent_msg = await message.reply_to_message.forward(target_user_id)
                        forward_text += f"★ <a href={message.reply_to_message.link}>Go to reported message</a>"
                        await sent_msg.reply_text(forward_text, disable_web_page_preview=True)
                    except Exception as e:
                        logging.warning(f"Could not forward report to owner/admin {target_user_id}: {e}")
                else:
                    try:
                        sent_msg = await message.forward(target_user_id)
                        forward_text += f"★ <a href={message.link}>Go to reporting message</a>"
                        await sent_msg.reply_text(forward_text, disable_web_page_preview=True)
                    except Exception as e:
                        logging.warning(f"Could not forward report to owner/admin {target_user_id}: {e}")

            # Notify in group with hidden mentions to all admins
            hidden_mentions = ''.join([f'[\u2064](tg://user?id={admin_id})' for admin_id in admins])
            await message.reply_text('<code>Report sent to admins.</code>' + hidden_mentions)
            return
        else:
            await auto_filter(client, message)
    else:
        k = await message.reply_text('<b>⚠️ ᴀᴜᴛᴏ ғɪʟᴛᴇʀ ᴍᴏᴅᴇ ɪꜱ ᴏғғ...</b>')
        await asyncio.sleep(10)
        try:
            await k.delete()
        except: pass
        try:
            await message.delete()
        except: pass

@Client.on_callback_query(filters.regex(r"^next"))
async def next_page(bot, query):
    ident, req, key, offset = query.data.split("_")
    if int(req) not in [query.from_user.id, 0]:
        return await query.answer(script.ALRT_TXT.format(query.from_user.first_name), show_alert=True)
    try:
        offset = int(offset)
    except:
        offset = 0
    search = BUTTONS.get(key)
    cap = CAP.get(key)
    if not search:
        await query.answer(script.OLD_ALRT_TXT.format(query.from_user.first_name),show_alert=True)
        return
    files, n_offset, total = await get_search_results(search, offset=offset)
    try:
        n_offset = int(n_offset)
    except:
        n_offset = 0
    if not files:
         await query.answer("No more files found for this query.", show_alert=True) # Notify user
         return
    temp.FILES_ID[key] = files

    batch_ids = files # Use the fetched files
    temp.FILES_ID[f"{query.message.chat.id}-{query.id}"] = batch_ids
    batch_link = f"batchfiles#{query.message.chat.id}#{query.id}#{query.from_user.id}"

    settings = await get_settings(query.message.chat.id)
    reqnxt  = query.from_user.id # Use actual user ID
    temp.CHAT[query.from_user.id] = query.message.chat.id
    del_msg = f"\n\n<b>⚠️ ᴛʜɪs ᴍᴇssᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ ᴀꜰᴛᴇʀ <code>{get_readable_time(DELETE_TIME)}</code> ᴛᴏ ᴀᴠᴏɪᴅ ᴄᴏᴘʏʀɪɢʜᴛ ɪssᴜᴇs</b>" if settings["auto_delete"] else ''
    links = ""
    btn = [] # Initialize btn

    if settings["link"]:
        for file_num, file in enumerate(files, start=offset+1):
            links += f"""<b>\n\n{file_num}. <a href=https://t.me/{temp.U_NAME}?start=file_{query.message.chat.id}_{file.file_id}>[{get_size(file.file_size)}] {' '.join(filter(lambda x: not x.startswith('[') and not x.startswith('@') and not x.startswith('www.'), file.file_name.split()))}</a></b>"""
    else:
        btn = [[InlineKeyboardButton(text=f"🔗 {get_size(file.file_size)}≽ {get_name(file.file_name)}", url=f'https://telegram.dog/{temp.U_NAME}?start=file_{query.message.chat.id}_{file.file_id}'),]
                for file in files
              ]

    # FIX: Insert buttons correctly
    btn.insert(0, [
        InlineKeyboardButton("📰 ʟᴀɴɢᴜᴀɢᴇs", callback_data=f"languages#{key}#{offset}#{req}"),
        InlineKeyboardButton("🎞️ ǫᴜᴀʟɪᴛʏ", callback_data=f"qualities#{key}#{offset}#{req}")
    ])
    btn.insert(0, [
        InlineKeyboardButton("♻️ sᴇɴᴅ ᴀʟʟ", callback_data=batch_link),
        InlineKeyboardButton("🥇ʙᴜʏ🥇", url=f"https://t.me/{temp.U_NAME}?start=buy_premium"),
    ])

    # ADDED BUTTONS (Ensure alignment)
    btn.append(
        [InlineKeyboardButton("🤔 ʜᴏᴡ ᴛᴏ ᴅᴏᴡɴʟᴏᴀᴅ 🤔", url=settings['tutorial'])]
    )
    btn.append(
        [InlineKeyboardButton(script.REFERRAL_BUTTON_TEXT, callback_data='referral')]
    )

    # Pagination logic
    if 0 < offset <= int(MAX_BTN):
        off_set = 0
    elif offset == 0:
        off_set = None
    else:
        off_set = offset - int(MAX_BTN)

    pagination_buttons = []
    if off_set is not None:
         pagination_buttons.append(InlineKeyboardButton("⪻ ʙᴀᴄᴋ", callback_data=f"next_{req}_{key}_{off_set}"))

    pagination_buttons.append(InlineKeyboardButton(f"ᴘɢ {math.ceil(int(offset) / int(MAX_BTN)) + 1} / {math.ceil(total / int(MAX_BTN))}", callback_data="pages"))

    if n_offset != 0:
        pagination_buttons.append(InlineKeyboardButton("ɴᴇxᴛ ⪼", callback_data=f"next_{req}_{key}_{n_offset}"))

    if pagination_buttons:
         btn.append(pagination_buttons)


    # Edit the message
    edit_caption = cap + links + del_msg if settings["link"] else cap + del_msg # Adjust caption based on link mode
    try:
        if settings["link"]:
             await query.message.edit_text(edit_caption, disable_web_page_preview=True, parse_mode=enums.ParseMode.HTML, reply_markup=InlineKeyboardMarkup(btn))
        else:
             # If not link mode, edit caption if there's a photo, otherwise edit reply markup
             if query.message.photo:
                  await query.message.edit_caption(caption=edit_caption, reply_markup=InlineKeyboardMarkup(btn), parse_mode=enums.ParseMode.HTML)
             else:
                  await query.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(btn))
    except MessageNotModified:
        pass # Ignore if content is the same
    except Exception as e:
         logging.error(f"Error editing message in next_page: {e}")
    await query.answer()

@Client.on_callback_query(filters.regex(r"^languages#"))
async def languages_cb_handler(client: Client, query: CallbackQuery):
    _, key, offset, req = query.data.split("#")
    if int(req) != query.from_user.id:
        return await query.answer(script.ALRT_TXT, show_alert=True)
    # Allow in PM as well
    # if query.message.chat.type == enums.ChatType.PRIVATE:
    #     return await query.answer('ᴛʜɪs ʙᴜᴛᴛᴏɴ ᴏɴʟʏ ᴡᴏʀᴋ ɪɴ ɢʀᴏᴜᴘ', show_alert=True)
    btn = [[
        InlineKeyboardButton(text=lang.title(), callback_data=f"lang_search#{lang.lower()}#{key}#0#{offset}#{req}"),
    ]
        for lang in LANGUAGES
    ]
    btn.append([InlineKeyboardButton(text="⪻ ʙᴀᴄᴋ ᴛᴏ ᴍᴀɪɴ ᴘᴀɢᴇ", callback_data=f"next_{req}_{key}_{offset}")])
    try:
        await query.message.edit_text("<b>ɪɴ ᴡʜɪᴄʜ ʟᴀɴɢᴜᴀɢᴇ ʏᴏᴜ ᴡᴀɴᴛ, ᴄʜᴏᴏsᴇ ʜᴇʀᴇ 👇</b>", reply_markup=InlineKeyboardMarkup(btn))
    except MessageNotModified:
        await query.answer() # Still answer the query
    except Exception as e:
        logging.error(f"Error in languages_cb_handler: {e}")

# Removed redundant 'return' and sleep/delete logic

@Client.on_callback_query(filters.regex(r"^lang_search#"))
async def lang_search(client: Client, query: CallbackQuery):
    _, lang, key, offset, orginal_offset, req = query.data.split("#")
    if int(req) != query.from_user.id:
        return await query.answer(script.ALRT_TXT, show_alert=True)
    offset = int(offset)
    search = BUTTONS.get(key)
    cap = CAP.get(key)
    if not search:
        await query.answer(script.OLD_ALRT_TXT.format(query.from_user.first_name),show_alert=True)
        return
    search = search.replace("_", " ")
    # Use the 'lang' parameter in get_search_results
    files, n_offset, total = await get_search_results(search, max_results=int(MAX_BTN), offset=offset, lang=lang)
    try:
        n_offset = int(n_offset)
    except:
        n_offset = 0

    # No need to filter again here, get_search_results did it
    # files = [file for file in files if re.search(lang, file.file_name, re.IGNORECASE)]

    if not files:
        await query.answer(f"sᴏʀʀʏ '{lang.title()}' ʟᴀɴɢᴜᴀɢᴇ ꜰɪʟᴇs ɴᴏᴛ ꜰᴏᴜɴᴅ 😕", show_alert=1)
        return

    batch_ids = files
    temp.FILES_ID[f"{query.message.chat.id}-{query.id}"] = batch_ids
    batch_link = f"batchfiles#{query.message.chat.id}#{query.id}#{query.from_user.id}"

    reqnxt = query.from_user.id # Use actual ID
    settings = await get_settings(query.message.chat.id)
    group_id = query.message.chat.id
    temp.CHAT[query.from_user.id] = query.message.chat.id
    del_msg = f"\n\n<b>⚠️ ᴛʜɪs ᴍᴇssᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ ᴀꜰᴛᴇʀ <code>{get_readable_time(DELETE_TIME)}</code> ᴛᴏ ᴀᴠᴏɪᴅ ᴄᴏᴘʏʀɪɢʜᴛ ɪssᴜᴇs</b>" if settings["auto_delete"] else ''
    links = ""
    btn = [] # Initialize btn

    if settings["link"]:
        for file_num, file in enumerate(files, start=offset+1):
            links += f"""<b>\n\n{file_num}. <a href=https://t.me/{temp.U_NAME}?start=file_{query.message.chat.id}_{file.file_id}>[{get_size(file.file_size)}] {' '.join(filter(lambda x: not x.startswith('[') and not x.startswith('@') and not x.startswith('www.'), file.file_name.split()))}</a></b>"""
    else:
        btn = [[
                InlineKeyboardButton(text=f"🔗 {get_size(file.file_size)}≽ {get_name(file.file_name)}", url=f'https://telegram.dog/{temp.U_NAME}?start=file_{query.message.chat.id}_{file.file_id}'),] # Changed callback_data to url
                   for file in files
              ]

    btn.insert(0, [
            InlineKeyboardButton("♻️ sᴇɴᴅ ᴀʟʟ ♻️", callback_data=batch_link),
            InlineKeyboardButton("🥇ʙᴜʏ🥇", url=f"https://t.me/{temp.U_NAME}?start=buy_premium") # Corrected URL
        ])
    btn.append(
        [InlineKeyboardButton("🤔 ʜᴏᴡ ᴛᴏ ᴅᴏᴡɴʟᴏᴀᴅ 🤔", url=settings['tutorial'])]
    )
    btn.append(
        [InlineKeyboardButton(script.REFERRAL_BUTTON_TEXT, callback_data='referral')]
    )

    # Simplified Pagination
    pagination_buttons = []
    if offset > 0:
        pagination_buttons.append(InlineKeyboardButton("⪻ ʙᴀᴄᴋ", callback_data=f"lang_search#{lang}#{key}#{offset- int(MAX_BTN)}#{orginal_offset}#{req}"))

    if total > offset + int(MAX_BTN): # Check if there are more pages
         pagination_buttons.append(InlineKeyboardButton(f"{math.ceil(offset / int(MAX_BTN)) + 1}/{math.ceil(total / int(MAX_BTN))}", callback_data="pages"))
         pagination_buttons.append(InlineKeyboardButton("ɴᴇxᴛ ⪼", callback_data=f"lang_search#{lang}#{key}#{n_offset}#{orginal_offset}#{req}"))
    elif total > int(MAX_BTN): # Last page has more than MAX_BTN files total
         pagination_buttons.append(InlineKeyboardButton(f"{math.ceil(offset / int(MAX_BTN)) + 1}/{math.ceil(total / int(MAX_BTN))}", callback_data="pages"))
    elif not pagination_buttons: # No Back button and no Next button needed
         pagination_buttons.append(InlineKeyboardButton("🚸 ɴᴏ ᴍᴏʀᴇ ᴘᴀɢᴇs 🚸", callback_data="buttons"))


    if pagination_buttons:
        btn.append(pagination_buttons)

    btn.append([
        InlineKeyboardButton(text="⪻ ʙᴀᴄᴋ ᴛᴏ ᴍᴀɪɴ ᴘᴀɢᴇ", callback_data=f"next_{req}_{key}_{orginal_offset}"),])

    # Edit the message
    edit_caption = cap + links + del_msg if settings["link"] else cap + del_msg
    try:
        if settings["link"]:
             await query.message.edit_text(edit_caption, disable_web_page_preview=True, parse_mode=enums.ParseMode.HTML, reply_markup=InlineKeyboardMarkup(btn))
        else:
             # If not link mode, edit caption if there's a photo, otherwise edit reply markup
             if query.message.photo:
                  await query.message.edit_caption(caption=edit_caption, reply_markup=InlineKeyboardMarkup(btn), parse_mode=enums.ParseMode.HTML)
             else:
                  await query.message.edit_text(text=edit_caption, reply_markup=InlineKeyboardMarkup(btn), disable_web_page_preview=True, parse_mode=enums.ParseMode.HTML) # Use edit_text for text messages
    except MessageNotModified:
        await query.answer()
    except Exception as e:
         logging.error(f"Error editing message in lang_search: {e}")
         await query.answer("An error occurred while updating results.", show_alert=True)
    # Removed redundant return and edit_message_reply_markup

# --- NEW QUALITY FILTER HANDLERS ---
@Client.on_callback_query(filters.regex(r"^qualities#"))
async def qualities_cb_handler(client: Client, query: CallbackQuery):
    _, key, offset, req = query.data.split("#")
    if int(req) != query.from_user.id:
        return await query.answer(script.ALRT_TXT, show_alert=True)
    # Allow in PM
    # if query.message.chat.type == enums.ChatType.PRIVATE:
    #     return await query.answer('ᴛʜɪs ʙᴜᴛᴛᴏɴ ᴏɴʟʏ ᴡᴏʀᴋ ɪɴ ɢʀᴏᴜᴘ', show_alert=True)

    btn = [[
        InlineKeyboardButton(text=quality, callback_data=f"qual_search#{quality}#{key}#0#{offset}#{req}"),
    ]
        for quality in QUALITIES
    ]
    btn.append([InlineKeyboardButton(text="⪻ ʙᴀᴄᴋ ᴛᴏ ᴍᴀɪɴ ᴘᴀɢᴇ", callback_data=f"next_{req}_{key}_{offset}")])
    try:
        await query.message.edit_text("<b>Select your desired quality: 👇</b>", reply_markup=InlineKeyboardMarkup(btn))
    except MessageNotModified:
        await query.answer()
    except Exception as e:
        logging.error(f"Error in qualities_cb_handler: {e}")
        await query.answer("An error occurred.", show_alert=True)


@Client.on_callback_query(filters.regex(r"^qual_search#"))
async def quality_search(client: Client, query: CallbackQuery):
    _, quality, key, offset, orginal_offset, req = query.data.split("#")
    if int(req) != query.from_user.id:
        return await query.answer(script.ALRT_TXT, show_alert=True)

    offset = int(offset)
    search = BUTTONS.get(key)
    cap = CAP.get(key)
    if not search:
        await query.answer(script.OLD_ALRT_TXT.format(query.from_user.first_name),show_alert=True)
        return

    search = search.replace("_", " ")
    files, n_offset, total = await get_search_results(search, max_results=int(MAX_BTN), offset=offset, quality=quality)
    try:
        n_offset = int(n_offset)
    except:
        n_offset = 0

    if not files:
        await query.answer(f"Sorry, no files found for '{quality}' quality. 😕", show_alert=1)
        return

    batch_ids = files
    temp.FILES_ID[f"{query.message.chat.id}-{query.id}"] = batch_ids
    batch_link = f"batchfiles#{query.message.chat.id}#{query.id}#{query.from_user.id}"

    reqnxt = query.from_user.id # Use actual ID
    settings = await get_settings(query.message.chat.id)
    group_id = query.message.chat.id
    temp.CHAT[query.from_user.id] = query.message.chat.id
    del_msg = f"\n\n<b>⚠️ ᴛʜɪs ᴍᴇssᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ ᴀꜰᴛᴇʀ <code>{get_readable_time(DELETE_TIME)}</code> ᴛᴏ ᴀᴠᴏɪᴅ ᴄᴏᴘʏʀɪɢʜᴛ ɪssᴜᴇs</b>" if settings["auto_delete"] else ''
    links = ""
    btn = [] # Initialize btn

    if settings["link"]:
        for file_num, file in enumerate(files, start=offset+1):
            links += f"""<b>\n\n{file_num}. <a href=https://t.me/{temp.U_NAME}?start=file_{query.message.chat.id}_{file.file_id}>[{get_size(file.file_size)}] {' '.join(filter(lambda x: not x.startswith('[') and not x.startswith('@') and not x.startswith('www.'), file.file_name.split()))}</a></b>"""
    else:
        btn = [[
                InlineKeyboardButton(text=f"🔗 {get_size(file.file_size)}≽ {get_name(file.file_name)}", url=f'https://telegram.dog/{temp.U_NAME}?start=file_{query.message.chat.id}_{file.file_id}'),] # Changed callback_data to url
                   for file in files
              ]

    btn.insert(0, [
            InlineKeyboardButton("♻️ sᴇɴᴅ ᴀʟʟ ♻️", callback_data=batch_link),
            InlineKeyboardButton("🥇ʙᴜʏ🥇", url=f"https://t.me/{temp.U_NAME}?start=buy_premium") # Corrected URL
        ])
    btn.append(
        [InlineKeyboardButton("🤔 ʜᴏᴡ ᴛᴏ ᴅᴏᴡɴʟᴏᴀᴅ 🤔", url=settings['tutorial'])]
    )
    btn.append(
        [InlineKeyboardButton(script.REFERRAL_BUTTON_TEXT, callback_data='referral')]
    )

    # Simplified Pagination
    pagination_buttons = []
    if offset > 0:
        pagination_buttons.append(InlineKeyboardButton("⪻ ʙᴀᴄᴋ", callback_data=f"qual_search#{quality}#{key}#{offset- int(MAX_BTN)}#{orginal_offset}#{req}"))

    if total > offset + int(MAX_BTN): # Check if there are more pages
         pagination_buttons.append(InlineKeyboardButton(f"{math.ceil(offset / int(MAX_BTN)) + 1}/{math.ceil(total / int(MAX_BTN))}", callback_data="pages"))
         pagination_buttons.append(InlineKeyboardButton("ɴᴇxᴛ ⪼", callback_data=f"qual_search#{quality}#{key}#{n_offset}#{orginal_offset}#{req}"))
    elif total > int(MAX_BTN): # Last page has more than MAX_BTN files total
         pagination_buttons.append(InlineKeyboardButton(f"{math.ceil(offset / int(MAX_BTN)) + 1}/{math.ceil(total / int(MAX_BTN))}", callback_data="pages"))
    elif not pagination_buttons: # No Back button and no Next button needed
         pagination_buttons.append(InlineKeyboardButton("🚸 ɴᴏ ᴍᴏʀᴇ ᴘᴀɢᴇs 🚸", callback_data="buttons"))

    if pagination_buttons:
        btn.append(pagination_buttons)

    btn.append([
        InlineKeyboardButton(text="⪻ ʙᴀᴄᴋ ᴛᴏ ᴍᴀɪɴ ᴘᴀɢᴇ", callback_data=f"next_{req}_{key}_{orginal_offset}"),])

    # Edit the message
    edit_caption = cap + links + del_msg if settings["link"] else cap + del_msg
    try:
        if settings["link"]:
             await query.message.edit_text(edit_caption, disable_web_page_preview=True, parse_mode=enums.ParseMode.HTML, reply_markup=InlineKeyboardMarkup(btn))
        else:
             if query.message.photo:
                  await query.message.edit_caption(caption=edit_caption, reply_markup=InlineKeyboardMarkup(btn), parse_mode=enums.ParseMode.HTML)
             else:
                  await query.message.edit_text(text=edit_caption, reply_markup=InlineKeyboardMarkup(btn), disable_web_page_preview=True, parse_mode=enums.ParseMode.HTML)
    except MessageNotModified:
        await query.answer()
    except Exception as e:
         logging.error(f"Error editing message in quality_search: {e}")
         await query.answer("An error occurred while updating results.", show_alert=True)
    # Removed redundant return

# --- END NEW QUALITY FILTER HANDLERS ---

@Client.on_callback_query(filters.regex(r"^spol"))
async def advantage_spoll_choker(bot, query):
    _, id, user = query.data.split('#')
    if int(user) != 0 and query.from_user.id != int(user):
        return await query.answer(script.ALRT_TXT, show_alert=True)
    movie = await get_poster(id, id=True)
    search = movie.get('title') if movie else None # Handle case where movie is None
    if not search:
        await query.answer('Could not find movie details.', show_alert=True)
        return
    await query.answer('ᴄʜᴇᴄᴋɪɴɢ ɪɴ ᴍʏ ᴅᴀᴛᴀʙᴀꜱᴇ 🌚')
    files, offset, total_results = await get_search_results(search)
    if files:
        k = (search, files, offset, total_results)
        await auto_filter(bot, query, k) # Pass query, not message
    else:
        k = await query.message.edit(script.NO_RESULT_TXT)
        await asyncio.sleep(60)
        try:
             await k.delete()
        except: pass
        try:
            # Delete the original message with buttons if it exists
            if query.message.reply_to_message:
                 await query.message.reply_to_message.delete()
        except: pass


@Client.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):
    # --- Moved regex filters above this handler ---

    if query.data == "close_data":
        try:
            user_id_to_check = query.message.reply_to_message.from_user.id
        except AttributeError:
             user_id_to_check = query.message.from_user.id # Fallback if no reply_to_message

        # Allow admins to close any message, allow users to close their own requests
        is_admin = await is_check_admin(client, query.message.chat.id, query.from_user.id)

        if query.from_user.id == user_id_to_check or is_admin:
            await query.answer("ᴛʜᴀɴᴋs ꜰᴏʀ ᴄʟᴏsᴇ 🙈")
            await query.message.delete()
            try:
                # Also delete the original trigger message if possible (e.g., the user's search query)
                if query.message.reply_to_message:
                    await query.message.reply_to_message.delete()
            except Exception as e:
                logging.debug(f"Could not delete reply_to_message: {e}")
        else:
            return await query.answer(script.ALRT_TXT, show_alert=True) # Use the correct alert text

    elif query.data == "delallcancel":
        userid = query.from_user.id
        chat_type = query.message.chat.type
        # Allow bot owner or chat owner/admin to cancel
        is_owner_or_admin = str(userid) in ADMINS # Check if bot owner
        if chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
            try:
                 st = await client.get_chat_member(query.message.chat.id, userid)
                 if st.status in [enums.ChatMemberStatus.OWNER, enums.ChatMemberStatus.ADMINISTRATOR]:
                      is_owner_or_admin = True
            except Exception as e:
                 logging.warning(f"Could not get chat member status for cancel: {e}")

        if is_owner_or_admin:
             await query.message.delete()
             try:
                  await query.message.reply_to_message.delete()
             except: pass
        else:
             await query.answer(script.ALRT_TXT, show_alert=True) # Use correct alert text


    elif query.data.startswith("checksub"):
        if not query.message.chat.id: # Ensure chat ID exists
             logging.warning("Chat ID missing in checksub callback.")
             return await query.answer("Error processing request.", show_alert=True)

        ident, file_id = query.data.split("#")
        settings = await get_settings(query.message.chat.id) # Use chat_id from message

        if AUTH_CHANNEL and not await is_req_subscribed(client, query):
            await query.answer("ɪ ʟɪᴋᴇ ʏᴏᴜʀ sᴍᴀʀᴛɴᴇss ʙᴜᴛ ᴅᴏɴ'ᴛ ʙᴇ ᴏᴠᴇʀsᴍᴀʀᴛ 😒\nꜰɪʀsᴛ ᴊᴏɪɴ ᴏᴜʀ ᴜᴘᴅᴀᴛᴇs ᴄʜᴀɴɴᴇʟ 😒", show_alert=True)
            return

        files_ = await get_file_details(file_id)
        if not files_:
            return await query.answer('ɴᴏ sᴜᴄʜ ꜰɪʟᴇ ᴇxɪsᴛs 🚫', show_alert=True) # show alert
        files = files_[0]
        CAPTION = settings['caption']
        f_caption = CAPTION.format(
            file_name = files.file_name,
            file_size = get_size(files.file_size),
            file_caption = files.caption if files.caption else "" # Handle None caption
        )
        try:
             await client.send_cached_media(
                 chat_id=query.from_user.id,
                 file_id=file_id,
                 caption=f_caption,
                 protect_content=settings['file_secure'], # Use setting
                 # Removed reply_markup as requested in previous steps
                 # reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('❌ ᴄʟᴏsᴇ ❌', callback_data='close_data')]])
             )
             await query.message.delete() # Delete the 'Try Again' message
        except Exception as e:
             logging.error(f"Error sending file in checksub: {e}")
             await query.answer("Could not send the file. Please try again.", show_alert=True)


    elif query.data.startswith("stream"):
        user_id = query.from_user.id
        # Allow referral access OR premium access
        if not await db.has_premium_access(user_id) and not await db.check_referral_access(user_id):
            d=await query.message.reply("<b>💔 ᴛʜɪꜱ ғᴇᴀᴛᴜʀᴇ ɪꜱ ᴏɴʟʏ ғᴏʀ ᴘʀᴇᴍɪᴜᴍ/ʀᴇғᴇʀʀᴀʟ ᴜꜱᴇʀꜱ.\n\n🪙 /plan ᴛᴏ ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ\n🔗 /start ᴛᴏ ɢᴇᴛ ʀᴇғᴇʀʀᴀʟ ʟɪɴᴋ</b>")
            await asyncio.sleep(10)
            try:
                await d.delete()
            except: pass
            return
        file_id = query.data.split('#', 1)[1]
        try:
             AKS = await client.send_cached_media(
                 chat_id=BIN_CHANNEL,
                 file_id=file_id)
             online = f"https://{URL}/watch/{AKS.id}?hash={get_hash(AKS)}"
             download = f"https://{URL}/{AKS.id}?hash={get_hash(AKS)}"
             btn= [[
                 InlineKeyboardButton("ᴡᴀᴛᴄʜ ᴏɴʟɪɴᴇ", url=online),
                 InlineKeyboardButton("ꜰᴀsᴛ ᴅᴏᴡɴʟᴏᴀᴅ", url=download)
             ],[
                 InlineKeyboardButton('❌ ᴄʟᴏsᴇ ❌', callback_data='close_data')
             ]]
             await query.edit_message_reply_markup(
                 reply_markup=InlineKeyboardMarkup(btn)
             )
        except Exception as e:
             logging.error(f"Error generating stream links: {e}")
             await query.answer("Could not generate streaming links.", show_alert=True)


    elif query.data == "buttons":
        await query.answer("ɴᴏ ᴍᴏʀᴇ ᴘᴀɢᴇs 😊", show_alert=True)

    elif query.data == "pages":
        await query.answer("ᴛʜɪs ɪs ᴘᴀɢᴇs ʙᴜᴛᴛᴏɴ 😅")

    elif query.data.startswith("lang_art"): # Assuming this might be used elsewhere
        _, lang = query.data.split("#")
        await query.answer(f"ʏᴏᴜ sᴇʟᴇᴄᴛᴇᴅ {lang.title()} ʟᴀɴɢᴜᴀɢᴇ ⚡️", show_alert=True)

    elif query.data == "start":
        buttons = [[
            InlineKeyboardButton('⇆ ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘs ⇆', url=f'http://t.me/{temp.U_NAME}?startgroup=start')
        ],[
            InlineKeyboardButton('⚙ ꜰᴇᴀᴛᴜʀᴇs', callback_data='features'),
            InlineKeyboardButton('💸 ᴘʀᴇᴍɪᴜᴍ', callback_data='buy_premium')
        ],[
            InlineKeyboardButton(script.REFERRAL_BUTTON_TEXT, callback_data='referral') # Added referral button
        ],[
            InlineKeyboardButton('🚫 ᴇᴀʀɴ ᴍᴏɴᴇʏ ᴡɪᴛʜ ʙᴏᴛ 🚫', callback_data='earn')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        try:
             await query.message.edit_text(
                 text=script.START_TXT.format(query.from_user.mention, get_status(), query.from_user.id),
                 reply_markup=reply_markup,
                 parse_mode=enums.ParseMode.HTML
             )
        except MessageNotModified:
             await query.answer()
        except Exception as e:
             logging.error(f"Error in start callback: {e}")

    elif query.data == "features":
        buttons = [[
            InlineKeyboardButton('📸 ᴛ-ɢʀᴀᴘʜ', callback_data='telegraph'),
            InlineKeyboardButton('🆎️ ғᴏɴᴛ', callback_data='font')
        ], [
            InlineKeyboardButton('⋞ ʙᴀᴄᴋ', callback_data='start')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        try:
             await query.message.edit_text(
                 text=script.HELP_TXT,
                 reply_markup=reply_markup,
                 parse_mode=enums.ParseMode.HTML
             )
        except MessageNotModified:
             await query.answer()
        except Exception as e:
             logging.error(f"Error in features callback: {e}")

    elif query.data == "earn":
        buttons = [[
            InlineKeyboardButton('⋞ ʙᴀᴄᴋ', callback_data='start'),
            InlineKeyboardButton('sᴜᴘᴘᴏʀᴛ', url=USERNAME)
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        try:
             await query.message.edit_text(
                  text=script.EARN_TEXT.format(temp.B_NAME), # Use B_NAME instead of B_LINK
                  reply_markup=reply_markup,
                  parse_mode=enums.ParseMode.HTML,
                  disable_web_page_preview=True # Disable preview for cleaner look
              )
        except MessageNotModified:
             await query.answer()
        except Exception as e:
             logging.error(f"Error in earn callback: {e}")

    elif query.data == "telegraph":
        buttons = [[
            InlineKeyboardButton('⋞ ʙᴀᴄᴋ', callback_data='features')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        try:
             await query.message.edit_text(
                 text=script.TELE_TXT,
                 reply_markup=reply_markup,
                 parse_mode=enums.ParseMode.HTML
             )
        except MessageNotModified:
             await query.answer()
        except Exception as e:
             logging.error(f"Error in telegraph callback: {e}")

    elif query.data == "font":
        buttons = [[
            InlineKeyboardButton('⋞ ʙᴀᴄᴋ', callback_data='features')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        try:
             await query.message.edit_text(
                 text=script.FONT_TXT,
                 reply_markup=reply_markup,
                 parse_mode=enums.ParseMode.HTML
             )
        except MessageNotModified:
             await query.answer()
        except Exception as e:
             logging.error(f"Error in font callback: {e}")

    # --- ADDED buy_premium handler ---
    elif query.data == "buy_premium":
        btn = [[
            InlineKeyboardButton('📸 sᴇɴᴅ sᴄʀᴇᴇɴsʜᴏᴛ 📸', url=USERNAME)
        ],[
            InlineKeyboardButton('🗑 ᴄʟᴏsᴇ 🗑', callback_data='close_data')
        ]]
        reply_markup = InlineKeyboardMarkup(btn)
        try:
            # Edit the existing message to show the photo and caption
            # Need to send photo if message doesn't have one, or edit if it does.
            # Simplest is to delete old and send new photo message.
            await query.message.delete() # Delete the text message
            await query.message.reply_photo( # Send photo as a reply to the original trigger if possible
                photo=(QR_CODE),
                caption=script.PREMIUM_TEXT.format(mention=query.from_user.mention), # Added mention format
                reply_markup=reply_markup,
                # parse_mode=enums.ParseMode.HTML # Parse mode often not needed for photo captions unless complex HTML
            )
        except Exception as e:
            logging.error(f"Error in buy_premium callback: {e}")
            # Fallback: Try editing if delete fails
            try:
                 await query.message.edit_text(
                     script.PREMIUM_TEXT.format(mention=query.from_user.mention) + "\n\nSee QR Code above.", # Add text explanation
                     reply_markup=reply_markup,
                     # parse_mode=enums.ParseMode.HTML
                 )
            except Exception as inner_e:
                 logging.error(f"Fallback error in buy_premium callback: {inner_e}")
                 await query.answer("Could not display premium info.", show_alert=True)

    # --- ADDED referral handler ---
    elif query.data == "referral":
        try:
            user_data = await db.get_user_data(query.from_user.id)
            if not user_data: # Handle case where user isn't in DB yet (shouldn't happen with /start first)
                 await db.add_user(query.from_user.id, query.from_user.first_name)
                 user_data = await db.get_user_data(query.from_user.id) # Fetch again

            referral_link = user_data.get('referral_link')

            if not referral_link:
                try:
                    new_link = await client.create_chat_invite_link(
                        chat_id=REFERRAL_GROUP_ID,
                        name=f"ref_{query.from_user.id}"
                    )
                    referral_link = new_link.invite_link
                    await db.set_referral_link(query.from_user.id, referral_link)
                except ChatAdminRequired:
                    await query.answer("Error: I lack permission to create invite links in the referral group.", show_alert=True)
                    return
                except Exception as link_e: # Catch specific link creation errors
                    logging.error(f"Error creating referral link: {link_e}")
                    await query.answer("Could not generate your referral link. Please try again later.", show_alert=True)
                    return


            referral_count = user_data.get('referral_count', 0)

            await query.message.edit_text(
                text=script.REFERRAL_INFO_TEXT.format(
                    link=referral_link,
                    count=referral_count,
                    target=REFERRAL_TARGET
                ),
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⋞ ʙᴀᴄᴋ", callback_data='start')]]),
                disable_web_page_preview=True,
                parse_mode=enums.ParseMode.HTML
            )

        except MessageNotModified:
            await query.answer()
        except Exception as e:
            logging.error(f"Error in referral callback: {e}")
            await query.answer("An error occurred. Please try again later.", show_alert=True)

    # --- END referral handler ---

    elif query.data == "all_files_delete": # Corrected callback_data
        if str(query.from_user.id) not in ADMINS: # Check permissions
             return await query.answer("Only admins can perform this action.", show_alert=True)
        files_count = await Media.count_documents() # Renamed variable
        await query.answer(f'Deleting {files_count} files...')
        await Media.collection.drop()
        await query.message.edit_text(f"Successfully deleted {files_count} files")

    elif query.data.startswith("killfilesak"):
        if str(query.from_user.id) not in ADMINS: # Check permissions
             return await query.answer("Only admins can perform this action.", show_alert=True)
        ident, keyword = query.data.split("#")
        await query.message.edit_text(f"<b>ꜰᴇᴛᴄʜɪɴɢ ꜰɪʟᴇs ꜰᴏʀ ʏᴏᴜʀ ǫᴜᴇʀʏ '{keyword}' ᴏɴ ᴅʙ...\n\nᴘʟᴇᴀsᴇ ᴡᴀɪᴛ...</b>")
        files, total = await get_bad_files(keyword)
        if total == 0:
             return await query.message.edit_text(f"No files found matching '{keyword}'.")

        await query.message.edit_text(f"<b>ꜰᴏᴜɴᴅ {total} ꜰɪʟᴇs ꜰᴏʀ ʏᴏᴜʀ ǫᴜᴇʀʏ '{keyword}'!!\nStarting deletion...</b>")

        deleted = 0
        async with lock: # Use lock for deletion
            try:
                delete_start_time = time.time()
                for file in files:
                    file_ids = file.file_id # Use . notation if possible
                    file_name = file.file_name
                    result = await Media.collection.delete_one({'_id': file_ids})
                    if result.deleted_count:
                        # print(f'Successfully deleted {file_name} from database.') # Avoid excessive printing in production
                        deleted += 1
                    # Update status less frequently to avoid rate limits
                    if deleted % 50 == 0 and (time.time() - delete_start_time) > 5: # Update every 50 or every 5 secs
                        try:
                            await query.message.edit_text(f"<b>Deletion in progress for '{keyword}'...\nSuccessfully deleted {deleted} / {total} files!\n\nPlease wait...</b>")
                            delete_start_time = time.time() # Reset timer
                        except MessageNotModified: pass
                        except FloodWait as fw:
                             await asyncio.sleep(fw.value)
                        except Exception as edit_e:
                             logging.warning(f"Could not edit killfiles status: {edit_e}")
                             break # Stop if editing fails

            except Exception as e:
                logging.error(f"Error during killfiles deletion: {e}")
                await query.message.edit_text(f'Error during deletion: {e}')
            else:
                await query.message.edit_text(f"<b>✅ Process Completed for '{keyword}'!\n\nSuccessfully deleted {deleted} / {total} files from database.</b>")

    elif query.data.startswith("reset_grp_data"):
        grp_id = query.message.chat.id
        if not await is_check_admin(client, grp_id, query.from_user.id): # Check permissions
             return await query.answer("Only group admins can reset settings.", show_alert=True)
        btn = [[
            InlineKeyboardButton('☕️ ᴄʟᴏsᴇ ☕️', callback_data='close_data')
        ]]
        reply_markup=InlineKeyboardMarkup(btn)
        # Use default values from info.py or wherever they are defined
        await save_group_settings(grp_id, 'shortner', SHORTENER_WEBSITE)
        await save_group_settings(grp_id, 'api', SHORTENER_API)
        await save_group_settings(grp_id, 'shortner_two', SHORTENER_WEBSITE2)
        await save_group_settings(grp_id, 'api_two', SHORTENER_API2)
        await save_group_settings(grp_id, 'template', IMDB_TEMPLATE)
        await save_group_settings(grp_id, 'tutorial', TUTORIAL)
        await save_group_settings(grp_id, 'caption', FILE_CAPTION)
        await save_group_settings(grp_id, 'log', LOG_VR_CHANNEL) # Assuming this is the intended default
        await query.answer('ꜱᴜᴄᴄᴇꜱꜱғᴜʟʟʏ ʀᴇꜱᴇᴛ...')
        await query.message.edit_text("<b>✅️ ꜱᴜᴄᴄᴇꜱꜱғᴜʟʟʏ ʀᴇꜱᴇᴛ ɢʀᴏᴜᴘ ꜱᴇᴛᴛɪɴɢꜱ ᴛᴏ ᴅᴇꜰᴀᴜʟᴛ.\n\nɴᴏᴡ ꜱᴇɴᴅ /details ᴀɢᴀɪɴ ᴛᴏ ᴠɪᴇᴡ.</b>", reply_markup=reply_markup)

    elif query.data.startswith("setgs"):
            ident, set_type, status, grp_id_str = query.data.split("#") # Rename grp_id to grp_id_str
            grp_id = int(grp_id_str) # Convert to int
            userid = query.from_user.id if query.from_user else None
            if not await is_check_admin(client, grp_id, userid):
                await query.answer(script.ALRT_TXT, show_alert=True)
                return

            new_status = False if status == "True" else True # Toggle status
            await save_group_settings(grp_id, set_type, new_status)

            # Answer based on the *new* status
            await query.answer(f"{set_type.replace('_',' ').title()} turned {'ON ✅' if new_status else 'OFF ❌'}")

            settings = await get_settings(grp_id) # Fetch updated settings
            if settings is not None:
                # Rebuild buttons with updated status
                buttons = [[
                    InlineKeyboardButton('ᴀᴜᴛᴏ ꜰɪʟᴛᴇʀ', callback_data=f'setgs#auto_filter#{settings["auto_filter"]}#{grp_id}'),
                    InlineKeyboardButton('ᴏɴ ✔️' if settings["auto_filter"] else 'ᴏғғ ✗', callback_data=f'setgs#auto_filter#{settings["auto_filter"]}#{grp_id}')
                ],[
                    InlineKeyboardButton('ꜰɪʟᴇ sᴇᴄᴜʀᴇ', callback_data=f'setgs#file_secure#{settings["file_secure"]}#{grp_id}'),
                    InlineKeyboardButton('ᴏɴ ✔️' if settings["file_secure"] else 'ᴏғғ ✗', callback_data=f'setgs#file_secure#{settings["file_secure"]}#{grp_id}')
                ],[
                    InlineKeyboardButton('ɪᴍᴅʙ', callback_data=f'setgs#imdb#{settings["imdb"]}#{grp_id}'),
                    InlineKeyboardButton('ᴏɴ ✔️' if settings["imdb"] else 'ᴏғғ ✗', callback_data=f'setgs#imdb#{settings["imdb"]}#{grp_id}')
                ],[
                    InlineKeyboardButton('sᴘᴇʟʟ ᴄʜᴇᴄᴋ', callback_data=f'setgs#spell_check#{settings["spell_check"]}#{grp_id}'),
                    InlineKeyboardButton('ᴏɴ ✔️' if settings["spell_check"] else 'ᴏғғ ✗', callback_data=f'setgs#spell_check#{settings["spell_check"]}#{grp_id}')
                ],[
                    InlineKeyboardButton('ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ', callback_data=f'setgs#auto_delete#{settings["auto_delete"]}#{grp_id}'),
                    InlineKeyboardButton(f'{get_readable_time(DELETE_TIME)}' if settings["auto_delete"] else 'ᴏғғ ✗', callback_data=f'setgs#auto_delete#{settings["auto_delete"]}#{grp_id}')
                ],[
                    InlineKeyboardButton('ʀᴇsᴜʟᴛ ᴍᴏᴅᴇ', callback_data=f'setgs#link#{settings["link"]}#{grp_id_str}'), # Use string grp_id here
                    InlineKeyboardButton('ʟɪɴᴋ' if settings["link"] else 'ʙᴜᴛᴛᴏɴ', callback_data=f'setgs#link#{settings["link"]}#{grp_id_str}') # Use string grp_id here
                ],[
                    InlineKeyboardButton('ᴠᴇʀɪғʏ', callback_data=f'setgs#is_verify#{settings["is_verify"]}#{grp_id}'),
                    InlineKeyboardButton('ᴏɴ ✔️' if settings["is_verify"] else 'ᴏғғ ✗', callback_data=f'setgs#is_verify#{settings["is_verify"]}#{grp_id}')
                ],[
                    InlineKeyboardButton('☕️ ᴄʟᴏsᴇ ☕️', callback_data='close_data')
                ]]
                reply_markup = InlineKeyboardMarkup(buttons)
                try:
                     await query.message.edit_reply_markup(reply_markup)
                except MessageNotModified:
                     pass # Ignore if markup is identical
                except Exception as e:
                     logging.error(f"Error editing settings markup: {e}")
                     await query.answer("Could not update buttons.", show_alert=True)
            else:
                await query.message.edit_text("<b>ꜱᴏᴍᴇᴛʜɪɴɢ ᴡᴇɴᴛ ᴡʀᴏɴɢ getting settings after update.</b>")

    # --- Request Channel Handlers ---
    elif query.data.startswith("show_options"):
        if not REQUEST_CHANNEL: return await query.answer("Request system disabled.", show_alert=True)
        ident, user_id, msg_id = query.data.split("#")
        chnl_id = query.message.chat.id # This is REQUEST_CHANNEL ID
        userid = query.from_user.id
        buttons = [[
            InlineKeyboardButton("✅️ ᴀᴄᴄᴇᴘᴛ ᴛʜɪꜱ ʀᴇǫᴜᴇꜱᴛ ✅️", callback_data=f"accept#{user_id}#{msg_id}")
        ],[
            InlineKeyboardButton("🚫 ʀᴇᴊᴇᴄᴛ ᴛʜɪꜱ ʀᴇǫᴜᴇꜱᴛ 🚫", callback_data=f"reject#{user_id}#{msg_id}")
        ]]
        try:
            st = await client.get_chat_member(chnl_id, userid)
            if st.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
                await query.message.edit_reply_markup(InlineKeyboardMarkup(buttons))
            else: # Regular members shouldn't see these options
                await query.answer(script.ALRT_TXT, show_alert=True)
        except UserNotParticipant: # Catch specific error
            await query.answer("⚠️ You need to be a member of the request channel to manage requests.", show_alert=True)
        except Exception as e:
            logging.error(f"Error in show_options: {e}")
            await query.answer("An error occurred.", show_alert=True)


    elif query.data.startswith("reject"):
        if not REQUEST_CHANNEL: return await query.answer("Request system disabled.", show_alert=True)
        ident, user_id_str, msg_id_str = query.data.split("#")
        user_id = int(user_id_str)
        msg_id = int(msg_id_str) # Original message ID in the group
        chnl_id = query.message.chat.id # This is REQUEST_CHANNEL ID
        userid = query.from_user.id
        buttons = [[
            InlineKeyboardButton("✗ ʀᴇᴊᴇᴄᴛᴇᴅ ʙʏ {} ✗".format(query.from_user.first_name), callback_data=f"rj_alert#{user_id_str}") # Show who rejected
        ]]
        btn = [[
            InlineKeyboardButton("♻️ ᴠɪᴇᴡ sᴛᴀᴛᴜs ♻️", url=f"{query.message.link}") # Link to the message in request channel
        ]]
        try:
             st = await client.get_chat_member(chnl_id, userid)
             if st.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
                 user = await client.get_users(user_id)
                 request = query.message.text # Original request text
                 await query.answer("Notifying requester...")
                 await query.message.edit_text(f"<s>{request}</s>\n\n#Rejected by {query.from_user.mention}") # Strike through and add rejector info
                 await query.message.edit_reply_markup(InlineKeyboardMarkup(buttons))
                 try:
                     await client.send_message(chat_id=user_id, text="<b>Sᴏʀʀʏ, ʏᴏᴜʀ ʀᴇǫᴜᴇsᴛ ᴡᴀs ʀᴇᴊᴇᴄᴛᴇᴅ 😶</b>", reply_markup=InlineKeyboardMarkup(btn))
                 except UserIsBlocked:
                     # Attempt to notify in support group if user blocked bot
                     if SUPPORT_GROUP and msg_id: # Check if SUPPORT_GROUP is set and msg_id is valid
                         try:
                             await client.send_message(SUPPORT_GROUP, text=f"<b>💥 ʜᴇʟʟᴏ {user.mention},\n\nSᴏʀʀʏ, ʏᴏᴜʀ ʀᴇǫᴜᴇsᴛ (<a href='{query.message.link}'>view</a>) ᴡᴀs ʀᴇᴊᴇᴄᴛᴇᴅ 😶</b>", reply_markup=InlineKeyboardMarkup(btn), reply_to_message_id=msg_id)
                         except Exception as sg_e:
                             logging.error(f"Could not notify rejected user in support group: {sg_e}")
                 except Exception as pm_e:
                      logging.error(f"Could not PM rejected user: {pm_e}")
             else:
                 await query.answer(script.ALRT_TXT, show_alert=True)
        except Exception as e:
             logging.error(f"Error in reject callback: {e}")
             await query.answer("An error occurred.", show_alert=True)


    elif query.data.startswith("accept"):
        if not REQUEST_CHANNEL: return await query.answer("Request system disabled.", show_alert=True)
        ident, user_id, msg_id = query.data.split("#")
        chnl_id = query.message.chat.id
        userid = query.from_user.id
        # Define actions/statuses
        buttons = [[
            InlineKeyboardButton("🟢 Already Available", callback_data=f"already_available#{user_id}#{msg_id}")
        ],[
            InlineKeyboardButton("🟡 Need Year/Language", callback_data=f"year#{user_id}#{msg_id}")
        ],[
            InlineKeyboardButton("🟠 Uploading Soon (1hr)", callback_data=f"upload_in#{user_id}#{msg_id}")
        ],[
            InlineKeyboardButton("🔵 Uploaded", callback_data=f"uploaded#{user_id}#{msg_id}")
        ],[
            InlineKeyboardButton("⚫ Not Available", callback_data=f"not_available#{user_id}#{msg_id}")
        ],[
            InlineKeyboardButton("🔙 Back to Options", callback_data=f"show_options#{user_id}#{msg_id}") # Back button
        ]]
        try:
            st = await client.get_chat_member(chnl_id, userid)
            if st.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
                await query.message.edit_reply_markup(InlineKeyboardMarkup(buttons))
                await query.answer("Select status...") # Give feedback
            else:
                await query.answer(script.ALRT_TXT, show_alert=True)
        except UserNotParticipant:
            await query.answer("⚠️ You need to be a member of the request channel.", show_alert=True)
        except Exception as e:
            logging.error(f"Error in accept callback: {e}")
            await query.answer("An error occurred.", show_alert=True)


    # --- Status Update Handlers (Simplified) ---
    async def update_request_status(query: CallbackQuery, client: Client, status_text: str, alert_text: str, status_emoji: str):
        if not REQUEST_CHANNEL: return await query.answer("Request system disabled.", show_alert=True)
        ident, user_id_str, msg_id_str = query.data.split("#")
        user_id = int(user_id_str)
        msg_id = int(msg_id_str)
        chnl_id = query.message.chat.id
        userid = query.from_user.id

        final_button = [[
             InlineKeyboardButton(f"{status_emoji} {status_text} by {query.from_user.first_name}", callback_data=f"{ident}_alert#{user_id_str}")
        ]]
        status_link_button = [[
             InlineKeyboardButton("♻️ ᴠɪᴇᴡ sᴛᴀᴛᴜs ♻️", url=f"{query.message.link}")
        ]]

        try:
            st = await client.get_chat_member(chnl_id, userid)
            if st.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
                user = await client.get_users(user_id)
                request_text = query.message.text # Use current text
                # Check if already processed
                if request_text.startswith("<s>"):
                     return await query.answer(f"This request was already processed.", show_alert=True)

                await query.answer(f"Setting status to: {status_text}")
                await query.message.edit_text(f"<s>{request_text}</s>\n\n#{status_text.replace(' ','_')} by {query.from_user.mention}")
                await query.message.edit_reply_markup(InlineKeyboardMarkup(final_button))
                try:
                    await client.send_message(chat_id=user_id, text=f"<b>Regarding your request:\n{alert_text}</b>", reply_markup=InlineKeyboardMarkup(status_link_button))
                except UserIsBlocked:
                    if SUPPORT_GROUP and msg_id:
                        try:
                            await client.send_message(SUPPORT_GROUP, text=f"<b>💥 ʜᴇʟʟᴏ {user.mention},\nRegarding your request (<a href='{query.message.link}'>view</a>):\n{alert_text}</b>", reply_markup=InlineKeyboardMarkup(status_link_button), reply_to_message_id=msg_id)
                        except Exception as sg_e: logging.error(f"Could not notify user ({status_text}) in support group: {sg_e}")
                except Exception as pm_e: logging.error(f"Could not PM user ({status_text}): {pm_e}")
            else:
                await query.answer(script.ALRT_TXT, show_alert=True)
        except Exception as e:
            logging.error(f"Error in {ident} callback: {e}")
            await query.answer("An error occurred.", show_alert=True)

    # Simplified handlers using the helper function
    elif query.data.startswith("not_available"):
        await update_request_status(query, client, "Not Available", "Sᴏʀʀʏ, ɪᴛ's ɴᴏᴛ ᴀᴠᴀɪʟᴀʙʟᴇ 😢", "⚫")
    elif query.data.startswith("uploaded"):
        await update_request_status(query, client, "Uploaded", "Yᴏᴜʀ ʀᴇǫᴜᴇsᴛ ɪs ᴜᴘʟᴏᴀᴅᴇᴅ ☺️", "🔵")
    elif query.data.startswith("already_available"):
        await update_request_status(query, client, "Already Available", "Yᴏᴜʀ ʀᴇǫᴜᴇsᴛ ɪs ᴀʟʀᴇᴀᴅʏ ᴀᴠᴀɪʟᴀʙʟᴇ 😋", "🟢")
    elif query.data.startswith("upload_in"):
        await update_request_status(query, client, "Uploading Soon", "Yᴏᴜʀ ʀᴇǫᴜᴇꜱᴛ ᴡɪʟʟ ʙᴇ ᴜᴘʟᴏᴀᴅᴇᴅ ᴡɪᴛʜɪɴ 1 ʜᴏᴜʀ 😁", "🟠")
    elif query.data.startswith("year"):
        await update_request_status(query, client, "Need Year/Language", "Pʟᴇᴀꜱᴇ ᴘʀᴏᴠɪᴅᴇ ᴛʜᴇ ʏᴇᴀʀ ᴀɴᴅ ʟᴀɴɢᴜᴀɢᴇ ꜰᴏʀ ʏᴏᴜʀ ʀᴇǫᴜᴇꜱᴛ, ᴛʜᴇɴ ɪ ᴡɪʟʟ ᴜᴘʟᴏᴀᴅ 😬", "🟡")

    # --- Alert Handlers (User clicking the final status button) ---
    async def final_status_alert(query: CallbackQuery, alert_text: str):
        ident, user_id_str = query.data.split("#")
        userid = query.from_user.id
        # Only the original requester should get the detailed alert
        if user_id_str == str(userid):
            await query.answer(alert_text, show_alert=True)
        else:
            await query.answer("This is the final status set by an admin.", show_alert=False) # Generic message for others

    elif query.data.startswith("rj_alert"):
        await final_status_alert(query, "Sᴏʀʀʏ, ʏᴏᴜʀ ʀᴇǫᴜᴇsᴛ ᴡᴀs ʀᴇᴊᴇᴄᴛᴇᴅ 😶")
    elif query.data.startswith("na_alert"):
        await final_status_alert(query, "Sᴏʀʀʏ, ʏᴏᴜʀ ʀᴇǫᴜᴇsᴛ ɪs ɴᴏᴛ ᴀᴠᴀɪʟᴀʙʟᴇ 😢")
    elif query.data.startswith("ul_alert"):
        await final_status_alert(query, "Yᴏᴜʀ ʀᴇǫᴜᴇsᴛ ɪs ᴜᴘʟᴏᴀᴅᴇᴅ ☺️")
    elif query.data.startswith("aa_alert"):
        await final_status_alert(query, "Yᴏᴜʀ ʀᴇǫᴜᴇsᴛ ɪs ᴀʟʀᴇᴀᴅʏ ᴀᴠᴀɪʟᴀʙʟᴇ 😋")
    elif query.data.startswith("upload_alert"):
        await final_status_alert(query, "Yᴏᴜʀ ʀᴇǫᴜᴇꜱᴛ ᴡɪʟʟ ʙᴇ ᴜᴘʟᴏᴀᴅᴇᴅ ᴡɪᴛʜɪɴ 1 ʜᴏᴜʀ 😁")
    elif query.data.startswith("yrs_alert"):
        await final_status_alert(query, "Pʟᴇᴀꜱᴇ ᴘʀᴏᴠɪᴅᴇ ᴛʜᴇ ʏᴇᴀʀ ᴀɴᴅ ʟᴀɴɢᴜᴀɢᴇ ꜰᴏʀ ʏᴏᴜʀ ʀᴇǫᴜᴇꜱᴛ.")


    elif query.data.startswith("batchfiles"):
        ident, group_id_str, message_id_str, user_str = query.data.split("#")
        group_id = int(group_id_str)
        message_id = int(message_id_str)
        user = int(user_str)
        if user != query.from_user.id:
            await query.answer(script.ALRT_TXT, show_alert=True)
            return
        # Fetch the file list associated with this specific button press
        file_keys = f"{group_id}-{message_id}"
        files_to_send = temp.FILES_ID.get(file_keys)

        if not files_to_send:
             await query.answer("Sorry, the file list for this request has expired or could not be found.", show_alert=True)
             return

        # Generate a unique key for this batch operation
        batch_key = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        temp.FILES_ID[batch_key] = files_to_send # Store files under the new key

        # Create start link using the new batch_key
        link = f"https://telegram.me/{temp.U_NAME}?start=allfiles_{batch_key}"
        await query.answer(f"Click OK to get all {len(files_to_send)} files.", url=link, cache_time=0)
        return

async def auto_filter(client, msg, spoll=False):
    if not spoll:
        message = msg
        search = message.text
        chat_id = message.chat.id
        settings = await get_settings(chat_id)
        # Fetch results without quality/language first for spell check
        files, offset, total_results = await get_search_results(search)
        if not files:
            if settings["spell_check"]:
                return await advantage_spell_chok(msg)
            else: # If no files and spell check off, do nothing or send a 'not found' message
                 # Example: Send 'not found' and delete after a delay
                 # k = await message.reply(script.I_CUD_NT.format(message.from_user.mention))
                 # await asyncio.sleep(60)
                 # try: await k.delete()
                 # except: pass
                 return # Explicitly return if no files and no spell check
    else:
        settings = await get_settings(msg.message.chat.id)
        message = msg.message.reply_to_message # msg will be callback query
        search, files, offset, total_results = spoll

    if not files: # Double-check after spell check logic
         # This case might happen if spell check suggests something with no results
         return

    req = message.from_user.id if message.from_user else 0
    key = f"{message.chat.id}-{message.id}" # Unique key for this specific message results

    # Store the initial search results for pagination/filtering
    BUTTONS[key] = search
    CAP[key] = "" # Initialize caption storage

    batch_ids = files # Use the fetched files
    temp.FILES_ID[f"{message.chat.id}-{message.id}"] = batch_ids # Store for 'Send All' button
    batch_link = f"batchfiles#{message.chat.id}#{message.id}#{req}" # Link to this specific message's files

    # Removed 'pre' variable, seems unused

    temp.CHAT[req] = message.chat.id # Store user's chat context

    del_msg = f"\n\n<b>⚠️ ᴛʜɪs ᴍᴇssᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ ᴀꜰᴛᴇʀ <code>{get_readable_time(DELETE_TIME)}</code> ᴛᴏ ᴀᴠᴏɪᴅ ᴄᴏᴘʏʀɪɢʜᴛ ɪssᴜᴇs</b>" if settings["auto_delete"] else ''
    links = ""
    btn = [] # Initialize btn

    if settings["link"]:
        for file_num, file in enumerate(files, start=1):
            links += f"""<b>\n\n{file_num}. <a href=https://t.me/{temp.U_NAME}?start=file_{message.chat.id}_{file.file_id}>[{get_size(file.file_size)}] {' '.join(filter(lambda x: not x.startswith('[') and not x.startswith('@') and not x.startswith('www.'), file.file_name.split()))}</a></b>"""
    else:
        btn = [[InlineKeyboardButton(text=f"🔗 {get_size(file.file_size)}≽ {get_name(file.file_name)}", url=f'https://telegram.dog/{temp.U_NAME}?start=file_{message.chat.id}_{file.file_id}'),]
               for file in files
              ]

    # Insert Top Buttons (Send All, Premium, Filters)
    filter_buttons = []
    if total_results > 0: # Only show filters if results exist
         filter_buttons.append(InlineKeyboardButton("📰 ʟᴀɴɢᴜᴀɢᴇs", callback_data=f"languages#{key}#0#{req}"))
         filter_buttons.append(InlineKeyboardButton("🎞️ ǫᴜᴀʟɪᴛʏ", callback_data=f"qualities#{key}#0#{req}"))

    if filter_buttons:
         btn.insert(0, filter_buttons)

    top_buttons = []
    if total_results >= 3: # Only show 'Send All' if 3 or more files
         top_buttons.append(InlineKeyboardButton("♻️ sᴇɴᴅ ᴀʟʟ", callback_data=batch_link))
    top_buttons.append(InlineKeyboardButton("🥇ʙᴜʏ🥇", url=f"https://t.me/{temp.U_NAME}?start=buy_premium"))

    if top_buttons:
         btn.insert(0, top_buttons)


    # Append Utility Buttons (How To, Referral)
    btn.append(
        [InlineKeyboardButton("🤔 ʜᴏᴡ ᴛᴏ ᴅᴏᴡɴʟᴏᴀᴅ 🤔", url=settings['tutorial'])]
    )
    btn.append(
        [InlineKeyboardButton(script.REFERRAL_BUTTON_TEXT, callback_data='referral')]
    )

    # --- Pagination ---
    if offset != "": # Check if pagination is needed (offset is the *next* offset)
        pagination_buttons = []
        # No back button on the first page
        pagination_buttons.append(InlineKeyboardButton(text=f"1/{math.ceil(int(total_results) / int(MAX_BTN))}", callback_data="pages"))
        if int(total_results) > int(MAX_BTN): # Only show Next if more than one page
             pagination_buttons.append(InlineKeyboardButton(text="ɴᴇxᴛ ⪼", callback_data=f"next_{req}_{key}_{offset}"))
        if pagination_buttons:
             btn.append(pagination_buttons)


    imdb = await get_poster(search, file=(files[0]).file_name) if settings["imdb"] and files else None # Check if files exist
    TEMPLATE = settings['template']
    cap = "" # Initialize cap

    if imdb:
        cap = TEMPLATE.format(
            query=search,
            title=imdb.get('title', "N/A"),
            votes=imdb.get('votes', "N/A"),
            aka=imdb.get("aka", "N/A"),
            seasons=imdb.get("seasons", "N/A"),
            box_office=imdb.get('box_office', "N/A"),
            localized_title=imdb.get('localized_title', "N/A"),
            kind=imdb.get('kind', "N/A"),
            imdb_id=imdb.get("imdb_id", "N/A"),
            cast=imdb.get("cast", "N/A"),
            runtime=imdb.get("runtime", "N/A"),
            countries=imdb.get("countries", "N/A"),
            certificates=imdb.get("certificates", "N/A"),
            languages=imdb.get("languages", "N/A"),
            director=imdb.get("director", "N/A"),
            writer=imdb.get("writer", "N/A"),
            producer=imdb.get("producer", "N/A"),
            composer=imdb.get("composer", "N/A"),
            cinematographer=imdb.get("cinematographer", "N/A"),
            music_team=imdb.get("music_team", "N/A"),
            distributors=imdb.get("distributors", "N/A"),
            release_date=imdb.get('release_date', "N/A"),
            year=imdb.get('year', "N/A"),
            genres=imdb.get('genres', "N/A"),
            poster=imdb.get('poster', ""), # Default to empty string if no poster
            plot=imdb.get('plot', "N/A"),
            rating=imdb.get('rating', "N/A"),
            url=imdb.get('url', "#"), # Default to # if no url
            **locals() # Be cautious using locals()
        )
    else:
        cap = f"<b>📂 ʜᴇʀᴇ ɪ ꜰᴏᴜɴᴅ ꜰᴏʀ ʏᴏᴜʀ sᴇᴀʀᴄʜ '{search}'</b>"

    CAP[key] = cap # Store the generated caption

    final_caption = cap + links + del_msg if settings["link"] else cap + del_msg

    # --- Sending/Editing Message ---
    reply_markup = InlineKeyboardMarkup(btn) if btn else None # Handle cases with no buttons

    if spoll: # If called from spell check callback
        try:
             # Edit the original message (which showed spell check options)
             if imdb and imdb.get('poster'):
                  await msg.message.edit_media(
                       media=InputMediaPhoto(imdb.get('poster'), caption=final_caption[:1024]),
                       reply_markup=reply_markup
                  )
             else:
                  await msg.message.edit_text(
                       text=final_caption,
                       reply_markup=reply_markup,
                       disable_web_page_preview=True,
                       parse_mode=enums.ParseMode.HTML
                  )
        except Exception as e:
             logging.error(f"Error editing message after spell check: {e}")
             # Fallback: Send a new message if editing fails
             try:
                  await client.send_message(
                       chat_id=msg.message.chat.id,
                       text=final_caption,
                       reply_markup=reply_markup,
                       disable_web_page_preview=True,
                       parse_mode=enums.ParseMode.HTML,
                       reply_to_message_id=message.id # Reply to the original user message
                  )
             except Exception as send_e:
                  logging.error(f"Fallback send message failed after spell check edit error: {send_e}")
        return # Exit after handling spell check callback


    # --- Regular message handling ---
    sent_message = None
    try:
        if imdb and imdb.get('poster'):
            sent_message = await message.reply_photo(
                photo=imdb.get('poster'),
                caption=final_caption[:1024], # Caption limit for photos
                parse_mode=enums.ParseMode.HTML,
                reply_markup=reply_markup,
                reply_to_message_id=message.id
            )
        else:
            sent_message = await message.reply_text(
                text=final_caption,
                disable_web_page_preview=True,
                parse_mode=enums.ParseMode.HTML,
                reply_markup=reply_markup,
                reply_to_message_id=message.id
            )
    except (MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty) as media_err:
         logging.warning(f"Media error sending poster for '{search}': {media_err}. Trying smaller poster.")
         pic = imdb.get('poster')
         if pic:
              poster = pic.replace('.jpg', "._V1_UX360.jpg") # Try smaller version
              try:
                   sent_message = await message.reply_photo(
                       photo=poster, caption=final_caption[:1024], parse_mode=enums.ParseMode.HTML, reply_markup=reply_markup, reply_to_message_id=message.id
                   )
              except Exception as e:
                   logging.error(f"Error sending smaller poster: {e}. Falling back to text.")
                   # Fallback to text if smaller poster also fails
                   sent_message = await message.reply_text(text=final_caption, disable_web_page_preview=True, parse_mode=enums.ParseMode.HTML, reply_markup=reply_markup, reply_to_message_id=message.id)
         else: # No poster URL at all
             sent_message = await message.reply_text(text=final_caption, disable_web_page_preview=True, parse_mode=enums.ParseMode.HTML, reply_markup=reply_markup, reply_to_message_id=message.id)

    except Exception as e:
        logging.error(f"Error sending auto_filter message for '{search}': {e}")
        # Attempt to send text message as fallback
        try:
             sent_message = await message.reply_text(text=final_caption, disable_web_page_preview=True, parse_mode=enums.ParseMode.HTML, reply_markup=reply_markup, reply_to_message_id=message.id)
        except Exception as fallback_e:
             logging.error(f"Fallback text message failed in auto_filter: {fallback_e}")

    # Auto-delete logic
    if settings['auto_delete'] and sent_message:
        await asyncio.sleep(DELETE_TIME)
        try:
            await sent_message.delete()
            # Also delete the user's trigger message
            await message.delete()
        except Exception as del_e:
            logging.warning(f"Could not auto-delete messages: {del_e}")


async def advantage_spell_chok(message):
    mv_id = message.id # Keep track of original message ID
    search = message.text
    chat_id = message.chat.id
    settings = await get_settings(chat_id)

    # Simplified query cleaning
    query = re.sub(r"(movie|series|tv|show|hindi|english|tamil|telugu|malayalam|kannada|dubbed|watch|online|download|free|full|hd|4k|1080p|720p|480p|episode|\d{1,3}|\W)+$", "", search, flags=re.IGNORECASE).strip()
    if not query: query = search # Fallback if cleaning removes everything

    try:
        movies = await get_poster(query, bulk=True) # Use cleaned query
    except Exception as e:
        logging.error(f"Error getting posters for spell check '{query}': {e}")
        k = await message.reply(script.I_CUDNT.format(message.from_user.mention))
        await asyncio.sleep(60)
        try: await k.delete()
        except: pass
        try: await message.delete()
        except: pass
        return

    if not movies:
        google_query = search.replace(" ", "+") # Use original search for Google
        button = [[
            InlineKeyboardButton("🔍 ᴄʜᴇᴄᴋ sᴘᴇʟʟɪɴɢ ᴏɴ ɢᴏᴏɢʟᴇ 🔍", url=f"https://www.google.com/search?q={google_query}")
        ]]
        k = await message.reply_text(text=script.I_CUD_NT.format(message.from_user.mention), reply_markup=InlineKeyboardMarkup(button)) # Use specific 'not found' message
        await asyncio.sleep(120)
        try: await k.delete()
        except: pass
        try: await message.delete()
        except: pass
        return

    user = message.from_user.id if message.from_user else 0
    buttons = [[
        InlineKeyboardButton(
            text=f"{movie.get('title')} ({movie.get('year')})", # Add year for clarity
            callback_data=f"spol#{movie.movieID}#{user}"
        )
    ]
        for movie in movies[:8] # Limit suggestions
    ]
    buttons.append(
        [InlineKeyboardButton(text="🚫 ᴄʟᴏsᴇ 🚫", callback_data='close_data')]
    )
    d = await message.reply_text(
         text=script.CUDNT_FND.format(message.from_user.mention),
         reply_markup=InlineKeyboardMarkup(buttons),
         reply_to_message_id=message.id # Reply to the original message
    )

    # Auto-delete the suggestion message
    await asyncio.sleep(120)
    try: await d.delete()
    except: pass
    # Do NOT delete the original user message here, wait for them to click or timeout
