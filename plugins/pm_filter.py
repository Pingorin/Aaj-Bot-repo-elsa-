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
from info import MAX_BTN, BIN_CHANNEL, USERNAME, URL, ADMINS, LANGUAGES, AUTH_CHANNEL, SUPPORT_GROUP, IMDB, IMDB_TEMPLATE, LOG_CHANNEL, LOG_VR_CHANNEL, TUTORIAL, FILE_CAPTION, SHORTENER_WEBSITE, SHORTENER_API, SHORTENER_WEBSITE2, SHORTENER_API2, IS_PM_SEARCH, QR_CODE, DELETE_TIME
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, InputMediaPhoto, ChatPermissions
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait, UserIsBlocked, MessageNotModified, PeerIdInvalid, ChatAdminRequired
from utils import temp, get_settings, is_check_admin, get_status, get_hash, get_name, get_size, save_group_settings, is_req_subscribed, get_poster, get_status, get_readable_time
from database.users_chats_db import db
from database.ia_filterdb import Media, get_search_results, get_bad_files, get_file_details

lock = asyncio.Lock()

BUTTONS = {}
FILES_ID = {}
CAP = {}

@Client.on_message(filters.private & filters.text & filters.incoming)
async def pm_search(client, message):
    if IS_PM_SEARCH:
        if 'hindi' in message.text.lower() or 'tamil' in message.text.lower() or 'telugu' in message.text.lower() or 'malayalam' in message.text.lower() or 'kannada' in message.text.lower() or 'english' in message.text.lower() or 'gujarati' in message.text.lower(): 
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
        
        if 'hindi' in message.text.lower() or 'tamil' in message.text.lower() or 'telugu' in message.text.lower() or 'malayalam' in message.text.lower() or 'kannada' in message.text.lower() or 'english' in message.text.lower() or 'gujarati' in message.text.lower(): 
            return await auto_filter(client, message)

        if message.text.startswith("/"):
            return
        
        elif re.findall(r'https?://\S+|www\.\S+|t\.me/\S+', message.text):
            if await is_check_admin(client, message.chat.id, message.from_user.id):
                return
            await message.delete()
            return await message.reply('<b>‼️ ᴡʜʏ ʏᴏᴜ ꜱᴇɴᴅ ʜᴇʀᴇ ʟɪɴᴋ\nʟɪɴᴋ ɴᴏᴛ ᴀʟʟᴏᴡᴇᴅ ʜᴇʀᴇ 🚫</b>')

        elif '@admin' in message.text.lower() or '@admins' in message.text.lower():
            if await is_check_admin(client, message.chat.id, message.from_user.id):
                return
            admins = []
            async for member in client.get_chat_members(chat_id=message.chat.id, filter=enums.ChatMembersFilter.ADMINISTRATORS):
                if not member.user.is_bot:
                    admins.append(member.user.id)
                    if member.status == enums.ChatMemberStatus.OWNER:
                        if message.reply_to_message:
                            try:
                                sent_msg = await message.reply_to_message.forward(member.user.id)
                                await sent_msg.reply_text(f"#Attention\n★ User: {message.from_user.mention}\n★ Group: {message.chat.title}\n\n★ <a href={message.reply_to_message.link}>Go to message</a>", disable_web_page_preview=True)
                            except:
                                pass
                        else:
                            try:
                                sent_msg = await message.forward(member.user.id)
                                await sent_msg.reply_text(f"#Attention\n★ User: {message.from_user.mention}\n★ Group: {message.chat.title}\n\n★ <a href={message.link}>Go to message</a>", disable_web_page_preview=True)
                            except:
                                pass
            hidden_mentions = (f'[\u2064](tg://user?id={user_id})' for user_id in admins)
            await message.reply_text('<code>Report sent</code>' + ''.join(hidden_mentions))
            return
        else:
            await auto_filter(client, message)   
    else:
        k=await message.reply_text('<b>⚠️ ᴀᴜᴛᴏ ғɪʟᴛᴇʀ ᴍᴏᴅᴇ ɪꜱ ᴏғғ...</b>')
        await asyncio.sleep(10)
        await k.delete()
        try:
            await message.delete()
        except:
            pass

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
        return
    temp.FILES_ID[key] = files
    
    batch_ids = files
    temp.FILES_ID[f"{query.message.chat.id}-{query.id}"] = batch_ids
    batch_link = f"batchfiles#{query.message.chat.id}#{query.id}#{query.from_user.id}"

    settings = await get_settings(query.message.chat.id)
    reqnxt  = query.from_user.id if query.from_user else 0
    temp.CHAT[query.from_user.id] = query.message.chat.id
    del_msg = f"\n\n<b>⚠️ ᴛʜɪs ᴍᴇssᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ ᴀꜰᴛᴇʀ <code>{get_readable_time(DELETE_TIME)}</code> ᴛᴏ ᴀᴠᴏɪᴅ ᴄᴏᴘʏʀɪɢʜᴛ ɪssᴜᴇs</b>" if settings["auto_delete"] else ''
    links = ""
    if settings["link"]:
        btn = []
        for file_num, file in enumerate(files, start=offset+1):
            links += f"""<b>\n\n{file_num}. <a href=https://t.me/{temp.U_NAME}?start=file_{query.message.chat.id}_{file.file_id}>[{get_size(file.file_size)}] {' '.join(filter(lambda x: not x.startswith('[') and not x.startswith('@') and not x.startswith('www.'), file.file_name.split()))}</a></b>"""
    else:
        btn = [[InlineKeyboardButton(text=f"🔗 {get_size(file.file_size)}≽ {get_name(file.file_name)}", url=f'https://telegram.dog/{temp.U_NAME}?start=file_{query.message.chat.id}_{file.file_id}'),]
                for file in files
              ]
    btn.insert(0,[
        InlineKeyboardButton("♻️ sᴇɴᴅ ᴀʟʟ", callback_data=batch_link),
        InlineKeyboardButton("🥇ʙᴜʏ🥇", url=f"https://t.me/{temp.U_NAME}?start=buy_premium"),
        InlineKeyboardButton("📰 ʟᴀɴɢᴜᴀɢᴇs", callback_data=f"languages#{key}#{offset}#{req}")
        ])

    if 0 < offset <= int(MAX_BTN):
        off_set = 0
    elif offset == 0:
        off_set = None
    else:
        off_set = offset - int(MAX_BTN)
    if n_offset == 0:

        btn.append(
            [InlineKeyboardButton("⪻ ʙᴀᴄᴋ", callback_data=f"next_{req}_{key}_{off_set}"),
             InlineKeyboardButton(f"ᴘᴀɢᴇ {math.ceil(int(offset) / int(MAX_BTN)) + 1} / {math.ceil(total / int(MAX_BTN))}", callback_data="pages")]
        )
    elif off_set is None:
        btn.append(
            [InlineKeyboardButton(f"{math.ceil(int(offset) / int(MAX_BTN)) + 1} / {math.ceil(total / int(MAX_BTN))}", callback_data="pages"),
             InlineKeyboardButton("ɴᴇxᴛ ⪼", callback_data=f"next_{req}_{key}_{n_offset}")])
    else:
        btn.append(
            [
                InlineKeyboardButton("⪻ ʙᴀᴄᴋ", callback_data=f"next_{req}_{key}_{off_set}"),
                InlineKeyboardButton(f"{math.ceil(int(offset) / int(MAX_BTN)) + 1} / {math.ceil(total / int(MAX_BTN))}", callback_data="pages"),
                InlineKeyboardButton("ɴᴇxᴛ ⪼", callback_data=f"next_{req}_{key}_{n_offset}")
            ],
        )
    if settings["link"]:
        links = ""
        for file_num, file in enumerate(files, start=offset+1):
            links += f"""<b>\n\n{file_num}. <a href=https://t.me/{temp.U_NAME}?start=file_{query.message.chat.id}_{file.file_id}>[{get_size(file.file_size)}] {' '.join(filter(lambda x: not x.startswith('[') and not x.startswith('@') and not x.startswith('www.'), file.file_name.split()))}</a></b>"""
        await query.message.edit_text(cap + links + del_msg, disable_web_page_preview=True, parse_mode=enums.ParseMode.HTML, reply_markup=InlineKeyboardMarkup(btn))
        return        
    try:
        await query.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup(btn)
        )
    except MessageNotModified:
        pass
    await query.answer()
    
@Client.on_callback_query(filters.regex(r"^languages#"))
async def languages_cb_handler(client: Client, query: CallbackQuery):
    _, key, offset, req = query.data.split("#")
    if int(req) != query.from_user.id:
        return await query.answer(script.ALRT_TXT, show_alert=True)
    if query.message.chat.type == enums.ChatType.PRIVATE:
        return await query.answer('ᴛʜɪs ʙᴜᴛᴛᴏɴ ᴏɴʟʏ ᴡᴏʀᴋ ɪɴ ɢʀᴏᴜᴘ', show_alert=True)
    btn = [[
        InlineKeyboardButton(text=lang.title(), callback_data=f"lang_search#{lang.lower()}#{key}#0#{offset}#{req}"),
    ]
        for lang in LANGUAGES
    ]
    btn.append([InlineKeyboardButton(text="⪻ ʙᴀᴄᴋ ᴛᴏ ᴍᴀɪɴ ᴘᴀɢᴇ", callback_data=f"next_{req}_{key}_{offset}")])
    await query.message.edit_text("<b>ɪɴ ᴡʜɪᴄʜ ʟᴀɴɢᴜᴀɢᴇ ʏᴏᴜ ᴡᴀɴᴛ, ᴄʜᴏᴏsᴇ ʜᴇʀᴇ 👇</b>", reply_markup=InlineKeyboardMarkup(btn))
    return
    d = await query.edit_message_reply_markup(InlineKeyboardMarkup(btn))
    await asyncio.sleep(600)
    await d.delete()

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
    files, n_offset, total = await get_search_results(f"{search} {lang}", max_results=int(MAX_BTN), offset=offset)
    try:
        n_offset = int(n_offset)
    except:
        n_offset = 0
    files = [file for file in files if re.search(lang, file.file_name, re.IGNORECASE)]
    if not files:
        await query.answer(f"sᴏʀʀʏ '{lang.title()}' ʟᴀɴɢᴜᴀɢᴇ ꜰɪʟᴇs ɴᴏᴛ ꜰᴏᴜɴᴅ 😕", show_alert=1)
        return

    batch_ids = files
    temp.FILES_ID[f"{query.message.chat.id}-{query.id}"] = batch_ids
    batch_link = f"batchfiles#{query.message.chat.id}#{query.id}#{query.from_user.id}"

    reqnxt = query.from_user.id if query.from_user else 0
    settings = await get_settings(query.message.chat.id)
    group_id = query.message.chat.id
    temp.CHAT[query.from_user.id] = query.message.chat.id
    del_msg = f"\n\n<b>⚠️ ᴛʜɪs ᴍᴇssᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ ᴀꜰᴛᴇʀ <code>{get_readable_time(DELETE_TIME)}</code> ᴛᴏ ᴀᴠᴏɪᴅ ᴄᴏᴘʏʀɪɢʜᴛ ɪssᴜᴇs</b>" if settings["auto_delete"] else ''
    links = ""
    if settings["link"]:
        btn = []
        for file_num, file in enumerate(files, start=offset+1):
            links += f"""<b>\n\n{file_num}. <a href=https://t.me/{temp.U_NAME}?start=file_{query.message.chat.id}_{file.file_id}>[{get_size(file.file_size)}] {' '.join(filter(lambda x: not x.startswith('[') and not x.startswith('@') and not x.startswith('www.'), file.file_name.split()))}</a></b>"""
    else:
        btn = [[
                InlineKeyboardButton(text=f"🔗 {get_size(file.file_size)}≽ {get_name(file.file_name)}", callback_data=f'files#{reqnxt}#{file.file_id}'),]
                   for file in files
              ]
        
    btn.insert(0, [
            InlineKeyboardButton("♻️ sᴇɴᴅ ᴀʟʟ ♻️", callback_data=batch_link),
            InlineKeyboardButton("🥇ʙᴜʏ🥇", url=f"https://t.me/{temp.U_NAME}?start=buy_premium")
        ])

    if n_offset== '':
        btn.append(
            [InlineKeyboardButton(text="🚸 ɴᴏ ᴍᴏʀᴇ ᴘᴀɢᴇs 🚸", callback_data="buttons")]
        )
    elif n_offset == 0:
        btn.append(
            [InlineKeyboardButton("⪻ ʙᴀᴄᴋ", callback_data=f"lang_search#{lang}#{key}#{offset- int(MAX_BTN)}#{orginal_offset}#{req}"),
             InlineKeyboardButton(f"{math.ceil(offset / int(MAX_BTN)) + 1}/{math.ceil(total / int(MAX_BTN))}", callback_data="pages",),
            ])
    elif offset==0:
        btn.append(
            [InlineKeyboardButton(f"{math.ceil(offset / int(MAX_BTN)) + 1}/{math.ceil(total / int(MAX_BTN))}",callback_data="pages",),
             InlineKeyboardButton("ɴᴇxᴛ ⪼", callback_data=f"lang_search#{lang}#{key}#{n_offset}#{orginal_offset}#{req}"),])
    else:
        btn.append(
            [InlineKeyboardButton("⪻ ʙᴀᴄᴋ", callback_data=f"lang_search#{lang}#{key}#{offset- int(MAX_BTN)}#{orginal_offset}#{req}"),
             InlineKeyboardButton(f"{math.ceil(offset / int(MAX_BTN)) + 1}/{math.ceil(total / int(MAX_BTN))}", callback_data="pages",),
             InlineKeyboardButton("ɴᴇxᴛ ⪼", callback_data=f"lang_search#{lang}#{key}#{n_offset}#{orginal_offset}#{req}"),])

    btn.append([
        InlineKeyboardButton(text="⪻ ʙᴀᴄᴋ ᴛᴏ ᴍᴀɪɴ ᴘᴀɢᴇ", callback_data=f"next_{req}_{key}_{orginal_offset}"),])
    await query.message.edit_text(cap + links + del_msg, disable_web_page_preview=True, parse_mode=enums.ParseMode.HTML, reply_markup=InlineKeyboardMarkup(btn))
    return
    await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(btn))

@Client.on_callback_query(filters.regex(r"^spol"))
async def advantage_spoll_choker(bot, query):
    _, id, user = query.data.split('#')
    if int(user) != 0 and query.from_user.id != int(user):
        return await query.answer(script.ALRT_TXT, show_alert=True)
    movie = await get_poster(id, id=True)
    search = movie.get('title')
    await query.answer('ᴄʜᴇᴄᴋɪɴɢ ɪɴ ᴍʏ ᴅᴀᴛᴀʙᴀꜱᴇ 🌚')
    files, offset, total_results = await get_search_results(search)
    if files:
        k = (search, files, offset, total_results)
        await auto_filter(bot, query, k)
    else:
        k = await query.message.edit(script.NO_RESULT_TXT)
        await asyncio.sleep(60)
        await k.delete()
        try:
            await query.message.reply_to_message.delete()
        except:
            pass

@Client.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):
    if query.data == "close_data":
        try:
            user = query.message.reply_to_message.from_user.id
        except:
            user = query.from_user.id
        if int(user) != 0 and query.from_user.id != int(user):
            return await query.answer(script.ALRT_TXT, show_alert=True)
        await query.answer("ᴛʜᴀɴᴋs ꜰᴏʀ ᴄʟᴏsᴇ 🙈")
        await query.message.delete()
        try:
            await query.message.reply_to_message.delete()
        except:
            pass
          
    elif query.data == "delallcancel":
        userid = query.from_user.id
        chat_type = query.message.chat.type
        if chat_type == enums.ChatType.PRIVATE:
            await query.message.reply_to_message.delete()
            await query.message.delete()
        elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
            grp_id = query.message.chat.id
            st = await client.get_chat_member(grp_id, userid)
            if (st.status == enums.ChatMemberStatus.OWNER) or (str(userid) in ADMINS):
                await query.message.delete()
                try:
                    await query.message.reply_to_message.delete()
                except:
                    pass
            else:
                await query.answer(script.ALRT_TXT.format(query.from_user.first_name), show_alert=True)    
            
    elif query.data.startswith("checksub"):
        ident, file_id = query.data.split("#")
        settings = await get_settings(query.message.chat.id)
        if AUTH_CHANNEL and not await is_req_subscribed(client, query):
            await query.answer("ɪ ʟɪᴋᴇ ʏᴏᴜʀ sᴍᴀʀᴛɴᴇss ʙᴜᴛ ᴅᴏɴ'ᴛ ʙᴇ ᴏᴠᴇʀsᴍᴀʀᴛ 😒\nꜰɪʀsᴛ ᴊᴏɪɴ ᴏᴜʀ ᴜᴘᴅᴀᴛᴇs ᴄʜᴀɴɴᴇʟ 😒", show_alert=True)
            return         
        files_ = await get_file_details(file_id)
        if not files_:
            return await query.answer('ɴᴏ sᴜᴄʜ ꜰɪʟᴇ ᴇxɪsᴛs 🚫')
        files = files_[0]
        CAPTION = settings['caption']
        f_caption = CAPTION.format(
            file_name = files.file_name,
            file_size = get_size(files.file_size),
            file_caption = files.caption
        )
        await client.send_cached_media(
            chat_id=query.from_user.id,
            file_id=file_id,
            caption=f_caption,
            protect_content=settings['file_secure'],
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton('❌ ᴄʟᴏsᴇ ❌', callback_data='close_data')
                    ]
                ]
            )
        )

    elif query.data.startswith("stream"):
        user_id = query.from_user.id
        if not await db.has_premium_access(user_id):
            d=await query.message.reply("<b>💔 ᴛʜɪꜱ ғᴇᴀᴛᴜʀᴇ ɪꜱ ᴏɴʟʏ ғᴏʀ ʙᴏᴛ ᴘʀᴇᴍɪᴜᴍ ᴜꜱᴇʀꜱ.\n\nɪғ ʏᴏᴜ ᴡᴀɴᴛ ʙᴏᴛ ꜱᴜʙꜱᴄʀɪᴘᴛɪᴏɴ ᴛʜᴇɴ ꜱᴇɴᴅ /plan</b>")
            await asyncio.sleep(10)
            await d.delete()
            return
        file_id = query.data.split('#', 1)[1]
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
            InlineKeyboardButton('🚫 ᴇᴀʀɴ ᴍᴏɴᴇʏ ᴡɪᴛʜ ʙᴏᴛ 🚫', callback_data='earn')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.START_TXT.format(query.from_user.mention, get_status(), query.from_user.id),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )      
    elif query.data == "features":
        buttons = [[
            InlineKeyboardButton('📸 ᴛ-ɢʀᴀᴘʜ', callback_data='telegraph'),
            InlineKeyboardButton('🆎️ ғᴏɴᴛ', callback_data='font')    
        ], [ 
            InlineKeyboardButton('⋞ ʙᴀᴄᴋ', callback_data='start')
        ]] 
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(                     
            text=script.HELP_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "earn":
        buttons = [[
            InlineKeyboardButton('⋞ ʙᴀᴄᴋ', callback_data='start'),
            InlineKeyboardButton('sᴜᴘᴘᴏʀᴛ', url=USERNAME)
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
             text=script.EARN_TEXT.format(temp.B_LINK),
             reply_markup=reply_markup,
             parse_mode=enums.ParseMode.HTML
         )
    elif query.data == "telegraph":
        buttons = [[
            InlineKeyboardButton('⋞ ʙᴀᴄᴋ', callback_data='features')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)  
        await query.message.edit_text(
            text=script.TELE_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "font":
        buttons = [[
            InlineKeyboardButton('⋞ ʙᴀᴄᴋ', callback_data='features')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons) 
        await query.message.edit_text(
            text=script.FONT_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "buy_premium":
        btn = [[
            InlineKeyboardButton('📸 sᴇɴᴅ sᴄʀᴇᴇɴsʜᴏᴛ 📸', url=USERNAME)
        ],[
            InlineKeyboardButton('🗑 ᴄʟᴏsᴇ 🗑', callback_data='close_data')
        ]]
        reply_markup = InlineKeyboardMarkup(btn)
        await query.message.reply_photo(
            photo=(QR_CODE),
            caption=script.PREMIUM_TEXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )

    elif query.data == "all_files_delete":
        files = await Media.count_documents()
        await query.answer('Deleting...')
        await Media.collection.drop()
        await query.message.edit_text(f"Successfully deleted {files} files")
        
    elif query.data.startswith("killfilesak"):
        ident, keyword = query.data.split("#")
        await query.message.edit_text(f"<b>ꜰᴇᴛᴄʜɪɴɢ ꜰɪʟᴇs ꜰᴏʀ ʏᴏᴜʀ ǫᴜᴇʀʏ {keyword} ᴏɴ ᴅʙ...\n\nᴘʟᴇᴀsᴇ ᴡᴀɪᴛ...</b>")
        files, total = await get_bad_files(keyword)
        await query.message.edit_text(f"<b>ꜰᴏᴜɴᴅ {total} ꜰɪʟᴇs ꜰᴏʀ ʏᴏᴜʀ ǫᴜᴇʀʏ {keyword}!!</b>")
        deleted = 0
        async with lock:
            try:
                for file in files:
                    file_ids = file.file_id
                    file_name = file.file_name
                    result = await Media.collection.delete_one({
                        '_id': file_ids,
                    })
                    if result.deleted_count:
                        print(f'Successfully deleted {file_name} from database.')
                    deleted += 1
                    if deleted % 20 == 0:
                        await query.message.edit_text(f"<b>Process started for deleting files from DB. Successfully deleted {str(deleted)} files from DB for your query {keyword} !\n\nPlease wait...</b>")
            except Exception as e:
                print(e)
                await query.message.edit_text(f'Error: {e}')
            else:
                await query.message.edit_text(f"<b>Process Completed for file deletion !\n\nSuccessfully deleted {str(deleted)} files from database for your query {keyword}.</b>")
          
    elif query.data.startswith("reset_grp_data"):
        grp_id = query.message.chat.id
        btn = [[
            InlineKeyboardButton('☕️ ᴄʟᴏsᴇ ☕️', callback_data='close_data')
        ]]
        reply_markup=InlineKeyboardMarkup(btn)
        await save_group_settings(grp_id, 'shortner', SHORTENER_WEBSITE)
        await save_group_settings(grp_id, 'api', SHORTENER_API)
        await save_group_settings(grp_id, 'shortner_two', SHORTENER_WEBSITE2)
        await save_group_settings(grp_id, 'api_two', SHORTENER_API2)
        await save_group_settings(grp_id, 'template', IMDB_TEMPLATE)
        await save_group_settings(grp_id, 'tutorial', TUTORIAL)
        await save_group_settings(grp_id, 'caption', FILE_CAPTION)
        await save_group_settings(grp_id, 'log', LOG_VR_CHANNEL)
        await query.answer('ꜱᴜᴄᴄᴇꜱꜱғᴜʟʟʏ ʀᴇꜱᴇᴛ...')
        await query.message.edit_text("<b>ꜱᴜᴄᴄᴇꜱꜱғᴜʟʟʏ ʀᴇꜱᴇᴛ ɢʀᴏᴜᴘ ꜱᴇᴛᴛɪɴɢꜱ...\n\nɴᴏᴡ ꜱᴇɴᴅ /details ᴀɢᴀɪɴ</b>", reply_markup=reply_markup)

    elif query.data.startswith("setgs"):
        ident, set_type, status, grp_id = query.data.split("#")
        userid = query.from_user.id if query.from_user else None
        if not await is_check_admin(client, int(grp_id), userid):
            await query.answer(script.ALRT_TXT, show_alert=True)
            return
        if status == "True":
            await save_group_settings(int(grp_id), set_type, False)
            await query.answer("ᴏғғ ❌")
        else:
            await save_group_settings(int(grp_id), set_type, True)
            await query.answer("ᴏɴ ✅")
        settings = await get_settings(int(grp_id))      
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
                InlineKeyboardButton('ʀᴇsᴜʟᴛ ᴍᴏᴅᴇ', callback_data=f'setgs#link#{settings["link"]}#{str(grp_id)}'),
                InlineKeyboardButton('ʟɪɴᴋ' if settings["link"] else 'ʙᴜᴛᴛᴏɴ', callback_data=f'setgs#link#{settings["link"]}#{str(grp_id)}')
            ],[
                InlineKeyboardButton('ᴠᴇʀɪғʏ', callback_data=f'setgs#is_verify#{settings["is_verify"]}#{grp_id}'),
                InlineKeyboardButton('ᴏɴ ✔️' if settings["is_verify"] else 'ᴏғғ ✗', callback_data=f'setgs#is_verify#{settings["is_verify"]}#{grp_id}')
            ],[
                InlineKeyboardButton('☕️ ᴄʟᴏsᴇ ☕️', callback_data='close_data')
            ]]
            reply_markup = InlineKeyboardMarkup(buttons)
            d = await query.message.edit_reply_markup(reply_markup)
            await asyncio.sleep(300)
            await d.delete()
        else:
            await query.message.edit_text("<b>ꜱᴏᴍᴇᴛʜɪɴɢ ᴡᴇɴᴛ ᴡʀᴏɴɢ</b>")
            
    elif query.data.startswith("show_options"):
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
            if (st.status == enums.ChatMemberStatus.ADMINISTRATOR) or (st.status == enums.ChatMemberStatus.OWNER):
                await query.message.edit_reply_markup(InlineKeyboardMarkup(buttons))
            elif st.status == enums.ChatMemberStatus.MEMBER:
                await query.answer(script.ALRT_TXT, show_alert=True)
        except pyrogram.errors.exceptions.bad_request_400.UserNotParticipant:
            await query.answer("⚠️ ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴀ ᴍᴇᴍʙᴇʀ ᴏꜰ ᴛʜɪꜱ ᴄʜᴀɴɴᴇʟ, ꜰɪʀꜱᴛ ᴊᴏɪɴ", show_alert=True)

    elif query.data.startswith("reject"):
        ident, user_id, msg_id = query.data.split("#")
        chnl_id = query.message.chat.id
        userid = query.from_user.id
        buttons = [[
            InlineKeyboardButton("✗ ʀᴇᴊᴇᴄᴛ ✗", callback_data=f"rj_alert#{user_id}")
        ]]
        btn = [[
            InlineKeyboardButton("♻️ ᴠɪᴇᴡ sᴛᴀᴛᴜs ♻️", url=f"{query.message.link}")
        ]]
        st = await client.get_chat_member(chnl_id, userid)
        if (st.status == enums.ChatMemberStatus.ADMINISTRATOR) or (st.status == enums.ChatMemberStatus.OWNER):
            user = await client.get_users(user_id)
            request = query.message.text
            await query.answer("Message sent to requester")
            await query.message.edit_text(f"<s>{request}</s>")
            await query.message.edit_reply_markup(InlineKeyboardMarkup(buttons))
            try:
                await client.send_message(chat_id=user_id, text="<b>sᴏʀʀʏ ʏᴏᴜʀ ʀᴇǫᴜᴇsᴛ ɪs ʀᴇᴊᴇᴄᴛᴇᴅ 😶</b>", reply_markup=InlineKeyboardMarkup(btn))
            except UserIsBlocked:
                await client.send_message(SUPPORT_GROUP, text=f"<b>💥 ʜᴇʟʟᴏ {user.mention},\n\nsᴏʀʀʏ ʏᴏᴜʀ ʀᴇǫᴜᴇsᴛ ɪs ʀᴇᴊᴇᴄᴛᴇᴅ 😶</b>", reply_markup=InlineKeyboardMarkup(btn), reply_to_message_id=int(msg_id))
        else:
            await query.answer(script.ALRT_TXT, show_alert=True)

    elif query.data.startswith("accept"):
        ident, user_id, msg_id = query.data.split("#")
        chnl_id = query.message.chat.id
        userid = query.from_user.id
        buttons = [[
            InlineKeyboardButton("😊 ᴀʟʀᴇᴀᴅʏ ᴀᴠᴀɪʟᴀʙʟᴇ 😊", callback_data=f"already_available#{user_id}#{msg_id}")
        ],[
            InlineKeyboardButton("‼️ ɴᴏᴛ ᴀᴠᴀɪʟᴀʙʟᴇ ‼️", callback_data=f"not_available#{user_id}#{msg_id}")
        ],[
            InlineKeyboardButton("🥵 ᴛᴇʟʟ ᴍᴇ ʏᴇᴀʀ/ʟᴀɴɢᴜᴀɢᴇ 🥵", callback_data=f"year#{user_id}#{msg_id}")
        ],[
            InlineKeyboardButton("🙃 ᴜᴘʟᴏᴀᴅᴇᴅ ɪɴ 1 ʜᴏᴜʀ 🙃", callback_data=f"upload_in#{user_id}#{msg_id}")
        ],[
            InlineKeyboardButton("☇ ᴜᴘʟᴏᴀᴅᴇᴅ ☇", callback_data=f"uploaded#{user_id}#{msg_id}")
        ]]
        try:
            st = await client.get_chat_member(chnl_id, userid)
            if (st.status == enums.ChatMemberStatus.ADMINISTRATOR) or (st.status == enums.ChatMemberStatus.OWNER):
                await query.message.edit_reply_markup(InlineKeyboardMarkup(buttons))
            elif st.status == enums.ChatMemberStatus.MEMBER:
                await query.answer(script.OLD_ALRT_TXT.format(query.from_user.first_name),show_alert=True)
        except pyrogram.errors.exceptions.bad_request_400.UserNotParticipant:
            await query.answer("⚠️ ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴀ ᴍᴇᴍʙᴇʀ ᴏꜰ ᴛʜɪꜱ ᴄʜᴀɴɴᴇʟ, ꜰɪʀꜱᴛ ᴊᴏɪɴ", show_alert=True)

    elif query.data.startswith("not_available"):
        ident, user_id, msg_id = query.data.split("#")
        chnl_id = query.message.chat.id
        userid = query.from_user.id
        buttons = [[
            InlineKeyboardButton("🚫 ɴᴏᴛ ᴀᴠᴀɪʟᴀʙʟᴇ 🚫", callback_data=f"na_alert#{user_id}")
        ]]
        btn = [[
            InlineKeyboardButton("♻️ ᴠɪᴇᴡ sᴛᴀᴛᴜs ♻️", url=f"{query.message.link}")
        ]]
        st = await client.get_chat_member(chnl_id, userid)
        if (st.status == enums.ChatMemberStatus.ADMINISTRATOR) or (st.status == enums.ChatMemberStatus.OWNER):
            user = await client.get_users(user_id)
            request = query.message.text
            await query.answer("Message sent to requester")
            await query.message.edit_text(f"<s>{request}</s>")
            await query.message.edit_reply_markup(InlineKeyboardMarkup(buttons))
            try:
                await client.send_message(chat_id=user_id, text="<b>sᴏʀʀʏ ʏᴏᴜʀ ʀᴇǫᴜᴇsᴛ ɪs ɴᴏᴛ ᴀᴠᴀɪʟᴀʙʟᴇ 😢</b>", reply_markup=InlineKeyboardMarkup(btn))
            except UserIsBlocked:
                await client.send_message(SUPPORT_GROUP, text=f"<b>💥 ʜᴇʟʟᴏ {user.mention},\n\nsᴏʀʀʏ ʏᴏᴜʀ ʀᴇǫᴜᴇsᴛ ɪs ɴᴏᴛ ᴀᴠᴀɪʟᴀʙʟᴇ 😢</b>", reply_markup=InlineKeyboardMarkup(btn), reply_to_message_id=int(msg_id))
        else:
            await query.answer(script.ALRT_TXT, show_alert=True)

    elif query.data.startswith("uploaded"):
        ident, user_id, msg_id = query.data.split("#")
        chnl_id = query.message.chat.id
        userid = query.from_user.id
        buttons = [[
            InlineKeyboardButton("🙂 ᴜᴘʟᴏᴀᴅᴇᴅ 🙂", callback_data=f"ul_alert#{user_id}")
        ]]
        btn = [[
            InlineKeyboardButton("♻️ ᴠɪᴇᴡ sᴛᴀᴛᴜs ♻️", url=f"{query.message.link}")
        ]]
        st = await client.get_chat_member(chnl_id, userid)
        if (st.status == enums.ChatMemberStatus.ADMINISTRATOR) or (st.status == enums.ChatMemberStatus.OWNER):
            user = await client.get_users(user_id)
            request = query.message.text
            await query.answer("Message sent to requester")
            await query.message.edit_text(f"<s>{request}</s>")
            await query.message.edit_reply_markup(InlineKeyboardMarkup(buttons))
            try:
                await client.send_message(chat_id=user_id, text="<b>ʏᴏᴜʀ ʀᴇǫᴜᴇsᴛ ɪs ᴜᴘʟᴏᴀᴅᴇᴅ ☺️</b>", reply_markup=InlineKeyboardMarkup(btn))
            except UserIsBlocked:
                await client.send_message(SUPPORT_GROUP, text=f"<b>💥 ʜᴇʟʟᴏ {user.mention},\n\nʏᴏᴜʀ ʀᴇǫᴜᴇsᴛ ɪs ᴜᴘʟᴏᴀᴅᴇᴅ ☺️</b>", reply_markup=InlineKeyboardMarkup(btn), reply_to_message_id=int(msg_id))
        else:
            await query.answer(script.ALRT_TXT, show_alert=True)

    elif query.data.startswith("already_available"):
        ident, user_id, msg_id = query.data.split("#")
        chnl_id = query.message.chat.id
        userid = query.from_user.id
        buttons = [[
            InlineKeyboardButton("🫤 ᴀʟʀᴇᴀᴅʏ ᴀᴠᴀɪʟᴀʙʟᴇ 🫤", callback_data=f"aa_alert#{user_id}")
        ]]
        btn = [[
            InlineKeyboardButton("♻️ ᴠɪᴇᴡ sᴛᴀᴛᴜs ♻️", url=f"{query.message.link}")
        ]]
        st = await client.get_chat_member(chnl_id, userid)
        if (st.status == enums.ChatMemberStatus.ADMINISTRATOR) or (st.status == enums.ChatMemberStatus.OWNER):
            user = await client.get_users(user_id)
            request = query.message.text
            await query.answer("Message sent to requester")
            await query.message.edit_text(f"<s>{request}</s>")
            await query.message.edit_reply_markup(InlineKeyboardMarkup(buttons))
            try:
                await client.send_message(chat_id=user_id, text="<b>ʏᴏᴜʀ ʀᴇǫᴜᴇsᴛ ɪs ᴀʟʀᴇᴀᴅʏ ᴀᴠᴀɪʟᴀʙʟᴇ 😋</b>", reply_markup=InlineKeyboardMarkup(btn))
            except UserIsBlocked:
                await client.send_message(SUPPORT_GROUP, text=f"<b>💥 ʜᴇʟʟᴏ {user.mention},\n\nʏᴏᴜʀ ʀᴇǫᴜᴇsᴛ ɪs ᴀʟʀᴇᴀᴅʏ ᴀᴠᴀɪʟᴀʙʟᴇ 😋</b>", reply_markup=InlineKeyboardMarkup(btn), reply_to_message_id=int(msg_id))
        else:
            await query.answer(script.ALRT_TXT, show_alert=True)

    elif query.data.startswith("upload_in"):
        ident, user_id, msg_id = query.data.split("#")
        chnl_id = query.message.chat.id
        userid = query.from_user.id
        buttons = [[
            InlineKeyboardButton("😌 ᴜᴘʟᴏᴀᴅ ɪɴ 1 ʜᴏᴜʀꜱ 😌", callback_data=f"upload_alert#{user_id}")
        ]]
        btn = [[
            InlineKeyboardButton("♻️ ᴠɪᴇᴡ sᴛᴀᴛᴜs ♻️", url=f"{query.message.link}")
        ]]
        st = await client.get_chat_member(chnl_id, userid)
        if (st.status == enums.ChatMemberStatus.ADMINISTRATOR) or (st.status == enums.ChatMemberStatus.OWNER):
            user = await client.get_users(user_id)
            request = query.message.text
            await query.answer("Message sent to requester")
            await query.message.edit_text(f"<s>{request}</s>")
            await query.message.edit_reply_markup(InlineKeyboardMarkup(buttons))
            try:
                await client.send_message(chat_id=user_id, text="<b>ʏᴏᴜʀ ʀᴇǫᴜᴇꜱᴛ ᴡɪʟʟ ʙᴇ ᴜᴘʟᴏᴀᴅᴇᴅ ᴡɪᴛʜɪɴ 1 ʜᴏᴜʀ 😁</b>", reply_markup=InlineKeyboardMarkup(btn))
            except UserIsBlocked:
                await client.send_message(SUPPORT_GROUP, text=f"<b>💥 ʜᴇʟʟᴏ {user.mention},\n\nʏᴏᴜʀ ʀᴇǫᴜᴇꜱᴛ ᴡɪʟʟ ʙᴇ ᴜᴘʟᴏᴀᴅᴇᴅ ᴡɪᴛʜɪɴ 1 ʜᴏᴜʀ 😁</b>", reply_markup=InlineKeyboardMarkup(btn), reply_to_message_id=int(msg_id))
        else:
            await query.answer(script.ALRT_TXT, show_alert=True)

    elif query.data.startswith("year"):
        ident, user_id, msg_id = query.data.split("#")
        chnl_id = query.message.chat.id
        userid = query.from_user.id
        buttons = [[
            InlineKeyboardButton("⚠️ ᴛᴇʟʟ ᴍᴇ ʏᴇᴀʀꜱ & ʟᴀɴɢᴜᴀɢᴇ ⚠️", callback_data=f"yrs_alert#{user_id}")
        ]]
        btn = [[
            InlineKeyboardButton("♻️ ᴠɪᴇᴡ sᴛᴀᴛᴜs ♻️", url=f"{query.message.link}")
        ]]
        st = await client.get_chat_member(chnl_id, userid)
        if (st.status == enums.ChatMemberStatus.ADMINISTRATOR) or (st.status == enums.ChatMemberStatus.OWNER):
            user = await client.get_users(user_id)
            request = query.message.text
            await query.answer("Message sent to requester")
            await query.message.edit_text(f"<s>{request}</s>")
            await query.message.edit_reply_markup(InlineKeyboardMarkup(buttons))
            try:
                await client.send_message(chat_id=user_id, text="<b>ʙʀᴏ ᴘʟᴇᴀꜱᴇ ᴛᴇʟʟ ᴍᴇ ʏᴇᴀʀꜱ ᴀɴᴅ ʟᴀɴɢᴜᴀɢᴇ, ᴛʜᴇɴ ɪ ᴡɪʟʟ ᴜᴘʟᴏᴀᴅ 😬</b>", reply_markup=InlineKeyboardMarkup(btn))
            except UserIsBlocked:
                await client.send_message(SUPPORT_GROUP, text=f"<b>💥 ʜᴇʟʟᴏ {user.mention},\n\nʙʀᴏ ᴘʟᴇᴀꜱᴇ ᴛᴇʟʟ ᴍᴇ ʏᴇᴀʀꜱ ᴀɴᴅ ʟᴀɴɢᴜᴀɢᴇ, ᴛʜᴇɴ ɪ ᴡɪʟʟ ᴜᴘʟᴏᴀᴅ 😬</b>", reply_markup=InlineKeyboardMarkup(btn), reply_to_message_id=int(msg_id))
        else:
            await query.answer(script.ALRT_TXT, show_alert=True)

    elif query.data.startswith("rj_alert"):
        ident, user_id = query.data.split("#")
        userid = query.from_user.id
        if str(userid) in user_id:
            await query.answer("sᴏʀʀʏ ʏᴏᴜʀ ʀᴇǫᴜᴇsᴛ ɪs ʀᴇᴊᴇᴄᴛ", show_alert=True)
        else:
            await query.answer(script.ALRT_TXT, show_alert=True)

    elif query.data.startswith("na_alert"):
        ident, user_id = query.data.split("#")
        userid = query.from_user.id
        if str(userid) in user_id:
            await query.answer("sᴏʀʀʏ ʏᴏᴜʀ ʀᴇǫᴜᴇsᴛ ɪs ɴᴏᴛ ᴀᴠᴀɪʟᴀʙʟᴇ", show_alert=True)
        else:
            await query.answer(script.ALRT_TXT, show_alert=True)

    elif query.data.startswith("ul_alert"):
        ident, user_id = query.data.split("#")
        userid = query.from_user.id
        if str(userid) in user_id:
            await query.answer("ʏᴏᴜʀ ʀᴇǫᴜᴇsᴛ ɪs ᴜᴘʟᴏᴀᴅᴇᴅ", show_alert=True)
        else:
            await query.answer(script.ALRT_TXT, show_alert=True)

    elif query.data.startswith("aa_alert"):
        ident, user_id = query.data.split("#")
        userid = query.from_user.id
        if str(userid) in user_id:
            await query.answer("ʏᴏᴜʀ ʀᴇǫᴜᴇsᴛ ɪs ᴀʟʀᴇᴀᴅʏ ᴀᴠᴀɪʟᴀʙʟᴇ", show_alert=True)
        else:
            await query.answer(script.ALRT_TXT, show_alert=True)

    elif query.data.startswith("upload_alert"):
        ident, user_id = query.data.split("#")
        userid = query.from_user.id
        if str(userid) in user_id:
            await query.answer("ʏᴏᴜʀ ʀᴇǫᴜᴇꜱᴛ ᴡɪʟʟ ʙᴇ ᴜᴘʟᴏᴀᴅᴇᴅ ᴡɪᴛʜɪɴ 1 ʜᴏᴜʀ 😁", show_alert=True)
        else:
            await query.answer(script.ALRT_TXT, show_alert=True)

    elif query.data.startswith("yrs_alert"):
        ident, user_id = query.data.split("#")
        userid = query.from_user.id
        if str(userid) in user_id:
            await query.answer("ʙʀᴏ ᴘʟᴇᴀꜱᴇ ᴛᴇʟʟ ᴍᴇ ʏᴇᴀʀꜱ ᴀɴᴅ ʟᴀɴɢᴜᴀɢᴇ, ᴛʜᴇɴ ɪ ᴡɪʟʟ ᴜᴘʟᴏᴀᴅ 😬", show_alert=True)
        else:
            await query.answer(script.ALRT_TXT, show_alert=True)

    elif query.data.startswith("batchfiles"):
        ident, group_id, message_id, user = query.data.split("#")
        group_id = int(group_id)
        message_id = int(message_id)
        user = int(user)
        if user != query.from_user.id:
            await query.answer(script.ALRT_TXT, show_alert=True)
            return
        link = f"https://telegram.me/{temp.U_NAME}?start=allfiles_{group_id}-{message_id}"
        await query.answer(url=link)
        return

async def auto_filter(client, msg, spoll=False):
    if not spoll:
        message = msg
        search = message.text
        chat_id = message.chat.id
        settings = await get_settings(chat_id)
        files, offset, total_results = await get_search_results(search)
        if not files:
            if settings["spell_check"]:
                return await advantage_spell_chok(msg)
            return
    else:
        settings = await get_settings(msg.message.chat.id)
        message = msg.message.reply_to_message  # msg will be callback query
        search, files, offset, total_results = spoll
    req = message.from_user.id if message.from_user else 0
    key = f"{message.chat.id}-{message.id}"
    batch_ids = files
    temp.FILES_ID[f"{message.chat.id}-{message.id}"] = batch_ids
    batch_link = f"batchfiles#{message.chat.id}#{message.id}#{message.from_user.id}"
    pre = 'filep' if settings['file_secure'] else 'file'
    temp.CHAT[message.from_user.id] = message.chat.id
    settings = await get_settings(message.chat.id)
    del_msg = f"\n\n<b>⚠️ ᴛʜɪs ᴍᴇssᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ ᴀꜰᴛᴇʀ <code>{get_readable_time(DELETE_TIME)}</code> ᴛᴏ ᴀᴠᴏɪᴅ ᴄᴏᴘʏʀɪɢʜᴛ ɪssᴜᴇs</b>" if settings["auto_delete"] else ''
    links = ""
    if settings["link"]:
        btn = []
        for file_num, file in enumerate(files, start=1):
            links += f"""<b>\n\n{file_num}. <a href=https://t.me/{temp.U_NAME}?start=file_{message.chat.id}_{file.file_id}>[{get_size(file.file_size)}] {' '.join(filter(lambda x: not x.startswith('[') and not x.startswith('@') and not x.startswith('www.'), file.file_name.split()))}</a></b>"""
    else:
        btn = [[InlineKeyboardButton(text=f"🔗 {get_size(file.file_size)}≽ {get_name(file.file_name)}", url=f'https://telegram.dog/{temp.U_NAME}?start=file_{message.chat.id}_{file.file_id}'),]
               for file in files
              ]
    if offset != "":
        if total_results >= 3:
            btn.insert(0,[
                InlineKeyboardButton("♻️ sᴇɴᴅ ᴀʟʟ", callback_data=batch_link),
                InlineKeyboardButton("🥇ʙᴜʏ🥇", url=f"https://t.me/{temp.U_NAME}?start=buy_premium"),
                InlineKeyboardButton("📰 ʟᴀɴɢᴜᴀɢᴇs", callback_data=f"languages#{key}#0#{req}")
            ])
        else:
            btn.insert(0,[
                InlineKeyboardButton("🥇ʙᴜʏ🥇", url=f"https://t.me/{temp.U_NAME}?start=buy_premium"),
                InlineKeyboardButton("📰 ʟᴀɴɢᴜᴀɢᴇs", callback_data=f"languages#{key}#0#{req}")
            ])
    else:
        if total_results >= 3:
            btn.insert(0,[
                InlineKeyboardButton("♻️ sᴇɴᴅ ᴀʟʟ", callback_data=batch_link),
                InlineKeyboardButton("🥇ʙᴜʏ🥇", url=f"https://t.me/{temp.U_NAME}?start=buy_premium")
            ])
        else:
            btn.insert(0,[
                InlineKeyboardButton("🥇ʙᴜʏ🥇", url=f"https://t.me/{temp.U_NAME}?start=buy_premium")
            ])
                             
    if spoll:
        m = await msg.message.edit(f"<b><code>{search}</code> ɪs ꜰᴏᴜɴᴅ ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ ꜰᴏʀ ꜰɪʟᴇs 📫</b>")
        await asyncio.sleep(1.2)
        await m.delete()

    if offset != "":
        BUTTONS[key] = search
        req = message.from_user.id if message.from_user else 0
        btn.append(
            [InlineKeyboardButton(text=f"1/{math.ceil(int(total_results) / int(MAX_BTN))}", callback_data="pages"),
             InlineKeyboardButton(text="ɴᴇxᴛ ⪼", callback_data=f"next_{req}_{key}_{offset}")]
        )
        key = f"{message.chat.id}-{message.id}"
        BUTTONS[key] = search
        req = message.from_user.id if message.from_user else 0
        try:
            offset = int(offset) 
        except:
            offset = int(MAX_BTN)
        
    imdb = await get_poster(search, file=(files[0]).file_name) if settings["imdb"] else None
    TEMPLATE = settings['template']
    if imdb:
        cap = TEMPLATE.format(
            query=search,
            title=imdb['title'],
            votes=imdb['votes'],
            aka=imdb["aka"],
            seasons=imdb["seasons"],
            box_office=imdb['box_office'],
            localized_title=imdb['localized_title'],
            kind=imdb['kind'],
            imdb_id=imdb["imdb_id"],
            cast=imdb["cast"],
            runtime=imdb["runtime"],
            countries=imdb["countries"],
            certificates=imdb["certificates"],
            languages=imdb["languages"],
            director=imdb["director"],
            writer=imdb["writer"],
            producer=imdb["producer"],
            composer=imdb["composer"],
            cinematographer=imdb["cinematographer"],
            music_team=imdb["music_team"],
            distributors=imdb["distributors"],
            release_date=imdb['release_date'],
            year=imdb['year'],
            genres=imdb['genres'],
            poster=imdb['poster'],
            plot=imdb['plot'],
            rating=imdb['rating'],
            url=imdb['url'],
            **locals()
        )
    else:
        cap = f"<b>📂 ʜᴇʀᴇ ɪ ꜰᴏᴜɴᴅ ꜰᴏʀ ʏᴏᴜʀ sᴇᴀʀᴄʜ {search}</b>"
    del_msg = f"\n\n<b>⚠️ ᴛʜɪs ᴍᴇssᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ ᴀꜰᴛᴇʀ <code>{get_readable_time(DELETE_TIME)}</code> ᴛᴏ ᴀᴠᴏɪᴅ ᴄᴏᴘʏʀɪɢʜᴛ ɪssᴜᴇs</b>" if settings["auto_delete"] else ''
    CAP[key] = cap
    if imdb and imdb.get('poster'):
        try:
            if settings['auto_delete']:
                k = await message.reply_photo(photo=imdb.get('poster'), caption=cap[:1024] + links + del_msg, parse_mode=enums.ParseMode.HTML, reply_markup=InlineKeyboardMarkup(btn))
                await asyncio.sleep(DELETE_TIME)
                await k.delete()
                try:
                    await message.delete()
                except:
                    pass
            else:
                await message.reply_photo(photo=imdb.get('poster'), caption=cap[:1024] + links + del_msg, reply_markup=InlineKeyboardMarkup(btn))                    
        except (MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty):
            pic = imdb.get('poster')
            poster = pic.replace('.jpg', "._V1_UX360.jpg")
            if settings["auto_delete"]:
                k = await message.reply_photo(photo=poster, caption=cap[:1024] + links + del_msg, parse_mode=enums.ParseMode.HTML, reply_markup=InlineKeyboardMarkup(btn))
                await asyncio.sleep(DELETE_TIME)
                await k.delete()
                try:
                    await message.delete()
                except:
                    pass
            else:
                await message.reply_photo(photo=poster, caption=cap[:1024] + links + del_msg, parse_mode=enums.ParseMode.HTML, reply_markup=InlineKeyboardMarkup(btn))
        except Exception as e:
            print(e)
            if settings["auto_delete"]:
                k = await message.reply_text(cap + links + del_msg, parse_mode=enums.ParseMode.HTML, reply_markup=InlineKeyboardMarkup(btn), disable_web_page_preview=True)
                await asyncio.sleep(DELETE_TIME)
                await k.delete()
                try:
                    await message.delete()
                except:
                    pass
            else:
                await message.reply_text(cap + links + del_msg, parse_mode=enums.ParseMode.HTML, reply_markup=InlineKeyboardMarkup(btn), disable_web_page_preview=True)
    else:
        k=await message.reply_text(text=cap + links + del_msg, disable_web_page_preview=True, parse_mode=enums.ParseMode.HTML, reply_markup=InlineKeyboardMarkup(btn), reply_to_message_id=message.id)
        if settings['auto_delete']:
            await asyncio.sleep(DELETE_TIME)
            await k.delete()
            try:
                await message.delete()
            except:
                pass

async def advantage_spell_chok(message):
    mv_id = message.id
    search = message.text
    chat_id = message.chat.id
    settings = await get_settings(chat_id)
    query = re.sub(
        r"\b(pl(i|e)*?(s|z+|ease|se|ese|(e+)s(e)?)|((send|snd|giv(e)?|gib)(\sme)?)|movie(s)?|new|latest|br((o|u)h?)*|^h(e|a)?(l)*(o)*|mal(ayalam)?|t(h)?amil|file|that|find|und(o)*|kit(t(i|y)?)?o(w)?|thar(u)?(o)*w?|kittum(o)*|aya(k)*(um(o)*)?|full\smovie|any(one)|with\ssubtitle(s)?)",
        "", message.text, flags=re.IGNORECASE)
    RQST = query.strip()
    query = query.strip() + " movie"
    try:
        movies = await get_poster(search, bulk=True)
    except:
        k = await message.reply(script.I_CUDNT.format(message.from_user.mention))
        await asyncio.sleep(60)
        await k.delete()
        try:
            await message.delete()
        except:
            pass
        return
    if not movies:
        google = search.replace(" ", "+")
        button = [[
            InlineKeyboardButton("🔍 ᴄʜᴇᴄᴋ sᴘᴇʟʟɪɴɢ ᴏɴ ɢᴏᴏɢʟᴇ 🔍", url=f"https://www.google.com/search?q={google}")
        ]]
        k = await message.reply_text(text=script.I_CUDNT.format(search), reply_markup=InlineKeyboardMarkup(button))
        await asyncio.sleep(120)
        await k.delete()
        try:
            await message.delete()
        except:
            pass
        return
    user = message.from_user.id if message.from_user else 0
    buttons = [[
        InlineKeyboardButton(text=movie.get('title'), callback_data=f"spol#{movie.movieID}#{user}")
    ]
        for movie in movies
    ]
    buttons.append(
        [InlineKeyboardButton(text="🚫 ᴄʟᴏsᴇ 🚫", callback_data='close_data')]
    )
    d = await message.reply_text(text=script.CUDNT_FND.format(message.from_user.mention), reply_markup=InlineKeyboardMarkup(buttons), reply_to_message_id=message.id)
    await asyncio.sleep(120)
    await d.delete()
    try:
        await message.delete()
    except:
        pass
