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
                           ChatAdminRequired, UserNotParticipant) # Added imports
from utils import temp, get_settings, is_check_admin, get_status, get_hash, get_name, get_size, save_group_settings, is_req_subscribed, get_poster, get_readable_time # Simplified get_status import
from database.users_chats_db import db
from database.ia_filterdb import Media, get_search_results, get_bad_files, get_file_details

lock = asyncio.Lock()

BUTTONS = {}
FILES_ID = {}
CAP = {}

# --- HELPER FUNCTIONS (Moved outside cb_handler) ---
async def update_request_status(query: CallbackQuery, client: Client, status_text: str, alert_text: str, status_emoji: str):
    # This block should be indented inside the function
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

    # 'try' is indented
    try:
        # Code inside 'try' is further indented
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
            try: # Nested try
                await client.send_message(chat_id=user_id, text=f"<b>Regarding your request:\n{alert_text}</b>", reply_markup=InlineKeyboardMarkup(status_link_button))
            except UserIsBlocked: # except for nested try
                if SUPPORT_GROUP and msg_id:
                    try:
                        await client.send_message(SUPPORT_GROUP, text=f"<b>💥 ʜᴇʟʟᴏ {user.mention},\nRegarding your request (<a href='{query.message.link}'>view</a>):\n{alert_text}</b>", reply_markup=InlineKeyboardMarkup(status_link_button), reply_to_message_id=msg_id)
                    except Exception as sg_e: logging.error(f"Could not notify user ({status_text}) in support group: {sg_e}")
            except Exception as pm_e: logging.error(f"Could not PM user ({status_text}): {pm_e}")
        else:
            await query.answer(script.ALRT_TXT, show_alert=True)

    # 'except' is aligned with 'try'
    except Exception as e:
        # Code inside 'except' is further indented
        logging.error(f"Error in {query.data.split('#')[0]} callback: {e}") # Use ident for logging
        await query.answer("An error occurred.", show_alert=True)


async def final_status_alert(query: CallbackQuery, alert_text: str):
    ident, user_id_str = query.data.split("#")
    userid = query.from_user.id
    # Only the original requester should get the detailed alert
    if user_id_str == str(userid):
        await query.answer(alert_text, show_alert=True)
    else:
        await query.answer("This is the final status set by an admin.", show_alert=False) # Generic message for others


# --- MAIN BOT LOGIC ---

@Client.on_message(filters.private & filters.text & filters.incoming)
async def pm_search(client, message):
    if IS_PM_SEARCH:
        lang_keywords = LANGUAGES + ['english', 'gujarati']
        if any(lang in message.text.lower() for lang in lang_keywords):
            return await auto_filter(client, message)
        await auto_filter(client, message)
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

        lang_keywords = LANGUAGES + ['english', 'gujarati']
        if any(lang in message.text.lower() for lang in lang_keywords):
            return await auto_filter(client, message)

        if message.text.startswith("/"):
            return

        elif re.findall(r'https?://\S+|www\.\S+|t\.me/\S+', message.text):
            if await is_check_admin(client, message.chat.id, message.from_user.id):
                return
            try:
                await message.delete()
            except ChatAdminRequired:
                pass
            return await message.reply('<b>‼️ ᴡʜʏ ʏᴏᴜ ꜱᴇɴᴅ ʜᴇʀᴇ ʟɪɴᴋ\nʟɪɴᴋ ɴᴏᴛ ᴀʟʟᴏᴡᴇᴅ ʜᴇʀᴇ 🚫</b>')

        elif '@admin' in message.text.lower() or '@admins' in message.text.lower():
            if await is_check_admin(client, message.chat.id, message.from_user.id):
                return
            admins = []
            owner_id = None
            async for member in client.get_chat_members(chat_id=message.chat.id, filter=enums.ChatMembersFilter.ADMINISTRATORS):
                if not member.user.is_bot:
                    admins.append(member.user.id)
                    if member.status == enums.ChatMemberStatus.OWNER:
                        owner_id = member.user.id

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

            hidden_mentions = ''.join([f'[\u2064](tg://user?id={admin_id})' for admin_id in admins])
            await message.reply_text('<code>Report sent to admins.</code>' + hidden_mentions)
            return
        else:
            await auto_filter(client, message)
    else:
        k = await message.reply_text('<b>⚠️ ᴀᴜᴛᴏ ғɪʟᴛᴇʀ ᴍᴏᴅᴇ ɪꜱ ᴏғғ...</b>')
        await asyncio.sleep(10)
        try: await k.delete()
        except: pass
        try: await message.delete()
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
         await query.answer("No more files found for this query.", show_alert=True)
         return
    temp.FILES_ID[key] = files

    batch_ids = files
    temp.FILES_ID[f"{query.message.chat.id}-{query.id}"] = batch_ids
    batch_link = f"batchfiles#{query.message.chat.id}#{query.id}#{query.from_user.id}"

    settings = await get_settings(query.message.chat.id)
    reqnxt  = query.from_user.id
    temp.CHAT[query.from_user.id] = query.message.chat.id
    del_msg = f"\n\n<b>⚠️ ᴛʜɪs ᴍᴇssᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ ᴀꜰᴛᴇʀ <code>{get_readable_time(DELETE_TIME)}</code> ᴛᴏ ᴀᴠᴏɪᴅ ᴄᴏᴘʏʀɪɢʜᴛ ɪssᴜᴇs</b>" if settings["auto_delete"] else ''
    links = ""
    btn = []

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
    edit_caption = cap + links + del_msg if settings["link"] else cap + del_msg
    try:
        if settings["link"]:
             await query.message.edit_text(edit_caption, disable_web_page_preview=True, parse_mode=enums.ParseMode.HTML, reply_markup=InlineKeyboardMarkup(btn))
        else:
             if query.message.photo:
                  await query.message.edit_caption(caption=edit_caption, reply_markup=InlineKeyboardMarkup(btn), parse_mode=enums.ParseMode.HTML)
             else:
                  await query.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(btn))
    except MessageNotModified:
        pass
    except Exception as e:
         logging.error(f"Error editing message in next_page: {e}")
    await query.answer()

@Client.on_callback_query(filters.regex(r"^languages#"))
async def languages_cb_handler(client: Client, query: CallbackQuery):
    _, key, offset, req = query.data.split("#")
    if int(req) != query.from_user.id:
        return await query.answer(script.ALRT_TXT, show_alert=True)

    btn = [[
        InlineKeyboardButton(text=lang.title(), callback_data=f"lang_search#{lang.lower()}#{key}#0#{offset}#{req}"),
    ]
        for lang in LANGUAGES
    ]
    btn.append([InlineKeyboardButton(text="⪻ ʙᴀᴄᴋ ᴛᴏ ᴍᴀɪɴ ᴘᴀɢᴇ", callback_data=f"next_{req}_{key}_{offset}")])
    try:
        await query.message.edit_text("<b>ɪɴ ᴡʜɪᴄʜ ʟᴀɴɢᴜᴀɢᴇ ʏᴏᴜ ᴡᴀɴᴛ, ᴄʜᴏᴏsᴇ ʜᴇʀᴇ 👇</b>", reply_markup=InlineKeyboardMarkup(btn))
    except MessageNotModified:
        await query.answer()
    except Exception as e:
        logging.error(f"Error in languages_cb_handler: {e}")

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

    files, n_offset, total = await get_search_results(search, max_results=int(MAX_BTN), offset=offset, lang=lang)
    try:
        n_offset = int(n_offset)
    except:
        n_offset = 0

    if not files:
        await query.answer(f"sᴏʀʀʏ '{lang.title()}' ʟᴀɴɢᴜᴀɢᴇ ꜰɪʟᴇs ɴᴏᴛ ꜰᴏᴜɴᴅ 😕", show_alert=1)
        return

    batch_ids = files
    temp.FILES_ID[f"{query.message.chat.id}-{query.id}"] = batch_ids
    batch_link = f"batchfiles#{query.message.chat.id}#{query.id}#{query.from_user.id}"

    reqnxt = query.from_user.id
    settings = await get_settings(query.message.chat.id)
    group_id = query.message.chat.id
    temp.CHAT[query.from_user.id] = query.message.chat.id
    del_msg = f"\n\n<b>⚠️ ᴛʜɪs ᴍᴇssᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ ᴀꜰᴛᴇʀ <code>{get_readable_time(DELETE_TIME)}</code> ᴛᴏ ᴀᴠᴏɪᴅ ᴄᴏᴘʏʀɪɢʜᴛ ɪssᴜᴇs</b>" if settings["auto_delete"] else ''
    links = ""
    btn = []

    if settings["link"]:
        for file_num, file in enumerate(files, start=offset+1):
            links += f"""<b>\n\n{file_num}. <a href=https://t.me/{temp.U_NAME}?start=file_{query.message.chat.id}_{file.file_id}>[{get_size(file.file_size)}] {' '.join(filter(lambda x: not x.startswith('[') and not x.startswith('@') and not x.startswith('www.'), file.file_name.split()))}</a></b>"""
    else:
        btn = [[
                InlineKeyboardButton(text=f"🔗 {get_size(file.file_size)}≽ {get_name(file.file_name)}", url=f'https://telegram.dog/{temp.U_NAME}?start=file_{query.message.chat.id}_{file.file_id}'),]
                   for file in files
              ]

    btn.insert(0, [
            InlineKeyboardButton("♻️ sᴇɴᴅ ᴀʟʟ ♻️", callback_data=batch_link),
            InlineKeyboardButton("🥇ʙᴜʏ🥇", url=f"https://t.me/{temp.U_NAME}?start=buy_premium")
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

    page_num_text = f"{math.ceil(offset / int(MAX_BTN)) + 1}/{math.ceil(total / int(MAX_BTN))}"
    pagination_buttons.append(InlineKeyboardButton(page_num_text, callback_data="pages"))

    if n_offset != 0 and n_offset != '': # Check if next offset is valid
        pagination_buttons.append(InlineKeyboardButton("ɴᴇxᴛ ⪼", callback_data=f"lang_search#{lang}#{key}#{n_offset}#{orginal_offset}#{req}"))
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
         logging.error(f"Error editing message in lang_search: {e}")
         await query.answer("An error occurred while updating results.", show_alert=True)


# --- NEW QUALITY FILTER HANDLERS ---
@Client.on_callback_query(filters.regex(r"^qualities#"))
async def qualities_cb_handler(client: Client, query: CallbackQuery):
    _, key, offset, req = query.data.split("#")
    if int(req) != query.from_user.id:
        return await query.answer(script.ALRT_TXT, show_alert=True)

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

    reqnxt = query.from_user.id
    settings = await get_settings(query.message.chat.id)
    group_id = query.message.chat.id
    temp.CHAT[query.from_user.id] = query.message.chat.id
    del_msg = f"\n\n<b>⚠️ ᴛʜɪs ᴍᴇssᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ ᴀꜰᴛᴇʀ <code>{get_readable_time(DELETE_TIME)}</code> ᴛᴏ ᴀᴠᴏɪᴅ ᴄᴏᴘʏʀɪɢʜᴛ ɪssᴜᴇs</b>" if settings["auto_delete"] else ''
    links = ""
    btn = []

    if settings["link"]:
        for file_num, file in enumerate(files, start=offset+1):
            links += f"""<b>\n\n{file_num}. <a href=https://t.me/{temp.U_NAME}?start=file_{query.message.chat.id}_{file.file_id}>[{get_size(file.file_size)}] {' '.join(filter(lambda x: not x.startswith('[') and not x.startswith('@') and not x.startswith('www.'), file.file_name.split()))}</a></b>"""
    else:
        btn = [[
                InlineKeyboardButton(text=f"🔗 {get_size(file.file_size)}≽ {get_name(file.file_name)}", url=f'https://telegram.dog/{temp.U_NAME}?start=file_{query.message.chat.id}_{file.file_id}'),]
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

    page_num_text = f"{math.ceil(offset / int(MAX_BTN)) + 1}/{math.ceil(total / int(MAX_BTN))}"
    pagination_buttons.append(InlineKeyboardButton(page_num_text, callback_data="pages"))

    if n_offset != 0 and n_offset != '': # Check if next offset is valid
        pagination_buttons.append(InlineKeyboardButton("ɴᴇxᴛ ⪼", callback_data=f"qual_search#{quality}#{key}#{n_offset}#{orginal_offset}#{req}"))
    elif total > int(MAX_BTN) and not pagination_buttons: # First page, no next, but more pages exist conceptually (though maybe not reachable with MAX_BTN limit)
         pass # No button needed if only one page of results shown
    elif not pagination_buttons : # No back and no next needed
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

# --- END NEW QUALITY FILTER HANDLERS ---

@Client.on_callback_query(filters.regex(r"^spol"))
async def advantage_spoll_choker(bot, query):
    _, id, user = query.data.split('#')
    if int(user) != 0 and query.from_user.id != int(user):
        return await query.answer(script.ALRT_TXT, show_alert=True)
    movie = await get_poster(id, id=True)
    search = movie.get('title') if movie else None
    if not search:
        await query.answer('Could not find movie details.', show_alert=True)
        return
    await query.answer('ᴄʜᴇᴄᴋɪɴɢ ɪɴ ᴍʏ ᴅᴀᴛᴀʙᴀꜱᴇ 🌚')
    files, offset, total_results = await get_search_results(search)
    if files:
        k = (search, files, offset, total_results)
        await auto_filter(bot, query, k)
    else:
        k = await query.message.edit(script.NO_RESULT_TXT)
        await asyncio.sleep(60)
        try: await k.delete()
        except: pass
        try:
            if query.message.reply_to_message:
                 await query.message.reply_to_message.delete()
        except: pass


@Client.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):

    if query.data == "close_data":
        try:
            user_id_to_check = query.message.reply_to_message.from_user.id
        except AttributeError:
             user_id_to_check = query.message.from_user.id

        is_admin = await is_check_admin(client, query.message.chat.id, query.from_user.id) if query.message.chat.type != enums.ChatType.PRIVATE else False

        if query.from_user.id == user_id_to_check or is_admin:
            await query.answer("ᴛʜᴀɴᴋs ꜰᴏʀ ᴄʟᴏsᴇ 🙈")
            await query.message.delete()
            try:
                if query.message.reply_to_message:
                    await query.message.reply_to_message.delete()
            except Exception as e:
                logging.debug(f"Could not delete reply_to_message: {e}")
        else:
            return await query.answer(script.ALRT_TXT, show_alert=True)

    elif query.data == "delallcancel":
        userid = query.from_user.id
        chat_type = query.message.chat.type
        is_owner_or_admin = str(userid) in ADMINS
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
             await query.answer(script.ALRT_TXT, show_alert=True)


    elif query.data.startswith("checksub"):
        chat_id = temp.CHAT.get(query.from_user.id) # Get chat_id from temp dict
        if not chat_id:
             logging.warning(f"Chat ID not found in temp for user {query.from_user.id} during checksub.")
             # Try getting chat_id from the message context if available (might be PM)
             chat_id = query.message.chat.id
             if not chat_id:
                  return await query.answer("Could not determine context. Please try requesting the file again from the group.", show_alert=True)


        ident, file_id = query.data.split("#")
        settings = await get_settings(chat_id) # Use retrieved chat_id

        if AUTH_CHANNEL and not await is_req_subscribed(client, query):
            await query.answer("ɪ ʟɪᴋᴇ ʏᴏᴜʀ sᴍᴀʀᴛɴᴇss ʙᴜᴛ ᴅᴏɴ'ᴛ ʙᴇ ᴏᴠᴇʀsᴍᴀʀᴛ 😒\nꜰɪʀsᴛ ᴊᴏɪɴ ᴏᴜʀ ᴜᴘᴅᴀᴛᴇs ᴄʜᴀɴɴᴇʟ 😒", show_alert=True)
            return

        files_ = await get_file_details(file_id)
        if not files_:
            return await query.answer('ɴᴏ sᴜᴄʜ ꜰɪʟᴇ ᴇxɪsᴛs 🚫', show_alert=True)
        files = files_[0]
        CAPTION = settings['caption']
        f_caption = CAPTION.format(
            file_name = files.file_name,
            file_size = get_size(files.file_size),
            file_caption = files.caption if files.caption else ""
        )
        try:
             await client.send_cached_media(
                 chat_id=query.from_user.id,
                 file_id=file_id,
                 caption=f_caption,
                 protect_content=settings.get('file_secure', False), # Use get with default
             )
             await query.message.delete()
        except Exception as e:
             logging.error(f"Error sending file in checksub: {e}")
             await query.answer("Could not send the file. Please try again.", show_alert=True)


    elif query.data.startswith("stream"):
        user_id = query.from_user.id
        if not await db.has_premium_access(user_id) and not await db.check_referral_access(user_id):
            d=await query.message.reply("<b>💔 ᴛʜɪꜱ ғᴇᴀᴛᴜʀᴇ ɪꜱ ᴏɴʟʏ ғᴏʀ ᴘʀᴇᴍɪᴜᴍ/ʀᴇғᴇʀʀᴀʟ ᴜꜱᴇʀꜱ.\n\n🪙 /plan ᴛᴏ ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ\n🔗 /start ᴛᴏ ɢᴇᴛ ʀᴇғᴇʀʀᴀʟ ʟɪɴᴋ</b>")
            await asyncio.sleep(10)
            try: await d.delete()
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

    elif query.data.startswith("lang_art"):
        _, lang = query.data.split("#")
        await query.answer(f"ʏᴏᴜ sᴇʟᴇᴄᴛᴇᴅ {lang.title()} ʟᴀɴɢᴜᴀɢᴇ ⚡️", show_alert=True)

    elif query.data == "start":
        buttons = [[
            InlineKeyboardButton('⇆ ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘs ⇆', url=f'http://t.me/{temp.U_NAME}?startgroup=start')
        ],[
            InlineKeyboardButton('⚙ ꜰᴇᴀᴛᴜʀᴇs', callback_data='features'),
            InlineKeyboardButton('💸 ᴘʀᴇᴍɪᴜᴍ', callback_data='buy_premium')
        ],[
            InlineKeyboardButton(script.REFERRAL_BUTTON_TEXT, callback_data='referral')
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
                  text=script.EARN_TEXT.format(temp.B_NAME),
                  reply_markup=reply_markup,
                  parse_mode=enums.ParseMode.HTML,
                  disable_web_page_preview=True
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

    elif query.data == "buy_premium":
        btn = [[
            InlineKeyboardButton('📸 sᴇɴᴅ sᴄʀᴇᴇɴsʜᴏᴛ 📸', url=USERNAME)
        ],[
            InlineKeyboardButton('🗑 ᴄʟᴏsᴇ 🗑', callback_data='close_data')
        ]]
        reply_markup = InlineKeyboardMarkup(btn)
        try:
            # Attempt to delete the old message and send a new photo message
            await query.message.delete()
            await query.message.reply_photo(
                photo=(QR_CODE),
                caption=script.PREMIUM_TEXT.format(mention=query.from_user.mention),
                reply_markup=reply_markup,
            )
        except Exception as e:
            logging.error(f"Error sending premium photo: {e}")
            # Fallback: Try editing the text if deletion/sending fails
            try:
                await query.message.edit_text(
                    script.PREMIUM_TEXT.format(mention=query.from_user.mention),
                    reply_markup=reply_markup,
                    disable_web_page_preview=True # Good for text fallback
                )
            except Exception as inner_e:
                logging.error(f"Fallback error in buy_premium callback: {inner_e}")
                await query.answer("Could not display premium info.", show_alert=True)


    elif query.data == "referral":
        try:
            user_data = await db.get_user_data(query.from_user.id)
            if not user_data:
                 await db.add_user(query.from_user.id, query.from_user.first_name)
                 user_data = await db.get_user_data(query.from_user.id)

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
                except Exception as link_e:
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

    elif query.data == "all_files_delete":
        if str(query.from_user.id) not in ADMINS:
             return await query.answer("Only admins can perform this action.", show_alert=True)
        files_count = await Media.count_documents()
        await query.answer(f'Deleting {files_count} files...')
        await Media.collection.drop() # More efficient for deleting all
        await query.message.edit_text(f"✅ Successfully deleted {files_count} files from the database.")


    elif query.data.startswith("killfilesak"):
        if str(query.from_user.id) not in ADMINS:
             return await query.answer("Only admins can perform this action.", show_alert=True)
        ident, keyword = query.data.split("#")
        await query.message.edit_text(f"<b>🔍 Fetching files for query '{keyword}'...\n\nPlease wait...</b>")
        files, total = await get_bad_files(keyword)
        if total == 0:
             return await query.message.edit_text(f"⚠️ No files found matching '{keyword}'.")

        await query.message.edit_text(f"<b>✅ Found {total} files for query '{keyword}'!\nStarting deletion process...</b>")

        deleted = 0
        async with lock:
            try:
                delete_start_time = time.time()
                for file in files:
                    file_ids = file.file_id
                    # file_name = file.file_name # Not needed for deletion by ID
                    result = await Media.collection.delete_one({'_id': file_ids})
                    if result.deleted_count:
                        deleted += 1

                    # Update status less frequently
                    if deleted % 50 == 0 and (time.time() - delete_start_time) > 5:
                        try:
                            await query.message.edit_text(f"<b>🗑 Deletion in progress for '{keyword}'...\nDeleted {deleted} / {total} files!\n\nPlease wait...</b>")
                            delete_start_time = time.time()
                        except (MessageNotModified, FloodWait): pass # Ignore these errors during status update
                        except Exception as edit_e:
                             logging.warning(f"Could not edit killfiles status: {edit_e}")
                             break # Stop if editing fails

            except Exception as e:
                logging.error(f"Error during killfiles deletion: {e}")
                await query.message.edit_text(f'❌ Error during deletion: {e}')
            else:
                await query.message.edit_text(f"<b>✅ Process Completed for '{keyword}'!\n\nSuccessfully deleted {deleted} / {total} files from database.</b>")


    elif query.data.startswith("reset_grp_data"):
        grp_id = query.message.chat.id
        if not await is_check_admin(client, grp_id, query.from_user.id):
             return await query.answer("Only group admins can reset settings.", show_alert=True)
        btn = [[
            InlineKeyboardButton('☕️ ᴄʟᴏsᴇ ☕️', callback_data='close_data')
        ]]
        reply_markup=InlineKeyboardMarkup(btn)

        # Reset using the default dictionary from db class
        await db.update_settings(grp_id, db.default)

        await query.answer('ꜱᴜᴄᴄᴇꜱꜱғᴜʟʟʏ ʀᴇꜱᴇᴛ...')
        await query.message.edit_text("<b>✅️ ꜱᴜᴄᴄᴇꜱꜱғᴜʟʟʏ ʀᴇꜱᴇᴛ ɢʀᴏᴜᴘ ꜱᴇᴛᴛɪɴɢꜱ ᴛᴏ ᴅᴇꜰᴀᴜʟᴛ.\n\nɴᴏᴡ ꜱᴇɴᴅ /details ᴀɢᴀɪɴ ᴛᴏ ᴠɪᴇᴡ.</b>", reply_markup=reply_markup)

    elif query.data.startswith("setgs"):
            ident, set_type, status, grp_id_str = query.data.split("#")
            grp_id = int(grp_id_str)
            userid = query.from_user.id if query.from_user else None
            if not await is_check_admin(client, grp_id, userid):
                await query.answer(script.ALRT_TXT, show_alert=True)
                return

            new_status = False if status == "True" else True
            await save_group_settings(grp_id, set_type, new_status)

            await query.answer(f"{set_type.replace('_',' ').title()} turned {'ON ✅' if new_status else 'OFF ❌'}")

            settings = await get_settings(grp_id)
            if settings is not None:
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
                    InlineKeyboardButton('ʀᴇsᴜʟᴛ ᴍᴏᴅᴇ', callback_data=f'setgs#link#{settings["link"]}#{grp_id_str}'),
                    InlineKeyboardButton('ʟɪɴᴋ' if settings["link"] else 'ʙᴜᴛᴛᴏɴ', callback_data=f'setgs#link#{settings["link"]}#{grp_id_str}')
                ],[
                    InlineKeyboardButton('ᴠᴇʀɪғʏ', callback_data=f'setgs#is_verify#{settings["is_verify"]}#{grp_id}'),
                    InlineKeyboardButton('ᴏɴ ✔️' if settings["is_verify"] else 'ᴏғғ ✗', callback_data=f'setgs#is_verify#{settings["is_verify"]}#{grp_id}')
                ],[
                    InlineKeyboardButton('☕️ ᴄʟᴏsᴇ ☕️', callback_data='close_data')
                ]]
                reply_markup = InlineKeyboardMarkup(buttons)
                try:
                     await query.message.edit_reply_markup(reply_markup)
                     # Auto-close settings panel after some time (optional)
                     # await asyncio.sleep(300)
                     # await query.message.delete()
                except MessageNotModified:
                     pass
                except Exception as e:
                     logging.error(f"Error editing settings markup: {e}")
                     # Don't show alert here, just log it
            else:
                await query.message.edit_text("<b>❌ ꜱᴏᴍᴇᴛʜɪɴɢ ᴡᴇɴᴛ ᴡʀᴏɴɢ getting settings after update.</b>")

    # --- Request Channel Handlers ---
    elif query.data.startswith("show_options"):
        if not REQUEST_CHANNEL: return await query.answer("Request system disabled.", show_alert=True)
        ident, user_id, msg_id = query.data.split("#")
        chnl_id = query.message.chat.id
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
            else:
                await query.answer(script.ALRT_TXT, show_alert=True)
        except UserNotParticipant:
            await query.answer("⚠️ You need to be a member of the request channel to manage requests.", show_alert=True)
        except Exception as e:
            logging.error(f"Error in show_options: {e}")
            await query.answer("An error occurred.", show_alert=True)


    elif query.data.startswith("reject"):
        await update_request_status(query, client, "Rejected", "Sᴏʀʀʏ, ʏᴏᴜʀ ʀᴇǫᴜᴇsᴛ ᴡᴀs ʀᴇᴊᴇᴄᴛᴇᴅ 😶", "🚫") # Use helper

    elif query.data.startswith("accept"):
        if not REQUEST_CHANNEL: return await query.answer("Request system disabled.", show_alert=True)
        ident, user_id, msg_id = query.data.split("#")
        chnl_id = query.message.chat.id
        userid = query.from_user.id
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
            InlineKeyboardButton("🔙 Back to Options", callback_data=f"show_options#{user_id}#{msg_id}")
        ]]
        try:
            st = await client.get_chat_member(chnl_id, userid)
            if st.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
                # Check if already processed
                if query.message.text.startswith("<s>"):
                     return await query.answer("This request was already processed.", show_alert=True)
                await query.message.edit_reply_markup(InlineKeyboardMarkup(buttons))
                await query.answer("Select status...")
            else:
                await query.answer(script.ALRT_TXT, show_alert=True)
        except UserNotParticipant:
            await query.answer("⚠️ You need to be a member of the request channel.", show_alert=True)
        except Exception as e:
            logging.error(f"Error in accept callback: {e}")
            await query.answer("An error occurred.", show_alert=True)

    # Simplified status handlers using the moved helper function
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

    # --- Alert Handlers (using moved helper function) ---
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

        file_keys = f"{group_id}-{message_id}"
        files_to_send = temp.FILES_ID.get(file_keys)

        if not files_to_send:
             await query.answer("Sorry, the file list for this request has expired or could not be found.", show_alert=True)
             return

        batch_key = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        temp.FILES_ID[batch_key] = files_to_send # Store files under the new key

        link = f"https://telegram.me/{temp.U_NAME}?start=allfiles_{batch_key}"
        await query.answer(f"Click OK to get all {len(files_to_send)} files.", url=link, cache_time=0)
        return

async def auto_filter(client, msg, spoll=False):
    message = None # Initialize message
    settings = None # Initialize settings
    search = "" # Initialize search
    files = [] # Initialize files
    offset = "" # Initialize offset
    total_results = 0 # Initialize total_results

    if not spoll:
        message = msg
        search = message.text
        chat_id = message.chat.id
        settings = await get_settings(chat_id)
        files, offset, total_results = await get_search_results(search)
        if not files:
            if settings.get("spell_check", True): # Use get with default
                return await advantage_spell_chok(msg)
            else:
                 return # Do nothing if no files and spell check off
    else: # If spoll is True (coming from callback query)
        settings = await get_settings(msg.message.chat.id)
        message = msg.message.reply_to_message # Original user message
        if not message: # Handle case where original message was deleted
             await msg.answer("The original message seems to be missing.", show_alert=True)
             return
        search, files, offset, total_results = spoll # Unpack spoll data

    if not files: # Final check if files list is empty
         return

    req = message.from_user.id if message.from_user else 0
    key = f"{message.chat.id}-{message.id}"

    BUTTONS[key] = search # Store original search query
    CAP[key] = "" # Initialize caption

    batch_ids = files
    temp.FILES_ID[f"{message.chat.id}-{message.id}"] = batch_ids
    batch_link = f"batchfiles#{message.chat.id}#{message.id}#{req}"

    temp.CHAT[req] = message.chat.id

    del_msg = f"\n\n<b>⚠️ ᴛʜɪs ᴍᴇssᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ ᴀꜰᴛᴇʀ <code>{get_readable_time(DELETE_TIME)}</code> ᴛᴏ ᴀᴠᴏɪᴅ ᴄᴏᴘʏʀɪɢʜᴛ ɪssᴜᴇs</b>" if settings.get("auto_delete", False) else '' # Use get
    links = ""
    btn = []

    if settings.get("link", True): # Use get
        for file_num, file in enumerate(files, start=1):
            file_link = f"https://t.me/{temp.U_NAME}?start=file_{message.chat.id}_{file.file_id}"
            file_name_display = ' '.join(filter(lambda x: not x.startswith('[') and not x.startswith('@') and not x.startswith('www.'), file.file_name.split()))
            links += f"""<b>\n\n{file_num}. <a href={file_link}>[{get_size(file.file_size)}] {file_name_display}</a></b>"""
    else:
        btn = [[InlineKeyboardButton(text=f"🔗 {get_size(file.file_size)}≽ {get_name(file.file_name)}", url=f'https://telegram.dog/{temp.U_NAME}?start=file_{message.chat.id}_{file.file_id}'),]
               for file in files
              ]

    # --- Insert Top Buttons ---
    filter_buttons = []
    if total_results > 0:
        filter_buttons.append(InlineKeyboardButton("📰 ʟᴀɴɢᴜᴀɢᴇs", callback_data=f"languages#{key}#0#{req}"))
        filter_buttons.append(InlineKeyboardButton("🎞️ ǫᴜᴀʟɪᴛʏ", callback_data=f"qualities#{key}#0#{req}"))
    if filter_buttons:
        btn.insert(0, filter_buttons)

    top_buttons = []
    if total_results >= 3:
        top_buttons.append(InlineKeyboardButton("♻️ sᴇɴᴅ ᴀʟʟ", callback_data=batch_link))
    top_buttons.append(InlineKeyboardButton("🥇ʙᴜʏ🥇", url=f"https://t.me/{temp.U_NAME}?start=buy_premium"))
    if top_buttons:
        btn.insert(0, top_buttons)

    # --- Append Utility Buttons ---
    btn.append([InlineKeyboardButton("🤔 ʜᴏᴡ ᴛᴏ ᴅᴏᴡɴʟᴏᴀᴅ 🤔", url=settings.get('tutorial', '#'))]) # Use get with default '#'
    btn.append([InlineKeyboardButton(script.REFERRAL_BUTTON_TEXT, callback_data='referral')])

    # --- Pagination ---
    if offset != "" and offset is not None: # Ensure offset is valid for pagination logic
        try:
             current_page = 1 # First page initially
             total_pages = math.ceil(int(total_results) / int(MAX_BTN))
             pagination_buttons = []
             if total_pages > 1: # Only add pagination if needed
                  pagination_buttons.append(InlineKeyboardButton(text=f"1/{total_pages}", callback_data="pages"))
                  pagination_buttons.append(InlineKeyboardButton(text="ɴᴇxᴛ ⪼", callback_data=f"next_{req}_{key}_{offset}"))
             if pagination_buttons:
                  btn.append(pagination_buttons)
        except Exception as page_e:
             logging.error(f"Error calculating pagination: {page_e}")


    # --- IMDB and Caption ---
    imdb = await get_poster(search, file=(files[0]).file_name) if settings.get("imdb", False) and files else None
    TEMPLATE = settings.get('template', script.IMDB_TEMPLATE_TXT) # Use get with default
    cap = ""

    if imdb:
        # Use .get with default values for all imdb fields to prevent KeyError
        cap = TEMPLATE.format(
            query=search,
            title=imdb.get('title', "N/A"),
            votes=imdb.get('votes', "N/A"),
            aka=imdb.get("aka", "N/A"),
            seasons=imdb.get("seasons", "N/A"),
            box_office=imdb.get('box_office', "N/A"),
            localized_title=imdb.get('localized_title', "N/A"),
            kind=imdb.get("kind", "N/A"),
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
            poster=imdb.get('poster', ""),
            plot=imdb.get('plot', "N/A"),
            rating=imdb.get('rating', "N/A"),
            url=imdb.get('url', "#"),
        )
    else:
        cap = f"<b>📂 Here is what I found for '{search}'</b>" # Simplified message

    CAP[key] = cap # Store generated caption

    final_caption = cap + links + del_msg if settings.get("link", True) else cap + del_msg
    reply_markup = InlineKeyboardMarkup(btn) if btn else None

    # --- Sending/Editing Logic ---
    sent_message = None

    if spoll: # Handle callback query editing
        try:
            target_message = msg.message # The message with the buttons
            if imdb and imdb.get('poster'):
                 sent_message = await target_message.edit_media(
                      media=InputMediaPhoto(imdb.get('poster'), caption=final_caption[:1024]),
                      reply_markup=reply_markup
                 )
            else:
                 sent_message = await target_message.edit_text(
                      text=final_caption,
                      reply_markup=reply_markup,
                      disable_web_page_preview=True,
                      parse_mode=enums.ParseMode.HTML
                 )
        except FloodWait as fw:
            await asyncio.sleep(fw.value)
            # Retry after floodwait
            return await auto_filter(client, msg, spoll)
        except MessageNotModified:
            pass # Ignore if message wasn't changed
        except Exception as e:
            logging.error(f"Error editing message after spell check: {e}")
            # Optionally send new message as fallback here if needed
        return # Important to return after handling spoll

    # --- Handle regular message reply ---
    try:
        if imdb and imdb.get('poster'):
            sent_message = await message.reply_photo(
                photo=imdb.get('poster'),
                caption=final_caption[:1024],
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
    # Handle media errors gracefully
    except (MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty) as media_err:
        logging.warning(f"Media error sending poster for '{search}': {media_err}. Trying smaller poster or text.")
        pic = imdb.get('poster') if imdb else None
        poster = pic.replace('.jpg', "._V1_UX360.jpg") if pic else None
        if poster:
            try:
                sent_message = await message.reply_photo(photo=poster, caption=final_caption[:1024], parse_mode=enums.ParseMode.HTML, reply_markup=reply_markup, reply_to_message_id=message.id)
            except Exception as e:
                 logging.error(f"Error sending smaller poster: {e}. Falling back to text.")
                 sent_message = await message.reply_text(text=final_caption, disable_web_page_preview=True, parse_mode=enums.ParseMode.HTML, reply_markup=reply_markup, reply_to_message_id=message.id)
        else: # No poster or smaller poster failed
             sent_message = await message.reply_text(text=final_caption, disable_web_page_preview=True, parse_mode=enums.ParseMode.HTML, reply_markup=reply_markup, reply_to_message_id=message.id)
    except FloodWait as fw:
         await asyncio.sleep(fw.value)
         # Retry after floodwait
         return await auto_filter(client, msg, spoll=False) # Retry the original call
    except Exception as e:
        logging.error(f"General error sending auto_filter message for '{search}': {e}")
        try: # Final fallback to simple text message
             sent_message = await message.reply_text(f"Found results for '{search}'. Please check the buttons.", reply_markup=reply_markup, reply_to_message_id=message.id)
        except Exception as fallback_e:
             logging.critical(f"FATAL: Could not send any response for '{search}': {fallback_e}")


    # Auto-delete logic
    if settings.get('auto_delete', False) and sent_message:
        await asyncio.sleep(DELETE_TIME)
        try: await sent_message.delete()
        except: pass
        try: await message.delete() # Delete user trigger message
        except: pass


async def advantage_spell_chok(message):
    search = message.text
    settings = await get_settings(message.chat.id) # Use message.chat.id

    # More robust query cleaning
    query = re.sub(r"(\b(pl(i|e)*?(s|z+|ease|se|ese)|send|snd|giv(e)?|gib)(\s*me)?\b)|(\b(movie|series|tv|show|hindi|eng|english|tamil|telugu|malayalam|kannada|dubbed|watch|online|download|free|full|hd|4k|1080p|720p|480p|bluray|webrip|dvdrip|episode|\d{1,3})\b)|[._\-]", " ", search, flags=re.IGNORECASE)
    query = ' '.join(query.split()).strip() # Remove extra spaces

    if not query: query = search # Fallback

    try:
        movies = await get_poster(query, bulk=True)
    except Exception as e:
        logging.error(f"Error getting posters for spell check '{query}': {e}")
        # Don't delete message immediately, user might want to see the error
        await message.reply(script.I_CUDNT.format(message.from_user.mention))
        return

    if not movies:
        google_query = search.replace(" ", "+")
        button = [[
            InlineKeyboardButton("🔍 ᴄʜᴇᴄᴋ sᴘᴇʟʟɪɴɢ ᴏɴ ɢᴏᴏɢʟᴇ 🔍", url=f"https://www.google.com/search?q={google_query}")
        ]]
        k = await message.reply_text(text=script.I_CUD_NT.format(message.from_user.mention), reply_markup=InlineKeyboardMarkup(button)) # Use specific 'not found' message
        # Auto-delete Google suggestion
        await asyncio.sleep(120)
        try: await k.delete()
        except: pass
        # Don't delete original user message here
        return

    user = message.from_user.id if message.from_user else 0
    buttons = [[
        InlineKeyboardButton(
            text=f"{movie.get('title', 'Unknown Title')} ({movie.get('year', 'N/A')})", # Add defaults
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
         reply_to_message_id=message.id
    )

    # Auto-delete the suggestion message after a while
    await asyncio.sleep(120) # Consider making this duration configurable
    try: await d.delete()
    except: pass
    # Do not delete the original user message
