import os, requests
import logging
import random
import asyncio
import string
import pytz
from datetime import datetime
from Script import script
from pyrogram import Client, filters, enums
from pyrogram.errors import ChatAdminRequired, FloodWait
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database.ia_filterdb import Media, get_file_details, get_bad_files, unpack_new_file_id
from database.users_chats_db import db
from info import (
    ADMINS, LOG_CHANNEL, USERNAME, VERIFY_IMG, IS_VERIFY, FILE_CAPTION, 
    AUTH_CHANNEL, SHORTENER_WEBSITE, SHORTENER_API, SHORTENER_WEBSITE2, 
    SHORTENER_API2, LOG_API_CHANNEL, TWO_VERIFY_GAP, QR_CODE, DELETE_TIME, 
    REQUEST_CHANNEL, REFERRAL_TARGET
)
from utils import get_settings, save_group_settings, is_req_subscribed, get_size, get_shortlink, is_check_admin, get_status, temp, get_readable_time
import re
import json
import base64

logger = logging.getLogger(__name__)

@Client.on_message(filters.command("start") & filters.incoming)
async def start(client:Client, message): 
    m = message
    user_id = m.from_user.id

    # --- Handle Referral Link ---
    is_referral = False
    referred_by_id = None
    if len(message.command) == 2 and message.command[1].startswith('ref_'):
        is_referral = True
        try:
            referrer_id = int(message.command[1].split('_')[1])
            if referrer_id != message.from_user.id: # Can't refer self
                referred_by_id = referrer_id
        except Exception as e:
            logger.error(f"Invalid referral link: {message.command[1]} - Error: {e}")
    # --- End Referral Handling ---

    if len(m.command) == 2 and m.command[1].startswith('notcopy'):
        _, userid, verify_id, file_id = m.command[1].split("_", 3)
        user_id = int(userid)
        grp_id = temp.CHAT.get(user_id, 0)
        settings = await get_settings(grp_id)         
        verify_id_info = await db.get_verify_id_info(user_id, verify_id)
        if not verify_id_info or verify_id_info["verified"]:
            await message.reply("<b>ʟɪɴᴋ ᴇxᴘɪʀᴇᴅ ᴛʀʏ ᴀɢᴀɪɴ...</b>")
            return  
        ist_timezone = pytz.timezone('Asia/Kolkata')
        key = "second_time_verified" if await db.is_user_verified(user_id) else "last_verified"
        current_time = datetime.now(tz=ist_timezone)  
        result = await db.update_notcopy_user(user_id, {key:current_time})
        await db.update_verify_id_info(user_id, verify_id, {"verified":True})
        num =  2 if key == "second_time_verified" else 1 
        msg = script.SECOND_VERIFY_COMPLETE_TEXT if key == "second_time_verified" else script.VERIFY_COMPLETE_TEXT
        
        log_channel_id = settings.get('log')
        if log_channel_id:
             try:
                 await client.send_message(log_channel_id, script.VERIFIED_LOG_TEXT.format(m.from_user.mention, user_id, datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%d %B %Y'), num))
             except Exception as e:
                 logger.error(f"Could not send log message to {log_channel_id}: {e}")
        else:
             logger.warning(f"Log channel not set for group {grp_id}")

        btn = [[
            InlineKeyboardButton("✅ ᴄʟɪᴄᴋ ʜᴇʀᴇ ᴛᴏ ɢᴇᴛ ꜰɪʟᴇ ✅", url=f"https://telegram.me/{temp.U_NAME}?start=file_{grp_id}_{file_id}"),
        ]]
        reply_markup=InlineKeyboardMarkup(btn)
        await m.reply_photo(
            photo=(VERIFY_IMG),
            caption=msg.format(message.from_user.mention, get_readable_time(TWO_VERIFY_GAP)),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
        return 
        
    if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        status = get_status()
        aks=await message.reply_text(f"<b>🔥 ʏᴇs {status},\nʜᴏᴡ ᴄᴀɴ ɪ ʜᴇʟᴘ ʏᴏᴜ??</b>")
        await asyncio.sleep(600)
        try:
             await aks.delete()
             await m.delete()
        except:
             pass 
        if (str(message.chat.id)).startswith("-100") and not await db.get_chat(message.chat.id):
            total=await client.get_chat_members_count(message.chat.id)
            try:
                group_link = await message.chat.export_invite_link()
            except ChatAdminRequired:
                group_link = "N/A (Bot is not admin)"
            user = message.from_user.mention if message.from_user else "Dear" 
            await client.send_message(LOG_CHANNEL, script.NEW_GROUP_TXT.format(temp.B_LINK, message.chat.title, message.chat.id, message.chat.username or 'N/A', group_link, total, user))       
            await db.add_chat(message.chat.id, message.chat.title)
        return 
    
    # --- New User Logic (with Referral) ---
    if not await db.is_user_exist(message.from_user.id):
        # Pass 'referred_by_id' (which is None or the referrer's ID)
        await db.add_user(message.from_user.id, message.from_user.first_name, referred_by=referred_by_id)
        await client.send_message(LOG_CHANNEL, script.NEW_USER_TXT.format(temp.B_LINK, message.from_user.id, message.from_user.mention))
        
        if referred_by_id:
            # Grant point to referrer
            try:
                await db.add_referral_point(referred_by_id)
                referrer_user = await client.get_users(referred_by_id)
                # Notify the new user who referred them
                await message.reply(script.NEW_REFERRAL_TXT.format(referrer_mention=referrer_user.mention)) 
            except Exception as e:
                logger.error(f"Failed to grant referral point or notify user: {e}")
    # --- End New User Logic ---

    # Handle plain /start or /start ref_...
    if len(message.command) != 2 or is_referral:
        buttons = [[
            InlineKeyboardButton('⇆ ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘs ⇆', url=f'http://t.me/{temp.U_NAME}?startgroup=start')
        ],[
            InlineKeyboardButton('⚙ ꜰᴇᴀᴛᴜʀᴇs', callback_data='features'),
            InlineKeyboardButton('💸 ᴘʀᴇᴍɪᴜᴍ', callback_data='buy_premium')
        ],[
            InlineKeyboardButton('🚫 ᴇᴀʀɴ ᴍᴏɴᴇʏ ᴡɪᴛʜ ʙᴏᴛ 🚫', callback_data='earn')
        ]]   
        reply_markup = InlineKeyboardMarkup(buttons)
        await message.reply_text(script.START_TXT.format(message.from_user.mention, get_status(), message.from_user.id),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
        return # Return here to prevent falling through to file logic

    if AUTH_CHANNEL and not await is_req_subscribed(client, message):
        try:
            invite_link = await client.create_chat_invite_link(int(AUTH_CHANNEL), creates_join_request=True)
        except ChatAdminRequired:
            logger.error("Make sure Bot is admin in Forcesub channel")
            return
        btn = [[
            InlineKeyboardButton("⛔️ ᴊᴏɪɴ ɴᴏᴡ ⛔️", url=invite_link.invite_link)
        ]]

        if message.command[1] != "subscribe":
            try:
                kk, grp_id, file_id = message.command[1].split('_', 2)
                pre = 'checksubp' if kk == 'filep' else 'checksub'
                btn.append(
                    [InlineKeyboardButton("♻️ ᴛʀʏ ᴀɢᴀɪɴ ♻️", callback_data=f"checksub#{file_id}")]
                )
            except (IndexError, ValueError):
                btn.append(
                    [InlineKeyboardButton("♻️ ᴛʀʏ ᴀɢᴀɪɴ ♻️", url=f"https://t.me/{temp.U_NAME}?start={message.command[1]}")]
                )
        await client.send_message(
            chat_id=message.from_user.id,
            text="🙁 ғɪʀꜱᴛ ᴊᴏɪɴ ᴏᴜʀ ʙᴀᴄᴋᴜᴘ ᴄʜᴀɴɴᴇʟ ᴛʜᴇɴ ʏᴏᴜ ᴡɪʟʟ ɢᴇᴛ ᴍᴏᴠɪᴇ, ᴏᴛʜᴇʀᴡɪꜱᴇ ʏᴏᴜ ᴡɪʟʟ ɴᴏᴛ ɢᴇᴛ ɪᴛ.\n\nᴄʟɪᴄᴋ ᴊᴏɪɴ ɴᴏᴡ ʙᴜᴛᴛᴏɴ 👇",
            reply_markup=InlineKeyboardMarkup(btn),
            parse_mode=enums.ParseMode.HTML
        )
        return

    if len(message.command) == 2 and message.command[1] in ["subscribe", "error", "okay", "help", "buy_premium"]:
        if message.command[1] == "buy_premium":
            btn = [[
                InlineKeyboardButton('📸 sᴇɴᴅ sᴄʀᴇᴇɴsʜᴏᴛ 📸', url=USERNAME)
            ],[
                InlineKeyboardButton('🗑 ᴄʟᴏsᴇ 🗑', callback_data='close_data')
            ]]            
            await message.reply_photo(
                photo=(QR_CODE),
                caption=script.PREMIUM_TEXT.format(message.from_user.mention),
                reply_markup=InlineKeyboardMarkup(btn)
            )
            return
        buttons = [[
            InlineKeyboardButton('⇆ ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘs ⇆', url=f'http://t.me/{temp.U_NAME}?startgroup=start')
        ],[
            InlineKeyboardButton('⚙ ꜰᴇᴀᴛᴜʀᴇs', callback_data='features'),
            InlineKeyboardButton('💸 ᴘʀᴇᴍɪᴜᴍ', callback_data='buy_premium')
        ],[
            InlineKeyboardButton('🚫 ᴇᴀʀɴ ᴍᴏɴᴇʏ ᴡɪᴛʜ ʙᴏᴛ 🚫', callback_data='earn')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await message.reply_text(
            text=script.START_TXT.format(message.from_user.mention, get_status(), message.from_user.id),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
        return

    data = message.command[1]
    try:
        pre, grp_id_str, file_id = data.split('_', 2)
        grp_id = int(grp_id_str) # Convert grp_id to integer early
    except:
        pre, grp_id, file_id = "", 0, data 
        try:
            decoded_data = (base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))).decode("ascii")
            pre, file_id = decoded_data.split("_", 1)
            grp_id = 0 
        except Exception as e:
            logger.error(f"Failed to process start command data: {data} - Error: {e}")
            return await message.reply('<b>⚠️ ɪɴᴠᴀʟɪᴅ ʟɪɴᴋ ᴏʀ ꜰɪʟᴇ ɪᴅ. ⚠️</b>')

    user_id = m.from_user.id
    if grp_id != 0: 
         if not await db.has_premium_access(user_id):
             user_verified = await db.is_user_verified(user_id)
             settings = await get_settings(grp_id)
             is_second_shortener = await db.use_second_shortener(user_id, settings.get('verify_time', TWO_VERIFY_GAP))        
             if settings.get("is_verify", IS_VERIFY) and not user_verified or is_second_shortener:
                 verify_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=7))
                 await db.create_verify_id(user_id, verify_id)
                 temp.CHAT[user_id] = grp_id
                 verify = await get_shortlink(f"https://telegram.me/{temp.U_NAME}?start=notcopy_{user_id}_{verify_id}_{file_id}", grp_id, is_second_shortener)
                 buttons = [[
                     InlineKeyboardButton(text="✅️ ᴠᴇʀɪғʏ ✅️", url=verify),
                     InlineKeyboardButton(text="⁉️ ʜᴏᴡ ᴛᴏ ᴠᴇʀɪғʏ ⁉️", url=settings.get('tutorial', '')) 
                 ],[
                     InlineKeyboardButton("😁 ʙᴜʏ ꜱᴜʙꜱᴄʀɪᴘᴛɪᴏɴ - ɴᴏ ɴᴇᴇᴅ ᴛᴏ ᴠᴇʀɪғʏ 😁", callback_data='buy_premium')
                 ]]
                 reply_markup=InlineKeyboardMarkup(buttons)            
                 msg = script.SECOND_VERIFICATION_TEXT if is_second_shortener else script.VERIFICATION_TEXT
                 try:
                     d = await m.reply_text(
                         text=msg.format(message.from_user.mention, get_status()),
                         protect_content = False,
                         reply_markup=reply_markup,
                         parse_mode=enums.ParseMode.HTML
                     )
                     await asyncio.sleep(300) 
                     await d.delete()
                     await m.delete()
                 except Exception as e:
                      logger.error(f"Error sending/deleting verify message: {e}")
                 return
            
    if data and data.startswith("allfiles"):
        _, key = data.split("_", 1)
        if '-' not in key:
             await message.reply_text("<b>⚠️ ɪɴᴠᴀʟɪᴅ ꜰᴏʀᴍᴀᴛ ꜰᴏʀ ʙᴀᴛᴄʜ ꜰɪʟᴇꜱ. ⚠️</b>")
             return
             
        files = temp.FILES_ID.get(key)
        if not files:
            await message.reply_text("<b>⚠️ ᴀʟʟ ꜰɪʟᴇs ɴᴏᴛ ꜰᴏᴜɴᴅ ᴏʀ ʟɪɴᴋ ᴇxᴘɪʀᴇᴅ. ⚠️</b>")
            return
            
        try:
             grp_id_from_key = int(key.split('-')[0])
             settings = await get_settings(grp_id_from_key)
        except (ValueError, IndexError, TypeError):
             await message.reply_text("<b>⚠️ ᴄᴏᴜʟᴅ ɴᴏᴛ ʟᴏᴀᴅ ɢʀᴏᴜᴘ sᴇᴛᴛɪɴɢs. ᴜsɪɴɢ ᴅᴇꜰᴀᴜʟᴛs. ⚠️</b>")
             settings = {'caption': FILE_CAPTION, 'file_secure': False} 
             
        for file in files:
            CAPTION = settings.get('caption', FILE_CAPTION) 
            f_caption = CAPTION.format(
                file_name = getattr(file, 'file_name', 'N/A'), 
                file_size = get_size(getattr(file, 'file_size', 0)),
                file_caption=getattr(file, 'caption', '') or '' 
            )
            btn=[[
                InlineKeyboardButton("✛ ᴡᴀᴛᴄʜ & ᴅᴏᴡɴʟᴏᴀᴅ ✛", callback_data=f'stream#{file.file_id}')
            ]]
            try:
                await client.send_cached_media(
                    chat_id=message.from_user.id,
                    file_id=file.file_id,
                    caption=f_caption,
                    protect_content=settings.get('file_secure', False), 
                    reply_markup=InlineKeyboardMarkup(btn)
                )
            except Exception as e:
                 logger.error(f"Error sending batch file {file.file_id} to {message.from_user.id}: {e}")
                 await message.reply_text(f"<b>⚠️ Sᴏʀʀʏ, ᴄᴏᴜʟᴅ ɴᴏᴛ sᴇɴᴅ ᴏɴᴇ ᴏꜰ ᴛʜᴇ ꜰɪʟᴇs ({getattr(file, 'file_name', 'N/A')}).</b>")
        return

    files_ = await get_file_details(file_id)           
    if not files_:
        if pre == "" and grp_id == 0: 
            try:
                 decoded_data = (base64.urlsafe_b64decode(file_id + "=" * (-len(file_id) % 4))).decode("ascii")
                 pre_decoded, file_id_decoded = decoded_data.split("_", 1)
                 files_ = await get_file_details(file_id_decoded)
                 if files_:
                      file_id = file_id_decoded 
                 else:
                      return await message.reply('<b>⚠️ ꜰɪʟᴇ ɴᴏᴛ ꜰᴏᴜɴᴅ. ⚠️</b>')
            except:
                 return await message.reply('<b>⚠️ ꜰɪʟᴇ ɴᴏᴛ ꜰᴏᴜɴᴅ / ɪɴᴠᴀʟɪᴅ ʟɪɴᴋ. ⚠️</b>')
        else:
            return await message.reply('<b>⚠️ ꜰɪʟᴇ ɴᴏᴛ ꜰᴏᴜɴᴅ. ⚠️</b>')

    files = files_[0]
    
    if grp_id != 0:
        settings = await get_settings(grp_id)
    else:
        grp_id = temp.CHAT.get(user_id, 0)
        if grp_id != 0:
             settings = await get_settings(grp_id)
        else:
             settings = {'caption': FILE_CAPTION, 'file_secure': False}
             logger.warning(f"Could not determine grp_id for file request. User: {user_id}, File: {file_id}. Using default settings.")

    CAPTION = settings.get('caption', FILE_CAPTION)
    f_caption = CAPTION.format(
        file_name = files.file_name,
        file_size = get_size(files.file_size),
        file_caption=files.caption or '' 
    )
    btn = [[
        InlineKeyboardButton("✛ ᴡᴀᴛᴄʜ & ᴅᴏᴡɴʟᴏᴀᴅ ✛", callback_data=f'stream#{file_id}')
    ]]
    try:
        d=await client.send_cached_media(
            chat_id=message.from_user.id,
            file_id=file_id,
            caption=f_caption,
            protect_content=settings.get('file_secure', False),
            reply_markup=InlineKeyboardMarkup(btn)
        )
        await asyncio.sleep(3600)
        await d.delete()
        await message.reply_text("<b>⚠️ ʏᴏᴜʀ ʀᴇǫᴜᴇsᴛᴇᴅ ᴍᴏᴠɪᴇ ꜰɪʟᴇ ɪs ᴅᴇʟᴇᴛᴇᴅ ᴀꜰᴛᴇʀ 1 ʜᴏᴜʀ ᴛᴏ ᴀᴠᴏɪᴅ ᴄᴏᴘʏʀɪɢʜᴛ. Iꜰ ʏᴏᴜ ᴡᴀɴᴛ ɪᴛ ᴀɢᴀɪɴ, ᴘʟᴇᴀsᴇ sᴇᴀʀᴄʜ ᴀɢᴀɪɴ. ☺️</b>")         
    except Exception as e:
         logger.error(f"Error sending single file {file_id} to {message.from_user.id}: {e}")
         await message.reply_text("<b>⚠️ Sᴏʀʀʏ, ᴀɴ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ ᴡʜɪʟᴇ sᴇɴᴅɪɴɢ ᴛʜᴇ ꜰɪʟᴇ.</b>")

@Client.on_message(filters.command('delete'))
async def delete(bot, message):
    if message.from_user.id not in ADMINS:
        await message.reply('ᴏɴʟʏ ᴛʜᴇ ʙᴏᴛ ᴏᴡɴᴇʀ ᴄᴀɴ ᴜsᴇ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ... 😑')
        return
    """Delete file from database"""
    reply = message.reply_to_message
    if reply and reply.media:
        msg = await message.reply("ᴘʀᴏᴄᴇssɪɴɢ...⏳", quote=True)
    else:
        await message.reply('Reply to file with /delete which you want to delete', quote=True)
        return
    for file_type in ("document", "video", "audio"):
        media = getattr(reply, file_type, None)
        if media is not None:
            break
    else:
        await msg.edit('<b>ᴛʜɪs ɪs ɴᴏᴛ sᴜᴘᴘᴏʀᴛᴇᴅ ꜰɪʟᴇ ꜰᴏʀᴍᴀᴛ</b>')
        return
    
    try:
        file_id, file_ref = unpack_new_file_id(media.file_id)
        result = await Media.collection.delete_one({
            '_id': file_id,
        })
        if result.deleted_count:
            await msg.edit('<b>ꜰɪʟᴇ ɪs sᴜᴄᴄᴇssꜰᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ ꜰʀᴏᴍ ᴅᴀᴛᴀʙᴀsᴇ 💥</b>')
        else:
            file_name = re.sub(r"(_|\-|\.|\+)", " ", str(media.file_name))
            result = await Media.collection.delete_many({
                'file_name': file_name,
                'file_size': media.file_size,
                'mime_type': media.mime_type
                })
            if result.deleted_count:
                await msg.edit(f'<b>{result.deleted_count} ꜰɪʟᴇ(s) ᴡɪᴛʜ sɪᴍɪʟᴀʀ ɴᴀᴍᴇ/sɪᴢᴇ sᴜᴄᴄᴇssꜰᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ ꜰʀᴏᴍ ᴅᴀᴛᴀʙᴀsᴇ 💥</b>')
            else:
                 result = await Media.collection.delete_many({
                     'file_name': media.file_name,
                     'file_size': media.file_size,
                     'mime_type': media.mime_type
                 })
                 if result.deleted_count:
                     await msg.edit(f'<b>{result.deleted_count} ꜰɪʟᴇ(s) ᴡɪᴛʜ ᴇxᴀᴄᴛ ɴᴀᴍᴇ/sɪᴢᴇ sᴜᴄᴄᴇssꜰᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ ꜰʀᴏᴍ ᴅᴀᴛᴀʙᴀsᴇ 💥</b>')
                 else:
                    await msg.edit('<b>ꜰɪʟᴇ ɴᴏᴛ ꜰᴏᴜɴᴅ ɪɴ ᴅᴀᴛᴀʙᴀsᴇ</b>')
    except Exception as e:
        logger.error(f"Error during file deletion: {e}")
        await msg.edit(f'<b>ᴀɴ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ: {e}</b>')


@Client.on_message(filters.command('deleteall'))
async def delete_all_index(bot, message):
    if message.from_user.id not in ADMINS:
        await message.reply('ᴏɴʟʏ ᴛʜᴇ ʙᴏᴛ ᴏᴡɴᴇʀ ᴄᴀɴ ᴜsᴇ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ... 😑')
        return
        
    try:
        files = await Media.count_documents()
        if int(files) == 0:
            return await message.reply_text('ɴᴏ ꜰɪʟᴇs ᴛᴏ ᴅᴇʟᴇᴛᴇ.')
        btn = [[
                InlineKeyboardButton(text="⚠️ ʏᴇs, ᴅᴇʟᴇᴛᴇ ᴀʟʟ!", callback_data="all_files_delete")
            ],[
                InlineKeyboardButton(text="🚫 ᴄᴀɴᴄᴇʟ", callback_data="close_data")
            ]]
        await message.reply_text(f'<b>ᴀʀᴇ ʏᴏᴜ sᴜʀᴇ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ᴅᴇʟᴇᴛᴇ ᴀʟʟ {files} ɪɴᴅᴇxᴇᴅ ꜰɪʟᴇs?\n\nᴛʜɪꜱ ᴀᴄᴛɪᴏɴ ɪꜱ ɪʀʀᴇᴠᴇʀsɪʙʟᴇ!</b>', reply_markup=InlineKeyboardMarkup(btn))
    except Exception as e:
        logger.error(f"Error counting documents for deleteall: {e}")
        await message.reply_text(f"<b>ᴄᴏᴜʟᴅ ɴᴏᴛ ᴄʜᴇᴄᴋ ᴅᴀᴛᴀʙᴀsᴇ sᴛᴀᴛᴜs. ᴇʀʀᴏʀ: {e}</b>")


@Client.on_message(filters.command('settings'))
async def settings(client, message):
    user_id = message.from_user.id if message.from_user else None
    if not user_id:
        try:
             await message.delete()
        except:
             pass
        return 
        
    chat_type = message.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await message.reply_text("<b>ᴜsᴇ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ɪɴ ᴀ ɢʀᴏᴜᴘ.</b>")
        
    grp_id = message.chat.id
    is_admin = await is_check_admin(client, grp_id, message.from_user.id)
    if not is_admin:
        return await message.reply_text('<b>ʏᴏᴜ ᴍᴜsᴛ ʙᴇ ᴀɴ ᴀᴅᴍɪɴ ɪɴ ᴛʜɪꜱ ɢʀᴏᴜᴘ ᴛᴏ ᴜsᴇ ᴛʜɪs.</b>')
        
    settings = await get_settings(grp_id)
    title = message.chat.title
    if settings is not None:
            buttons = [[
                InlineKeyboardButton('ᴀᴜᴛᴏ ꜰɪʟᴛᴇʀ', callback_data=f'setgs#auto_filter#{settings["auto_filter"]}#{grp_id}'),
                InlineKeyboardButton('✅ ᴏɴ' if settings["auto_filter"] else '❌ ᴏғғ', callback_data=f'setgs#auto_filter#{settings["auto_filter"]}#{grp_id}')
            ],[
                InlineKeyboardButton('ꜰɪʟᴇ sᴇᴄᴜʀᴇ', callback_data=f'setgs#file_secure#{settings["file_secure"]}#{grp_id}'),
                InlineKeyboardButton('✅ ᴏɴ' if settings["file_secure"] else '❌ ᴏғғ', callback_data=f'setgs#file_secure#{settings["file_secure"]}#{grp_id}')
            ],[
                InlineKeyboardButton('ɪᴍᴅʙ', callback_data=f'setgs#imdb#{settings["imdb"]}#{grp_id}'),
                InlineKeyboardButton('✅ ᴏɴ' if settings["imdb"] else '❌ ᴏғғ', callback_data=f'setgs#imdb#{settings["imdb"]}#{grp_id}')
            ],[
                InlineKeyboardButton('sᴘᴇʟʟ ᴄʜᴇᴄᴋ', callback_data=f'setgs#spell_check#{settings["spell_check"]}#{grp_id}'),
                InlineKeyboardButton('✅ ᴏɴ' if settings["spell_check"] else '❌ ᴏғғ', callback_data=f'setgs#spell_check#{settings["spell_check"]}#{grp_id}')
            ],[
                InlineKeyboardButton('ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ', callback_data=f'setgs#auto_delete#{settings["auto_delete"]}#{grp_id}'),
                InlineKeyboardButton(f'{get_readable_time(DELETE_TIME)}' if settings["auto_delete"] else '❌ ᴏғғ', callback_data=f'setgs#auto_delete#{settings["auto_delete"]}#{grp_id}')
            ],[
                InlineKeyboardButton('ʀᴇsᴜʟᴛ ᴍᴏᴅᴇ', callback_data=f'setgs#link#{settings["link"]}#{str(grp_id)}'),
                InlineKeyboardButton('🔗 ʟɪɴᴋ' if settings["link"] else '🔘 ʙᴜᴛᴛᴏɴ', callback_data=f'setgs#link#{settings["link"]}#{str(grp_id)}')
            ],[
                InlineKeyboardButton('ᴠᴇʀɪғʏ', callback_data=f'setgs#is_verify#{settings["is_verify"]}#{grp_id}'),
                InlineKeyboardButton('✅ ᴏɴ' if settings["is_verify"] else '❌ ᴏғғ', callback_data=f'setgs#is_verify#{settings["is_verify"]}#{grp_id}')
            ],[
                InlineKeyboardButton('☕️ ᴄʟᴏsᴇ ☕️', callback_data='close_data')
            ]]
            try:
                await message.reply_text(
                    text=f"⚙️ ᴄᴏɴꜰɪɢᴜʀᴇ sᴇᴛᴛɪɴɢs ꜰᴏʀ <b>'{title}'</b>:",
                    reply_markup=InlineKeyboardMarkup(buttons),
                    parse_mode=enums.ParseMode.HTML
                )
            except Exception as e:
                 logger.error(f"Error sending settings message: {e}")
    else:
        await message.reply_text('<b>⚠️ Sᴏᴍᴇᴛʜɪɴɢ ᴡᴇɴᴛ ᴡʀᴏɴɢ, ᴄᴏᴜʟᴅ ɴᴏᴛ ꜰᴇᴛᴄʜ sᴇᴛᴛɪɴɢs.</b>')


@Client.on_message(filters.command('set_template'))
async def save_template(client, message):
    chat_type = message.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await message.reply_text("<b>ᴜꜱᴇ ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ ɪɴ ᴀ ɢʀᴏᴜᴘ.</b>")
        
    grp_id = message.chat.id
    is_admin = await is_check_admin(client, grp_id, message.from_user.id)
    if not is_admin:
        return await message.reply_text('<b>ʏᴏᴜ ᴍᴜsᴛ ʙᴇ ᴀɴ ᴀᴅᴍɪɴ ɪɴ ᴛʜɪꜱ ɢʀᴏᴜᴘ.</b>')
        
    try:
        template = message.text.split(" ", 1)[1]
    except IndexError:
        return await message.reply_text("<b>⚠️ ᴄᴏᴍᴍᴀɴᴅ ɪɴᴄᴏᴍᴘʟᴇᴛᴇ!\n\nUsage:</b> `/set_template {template_text}`\n\nUse placeholders like `{title}`, `{rating}`, etc.")    
        
    try:
        await save_group_settings(grp_id, 'template', template)
        await message.reply_text(f"✅ sᴜᴄᴄᴇssꜰᴜʟʟʏ ᴄʜᴀɴɢᴇᴅ ɪᴍᴅʙ ᴛᴇᴍᴘʟᴀᴛᴇ ꜰᴏʀ <b>{message.chat.title}</b> ᴛᴏ:\n\n`{template}`", disable_web_page_preview=True)
    except Exception as e:
        logger.error(f"Error saving template for group {grp_id}: {e}")
        await message.reply_text(f"<b>⚠️ ꜰᴀɪʟᴇᴅ ᴛᴏ sᴀᴠᴇ ᴛᴇᴍᴘʟᴀᴛᴇ. ᴇʀʀᴏʀ: {e}</b>")

    
@Client.on_message(filters.command("send"))
async def send_msg(bot, message):
    if message.from_user.id not in ADMINS:
        return await message.reply('<b>ᴏɴʟʏ ᴛʜᴇ ʙᴏᴛ ᴏᴡɴᴇʀ ᴄᴀɴ ᴜꜱᴇ ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ.</b>')
        
    if message.reply_to_message:
        target_ids_str = message.text.split(" ", 1)
        if len(target_ids_str) < 2 or not target_ids_str[1]:
             return await message.reply_text("<b>ᴘʟᴇᴀꜱᴇ ᴘʀᴏᴠɪᴅᴇ ᴏɴᴇ ᴏʀ ᴍᴏʀᴇ ᴜꜱᴇʀ/ᴄʜᴀᴛ ɪᴅꜱ sᴇᴘᴀʀᴀᴛᴇᴅ ʙʏ sᴘᴀᴄᴇ.\n\nUsage:</b> `/send ID1 ID2 ID3...` (Reply to the message you want to send)")
             
        target_ids = target_ids_str[1].split()
        out = "<b><u>ʀᴇᴘᴏʀᴛ:</u></b>\n\n"
        success_count = 0
        fail_count = 0
        
        status_msg = await message.reply_text(f"<b>sᴇɴᴅɪɴɢ ᴍᴇssᴀɢᴇ ᴛᴏ {len(target_ids)} ɪᴅ(s)...</b>")
        
        for i, target_id_str in enumerate(target_ids):
            try:
                target_id = int(target_id_str.strip())
                user_info = await bot.get_chat(target_id) 
                
                await message.reply_to_message.copy(target_id)
                success_count += 1
                out += f"✅ sᴇɴᴛ ᴛᴏ: {user_info.title or user_info.first_name} [`{target_id}`]\n"
            except ValueError:
                fail_count += 1
                out += f"❌ ɪɴᴠᴀʟɪᴅ ɪᴅ: `{target_id_str}`\n"
            except Exception as e:
                fail_count += 1
                out += f"❌ ꜰᴀɪʟᴇᴅ ꜰᴏʀ `{target_id_str}`: {e}\n"
                
            if (i + 1) % 10 == 0 or (i + 1) == len(target_ids):
                 try:
                     await status_msg.edit_text(f"<b>ᴘʀᴏɢʀᴇss: {i + 1}/{len(target_ids)}\nsᴜᴄᴄᴇss: {success_count} | ꜰᴀɪʟᴜʀᴇ: {fail_count}</b>")
                 except FloodWait as fw:
                     await asyncio.sleep(fw.value + 1)
                 except MessageNotModified:
                     pass 
                     
            await asyncio.sleep(1) 

        try:
             await status_msg.edit_text(f"<b><u>ꜰɪɴᴀʟ ʀᴇᴘᴏʀᴛ:</u>\n✅ sᴜᴄᴄᴇssꜰᴜʟʟʏ sᴇɴᴛ ᴛᴏ {success_count} ɪᴅ(s).\n❌ ꜰᴀɪʟᴇᴅ ꜰᴏʀ {fail_count} ɪᴅ(s).</b>")
             if len(out) > 4000:
                  with open("send_report.txt", "w") as f:
                       f.write(out.replace('<b>','').replace('</b>','').replace('<u>','').replace('</u>','').replace('<code>','').replace('</code>',''))
                  await message.reply_document("send_report.txt", caption="Detailed Send Report")
                  os.remove("send_report.txt")
             else:
                  await message.reply_text(out)
        except Exception as e:
             logger.error(f"Error sending final report for /send: {e}")
             await message.reply_text("<b>ᴇʀʀᴏʀ ɢᴇɴᴇʀᴀᴛɪɴɢ ꜰɪɴᴀʟ ʀᴇᴘᴏʀᴛ.</b>")

    else:
        await message.reply_text("<b>⚠️ ᴘʟᴇᴀsᴇ ʀᴇᴘʟʏ ᴛᴏ ᴛʜᴇ ᴍᴇssᴀɢᴇ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ sᴇɴᴅ.\n\nUsage:</b> `/send ID1 ID2 ID3...`")


@Client.on_message(filters.regex("#request") & filters.chat(REQUEST_CHANNEL) == False) 
async def send_request(bot, message):
    if not REQUEST_CHANNEL:
         return await message.reply_text("<b>⚠️ ʀᴇǫᴜᴇsᴛ ғᴇᴀᴛᴜʀᴇ ɪs ᴅɪsᴀʙʟᴇᴅ (ɴᴏ ʀᴇǫᴜᴇsᴛ ᴄʜᴀɴɴᴇʟ sᴇᴛ).</b>")
         
    try:
        request_text = message.text.split(" ", 1)[1].strip()
        if not request_text:
             raise IndexError 
    except IndexError:
        await message.reply_text("<b>⚠️ ᴘʟᴇᴀsᴇ ᴘʀᴏᴠɪᴅᴇ ʏᴏᴜʀ ʀᴇǫᴜᴇsᴛ ᴀꜰᴛᴇʀ #request.\n\nExample:</b> `#request Movie Name (Year)`")
        return
        
    user_mention = message.from_user.mention
    user_id = message.from_user.id
    original_msg_link = message.link

    buttons = [[
        InlineKeyboardButton('👀 ᴠɪᴇᴡ ᴏʀɪɢɪɴᴀʟ ʀᴇǫᴜᴇꜱᴛ 👀', url=original_msg_link)
    ],[
        InlineKeyboardButton('⚙️ ᴀᴅᴍɪɴ ᴏᴘᴛɪᴏɴs ⚙️', callback_data=f'show_options#{user_id}#{message.id}') 
    ]]
    
    try:
        sent_request_msg = await bot.send_message(
            REQUEST_CHANNEL, 
            script.REQUEST_TXT.format(user_mention, user_id, request_text), 
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        
        btn_view = [[
             InlineKeyboardButton('✨ ᴠɪᴇᴡ ʏᴏᴜʀ ʀᴇǫᴜᴇꜱᴛ sᴛᴀᴛᴜs ✨', url=sent_request_msg.link)
        ]]
        await message.reply_text(
            "<b>✅ sᴜᴄᴄᴇssғᴜʟʟʏ sᴜʙᴍɪᴛᴛᴇᴅ ʏᴏᴜʀ ʀᴇǫᴜᴇꜱᴛ. ᴀᴅᴍɪɴs ᴡɪʟʟ ʀᴇᴠɪᴇᴡ ɪᴛ.</b>", 
            reply_markup=InlineKeyboardMarkup(btn_view)
        )
    except Exception as e:
        logger.error(f"Failed to send request to REQUEST_CHANNEL ({REQUEST_CHANNEL}): {e}")
        await message.reply_text(f"<b>⚠️ Sᴏʀʀʏ, ᴄᴏᴜʟᴅ ɴᴏᴛ sᴜʙᴍɪᴛ ʏᴏᴜʀ ʀᴇǫᴜᴇsᴛ ᴀᴛ ᴛʜɪs ᴛɪᴍᴇ. ᴘʟᴇᴀsᴇ ᴛʀʏ ᴀɢᴀɪɴ ʟᴀᴛᴇʀ ᴏʀ ᴄᴏɴᴛᴀᴄᴛ ᴀɴ ᴀᴅᴍɪɴ.\nError: {e}</b>")


@Client.on_message(filters.command("search") & filters.private)
async def search_files_cmd(bot, message):
    if message.from_user.id not in ADMINS:
        return await message.reply('<b>ᴏɴʟʏ ᴛʜᴇ ʙᴏᴛ ᴏᴡɴᴇʀ ᴄᴀɴ ᴜsᴇ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ.</b>')
        
    try:
        keyword = message.text.split(" ", 1)[1].strip()
        if not keyword: raise IndexError
    except IndexError:
        return await message.reply_text("<b>⚠️ ᴘʟᴇᴀsᴇ ᴘʀᴏᴠɪᴅᴇ ᴀ ᴋᴇʏᴡᴏʀᴅ ᴛᴏ sᴇᴀʀᴄʜ.\n\nUsage:</b> `/search keyword`")
        
    msg = await message.reply_text("<b>sᴇᴀʀᴄʜɪɴɢ ꜰɪʟᴇs... ⏳</b>")
    
    try:
        files, total = await get_bad_files(keyword) 
        
        if total == 0:
            return await msg.edit_text('<i>🚫 ɴᴏ ꜰɪʟᴇs ꜰᴏᴜɴᴅ ᴍᴀᴛᴄʜɪɴɢ ᴛʜɪs ᴋᴇʏᴡᴏʀᴅ.</i>') 
            
        file_list_text = f"🔎 ꜰᴏᴜɴᴅ {total} ꜰɪʟᴇ(s) ꜰᴏʀ '<b>{keyword}</b>':\n\n"
        max_files_in_message = 50 
        
        for index, item in enumerate(files[:max_files_in_message]):
             file_list_text += f"{index + 1}. `{item.file_name}` ({get_size(item.file_size)})\n"
             
        if total > max_files_in_message:
             file_list_text += f"\n...ᴀɴᴅ {total - max_files_in_message} ᴍᴏʀᴇ."

        full_file_data = f"Full list for '{keyword}' ({total} files):\n\n" + "\n".join(
            f"{index + 1}. {item.file_name} ({get_size(item.file_size)}) - ID: {item.file_id}" 
            for index, item in enumerate(files)
        )
            
        temp_file_path = f"search_results_{keyword.replace(' ','_')}.txt"
        with open(temp_file_path, "w", encoding='utf-8') as file:
             file.write(full_file_data)
             
        await msg.delete() 
        
        await message.reply_document(
            document=temp_file_path,
            caption=f"<b>📄 ғᴜʟʟ ʟɪsᴛ ᴏꜰ {total} ꜰɪʟᴇ(s) ғᴏᴜɴᴅ ғᴏʀ '<code>{keyword}</code>'.</b>\n\nFirst {min(total, max_files_in_message)} results shown below:",
            parse_mode=enums.ParseMode.HTML
        )
        await message.reply_text(file_list_text, parse_mode=enums.ParseMode.HTML) 

        os.remove(temp_file_path) 

    except Exception as e:
        logger.error(f"Error during /search command: {e}")
        await msg.edit_text(f"<b>⚠️ ᴀɴ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ ᴅᴜʀɪɴɢ sᴇᴀʀᴄʜ: {e}</b>")


@Client.on_message(filters.command("deletefiles") & filters.private)
async def delete_multiple_files_cmd(bot, message):
    if message.from_user.id not in ADMINS:
        return await message.reply('<b>ᴏɴʟʏ ᴛʜᴇ ʙᴏᴛ ᴏᴡɴᴇʀ ᴄᴀɴ ᴜsᴇ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ.</b>')
        
    try:
        keyword = message.text.split(" ", 1)[1].strip()
        if not keyword: raise IndexError
    except IndexError:
        return await message.reply_text("<b>⚠️ ᴘʟᴇᴀsᴇ ᴘʀᴏᴠɪᴅᴇ ᴀ ᴋᴇʏᴡᴏʀᴅ ᴛᴏ ᴅᴇʟᴇᴛᴇ.\n\nUsage:</b> `/deletefiles keyword`")
        
    msg = await message.reply_text("<b>ᴄʜᴇᴄᴋɪɴɢ ꜰᴏʀ ꜰɪʟᴇs ᴛᴏ ᴅᴇʟᴇᴛᴇ... ⏳</b>")
    
    try:
        files, total = await get_bad_files(keyword) 
        
        if total == 0:
            return await msg.edit_text('<i>🚫 ɴᴏ ꜰɪʟᴇs ꜰᴏᴜɴᴅ ᴍᴀᴛᴄʜɪɴɢ ᴛʜɪs ᴋᴇʏᴡᴏʀᴅ ᴛᴏ ᴅᴇʟᴇᴛᴇ.</i>') 
            
        btn = [[
           InlineKeyboardButton("⚠️ ʏᴇs, ᴅᴇʟᴇᴛᴇ ᴛʜᴇᴍ!", callback_data=f"killfilesak#{keyword}")
           ],[
           InlineKeyboardButton("🚫 ɴᴏ, ᴄᴀɴᴄᴇʟ", callback_data="close_data")
        ]]
        
        await msg.edit_text(
            text=f"<b>ꜰᴏᴜɴᴅ {total} ꜰɪʟᴇ(s) ᴍᴀᴛᴄʜɪɴɢ '<code>{keyword}</code>'.\n\nᴀʀᴇ ʏᴏᴜ sᴜʀᴇ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ᴘᴇʀᴍᴀɴᴇɴᴛʟʏ ᴅᴇʟᴇᴛᴇ ᴛʜᴇᴍ?\n\nᴛʜɪꜱ ᴀᴄᴛɪᴏɴ ɪꜱ ɪʀʀᴇᴠᴇʀsɪʙʟᴇ!</b>",
            reply_markup=InlineKeyboardMarkup(btn),
            parse_mode=enums.ParseMode.HTML
        )
    except Exception as e:
        logger.error(f"Error during /deletefiles check: {e}")
        await msg.edit_text(f"<b>⚠️ ᴀɴ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ: {e}</b>")


@Client.on_message(filters.command("del_file") & filters.private)
async def delete_specific_files_cmd(bot, message):
    if message.from_user.id not in ADMINS:
        return await message.reply('<b>ᴏɴʟʏ ᴛʜᴇ ʙᴏᴛ ᴏᴡɴᴇʀ ᴄᴀɴ ᴜsᴇ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ.</b>')
        
    try:
        keywords_str = message.text.split(" ", 1)[1].strip()
        if not keywords_str: raise IndexError
        keywords = [kw.strip() for kw in keywords_str.split(",") if kw.strip()]
        if not keywords: raise IndexError
    except IndexError:
        return await message.reply_text("<b>⚠️ ᴘʟᴇᴀsᴇ ᴘʀᴏᴠɪᴅᴇ ᴏɴᴇ ᴏʀ ᴍᴏʀᴇ ᴇxᴀᴄᴛ ꜰɪʟᴇɴᴀᴍᴇs sᴇᴘᴀʀᴀᴛᴇᴅ ʙʏ ᴄᴏᴍᴍᴀs.\n\nUsage:</b> `/del_file filename1.mkv, filename2.mp4`")   
        
    msg = await message.reply_text(f"<b>ᴘʀᴏᴄᴇssɪɴɢ ᴅᴇʟᴇᴛɪᴏɴ ꜰᴏʀ {len(keywords)} ꜰɪʟᴇɴᴀᴍᴇ(s)... ⏳</b>")
    
    deleted_files_count = 0
    not_found_files = []
    error_files = []
    
    for keyword in keywords:
        try:
            result = await Media.collection.delete_many({'file_name': keyword}) 
            if result.deleted_count > 0:
                deleted_files_count += result.deleted_count
            else:
                not_found_files.append(keyword)
        except Exception as e:
            logger.error(f"Error deleting file '{keyword}': {e}")
            error_files.append(f"{keyword} ({e})")
            
    report = f"<b><u>ᴅᴇʟᴇᴛɪᴏɴ ʀᴇᴘᴏʀᴛ:</u></b>\n\n"
    if deleted_files_count > 0:
        report += f"✅ sᴜᴄᴄᴇssꜰᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ {deleted_files_count} ꜰɪʟᴇ(s).\n"
    if not_found_files:
        report += f"🤷‍♀️ ɴᴏᴛ ꜰᴏᴜɴᴅ: {', '.join([f'`{nf}`' for nf in not_found_files])}\n"
    if error_files:
        report += f"❌ ᴇʀʀᴏʀs: {', '.join([f'`{err}`' for err in error_files])}\n"
        
    if deleted_files_count == 0 and not not_found_files and not error_files:
         report = "<b>⚠️ ɴᴏ ᴀᴄᴛɪᴏɴ ᴛᴀᴋᴇɴ. ᴘʟᴇᴀsᴇ ᴄʜᴇᴄᴋ ɪɴᴘᴜᴛ.</b>"

    await msg.edit_text(report)


@Client.on_message(filters.command('set_caption'))
async def save_caption(client, message):
    grp_id = message.chat.id
    title = message.chat.title
    is_admin = await is_check_admin(client, grp_id, message.from_user.id)
    if not is_admin:
        return await message.reply_text('<b>ʏᴏᴜ ᴍᴜsᴛ ʙᴇ ᴀɴ ᴀᴅᴍɪɴ ɪɴ ᴛʜɪꜱ ɢʀᴏᴜᴘ.</b>')
        
    chat_type = message.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await message.reply_text("<b>ᴜꜱᴇ ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ ɪɴ ᴀ ɢʀᴏᴜᴘ.</b>")
        
    try:
        caption = message.text.split(" ", 1)[1].strip()
        if not caption: raise IndexError
    except IndexError:
        return await message.reply_text("<b>⚠️ ᴄᴏᴍᴍᴀɴᴅ ɪɴᴄᴏᴍᴘʟᴇᴛᴇ!\n\nUsage:</b> `/set_caption {caption_text}`\n\nUse placeholders: `{file_name}`, `{file_size}`, `{file_caption}`")
        
    try:
        await save_group_settings(grp_id, 'caption', caption)
        await message.reply_text(f"✅ sᴜᴄᴄᴇssꜰᴜʟʟʏ ᴄʜᴀɴɢᴇᴅ ꜰɪʟᴇ ᴄᴀᴘᴛɪᴏɴ ꜰᴏʀ <b>{title}</b> ᴛᴏ:\n\n`{caption}`", disable_web_page_preview=True) 
    except Exception as e:
         logger.error(f"Error saving caption for group {grp_id}: {e}")
         await message.reply_text(f"<b>⚠️ ꜰᴀɪʟᴇᴅ ᴛᴏ sᴀᴠᴇ ᴄᴀᴘᴛɪᴏɴ. ᴇʀʀᴏʀ: {e}</b>")
    
@Client.on_message(filters.command('set_tutorial'))
async def save_tutorial(client, message):
    grp_id = message.chat.id
    title = message.chat.title
    is_admin = await is_check_admin(client, grp_id, message.from_user.id)
    if not is_admin:
        return await message.reply_text('<b>ʏᴏᴜ ᴍᴜsᴛ ʙᴇ ᴀɴ ᴀᴅᴍɪɴ ɪɴ ᴛʜɪꜱ ɢʀᴏᴜᴘ.</b>')
        
    chat_type = message.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await message.reply_text("<b>ᴜꜱᴇ ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ ɪɴ ᴀ ɢʀᴏᴜᴘ.</b>")
        
    try:
        tutorial = message.text.split(" ", 1)[1].strip()
        if not tutorial or not (tutorial.startswith("http://") or tutorial.startswith("https://")):
             raise ValueError("Invalid URL")
    except IndexError:
        return await message.reply_text("<b>⚠️ ᴄᴏᴍᴍᴀɴᴅ ɪɴᴄᴏᴍᴘʟᴇᴛᴇ!\n\nUsage:</b> `/set_tutorial https://your_tutorial_link.com`")    
    except ValueError:
        return await message.reply_text("<b>⚠️ ɪɴᴠᴀʟɪᴅ ꜰᴏʀᴍᴀᴛ! ᴘʟᴇᴀsᴇ ᴘʀᴏᴠɪᴅᴇ ᴀ ᴠᴀʟɪᴅ ᴜʀʟ (starting with http:// or https://).</b>")
        
    try:
        await save_group_settings(grp_id, 'tutorial', tutorial)
        await message.reply_text(f"✅ sᴜᴄᴄᴇssꜰᴜʟʟʏ ᴄʜᴀɴɢᴇᴅ ᴛᴜᴛᴏʀɪᴀʟ ʟɪɴᴋ ꜰᴏʀ <b>{title}</b> ᴛᴏ:\n\n{tutorial}", disable_web_page_preview=True)
    except Exception as e:
         logger.error(f"Error saving tutorial for group {grp_id}: {e}")
         await message.reply_text(f"<b>⚠️ ꜰᴀɪʟᴇᴅ ᴛᴏ sᴀᴠᴇ ᴛᴜᴛᴏʀɪᴀʟ ʟɪɴᴋ. ᴇʀʀᴏʀ: {e}</b>")

    
@Client.on_message(filters.command('set_shortner'))
async def set_shortner(c, m):
    grp_id = m.chat.id
    title = m.chat.title
    is_admin = await is_check_admin(c, grp_id, m.from_user.id)
    if not is_admin:
        return await m.reply_text('<b>ʏᴏᴜ ᴍᴜsᴛ ʙᴇ ᴀɴ ᴀᴅᴍɪɴ ɪɴ ᴛʜɪꜱ ɢʀᴏᴜᴘ.</b>')        
        
    if len(m.command) < 3:
        await m.reply("<b>⚠️ ɪɴᴄᴏᴍᴘʟᴇᴛᴇ ᴄᴏᴍᴍᴀɴᴅ!\n\nUsage:</b> `/set_shortner <website_domain> <api_key>`\n\nExample:\n`/set_shortner tnshort.net 06b24eb6...`")
        return        
        
    sts = await m.reply("<b>♻️ ᴠᴀʟɪᴅᴀᴛɪɴɢ sʜᴏʀᴛᴇɴᴇʀ...</b>")
    await asyncio.sleep(1) 
    
    chat_type = m.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        await sts.delete()
        return await m.reply_text("<b>ᴜꜱᴇ ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ ɪɴ ᴀ ɢʀᴏᴜᴘ.</b>")
        
    try:
        URL = m.command[1].strip()
        API = m.command[2].strip()
        
        if '.' not in URL or len(API) < 10: 
             raise ValueError("Invalid Domain or API Key format.")
             
        test_url = f'https://{URL}/api?api={API}&url=https://telegram.org' 
        resp = requests.get(test_url, timeout=10).json() 

        if resp.get('status') == 'success' and resp.get('shortenedUrl'):
            SHORT_LINK = resp['shortenedUrl']
            await save_group_settings(grp_id, 'shortner', URL)
            await save_group_settings(grp_id, 'api', API)
            await sts.edit_text(f"<b>✅ sᴜᴄᴄᴇssꜰᴜʟʟʏ sᴇᴛ 1sᴛ ᴠᴇʀɪꜰʏ sʜᴏʀᴛᴇɴᴇʀ!\n\nSite: `{URL}`\nAPI: `{API}`\nTest Link: {SHORT_LINK}</b>", disable_web_page_preview=True)
            
            user_id = m.from_user.id
            user_info = f"@{m.from_user.username}" if m.from_user.username else f"{m.from_user.mention}"
            try:
                 link = (await c.get_chat(m.chat.id)).invite_link or "N/A"
            except:
                 link = "N/A"
            grp_link = f"[{m.chat.title}]({link})"
            log_message = f"#Shortner1_Set\nUser: {user_info} (`{user_id}`)\nGroup: {grp_link} (`{grp_id}`)\nDomain: `{URL}`\nAPI: `{API}`"
            await c.send_message(LOG_API_CHANNEL, log_message, disable_web_page_preview=True)
        else:
            raise ValueError(f"API Test Failed. Response: {resp.get('message', 'No message')}")
            
    except requests.exceptions.RequestException as e:
         await sts.edit_text(f"<b>⚠️ ɴᴇᴛᴡᴏʀᴋ ᴇʀʀᴏʀ!\nCould not connect to `{URL}`. Check the domain and try again.\nError: `{e}`</b>")
    except ValueError as e:
         await sts.edit_text(f"<b>⚠️ ɪɴᴠᴀʟɪᴅ sʜᴏʀᴛᴇɴᴇʀ!\n{e}\nPlease check your website domain and API key.</b>")
    except Exception as e:
        logger.error(f"Error setting shortner 1 for group {grp_id}: {e}")
        await sts.edit_text(f"<b>⚠️ ᴀɴ ᴜɴᴇxᴘᴇᴄᴛᴇᴅ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ!\nError: `{e}`\n\nDefault shortener might be restored.</b>")
        await save_group_settings(grp_id, 'shortner', SHORTENER_WEBSITE)
        await save_group_settings(grp_id, 'api', SHORTENER_API)


@Client.on_message(filters.command('set_shortner_2'))
async def set_shortner_2(c, m):
    grp_id = m.chat.id
    title = m.chat.title
    is_admin = await is_check_admin(c, grp_id, m.from_user.id)
    if not is_admin:
        return await m.reply_text('<b>ʏᴏᴜ ᴍᴜsᴛ ʙᴇ ᴀɴ ᴀᴅᴍɪɴ ɪɴ ᴛʜɪꜱ ɢʀᴏᴜᴘ.</b>')
        
    if len(m.command) < 3:
        await m.reply("<b>⚠️ ɪɴᴄᴏᴍᴘʟᴇᴛᴇ ᴄᴏᴍᴍᴀɴᴅ!\n\nUsage:</b> `/set_shortner_2 <website_domain> <api_key>`\n\nExample:\n`/set_shortner_2 mdisk.link e7beb3c8...`")
        return
        
    sts = await m.reply("<b>♻️ ᴠᴀʟɪᴅᴀᴛɪɴɢ sʜᴏʀᴛᴇɴᴇʀ...</b>")
    await asyncio.sleep(1)
    
    chat_type = m.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        await sts.delete()
        return await m.reply_text("<b>ᴜꜱᴇ ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ ɪɴ ᴀ ɢʀᴏᴜᴘ.</b>")
        
    try:
        URL = m.command[1].strip()
        API = m.command[2].strip()
        
        if '.' not in URL or len(API) < 10: 
             raise ValueError("Invalid Domain or API Key format.")
             
        test_url = f'https://{URL}/api?api={API}&url=https://telegram.org'
        resp = requests.get(test_url, timeout=10).json()

        if resp.get('status') == 'success' and resp.get('shortenedUrl'):
            SHORT_LINK = resp['shortenedUrl']
            await save_group_settings(grp_id, 'shortner_two', URL)
            await save_group_settings(grp_id, 'api_two', API)
            await sts.edit_text(f"<b>✅ sᴜᴄᴄᴇssꜰᴜʟʟʏ sᴇᴛ 2ɴᴅ ᴠᴇʀɪꜰʏ sʜᴏʀᴛᴇɴᴇʀ!\n\nSite: `{URL}`\nAPI: `{API}`\nTest Link: {SHORT_LINK}</b>", disable_web_page_preview=True)
            
            user_id = m.from_user.id
            user_info = f"@{m.from_user.username}" if m.from_user.username else f"{m.from_user.mention}"
            try:
                 link = (await c.get_chat(m.chat.id)).invite_link or "N/A"
            except:
                 link = "N/A"
            grp_link = f"[{m.chat.title}]({link})"
            log_message = f"#Shortner2_Set\nUser: {user_info} (`{user_id}`)\nGroup: {grp_link} (`{grp_id}`)\nDomain: `{URL}`\nAPI: `{API}`"
            await c.send_message(LOG_API_CHANNEL, log_message, disable_web_page_preview=True)
        else:
            raise ValueError(f"API Test Failed. Response: {resp.get('message', 'No message')}")
            
    except requests.exceptions.RequestException as e:
         await sts.edit_text(f"<b>⚠️ ɴᴇᴛᴡᴏʀᴋ ᴇʀʀᴏʀ!\nCould not connect to `{URL}`. Check the domain and try again.\nError: `{e}`</b>")
    except ValueError as e:
         await sts.edit_text(f"<b>⚠️ ɪɴᴠᴀʟɪᴅ sʜᴏʀᴛᴇɴᴇʀ!\n{e}\nPlease check your website domain and API key.</b>")
    except Exception as e:
        logger.error(f"Error setting shortner 2 for group {grp_id}: {e}")
        await sts.edit_text(f"<b>⚠️ ᴀɴ ᴜɴᴇxᴘᴇᴄᴛᴇᴅ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ!\nError: `{e}`\n\nDefault shortener might be restored.</b>")
        await save_group_settings(grp_id, 'shortner_two', SHORTENER_WEBSITE2)
        await save_group_settings(grp_id, 'api_two', SHORTENER_API2)


@Client.on_message(filters.command('set_log_channel'))
async def set_log(client, message):
    grp_id = message.chat.id
    title = message.chat.title
    is_admin = await is_check_admin(client, grp_id, message.from_user.id)
    if not is_admin:
        return await message.reply_text('<b>ʏᴏᴜ ᴍᴜsᴛ ʙᴇ ᴀɴ ᴀᴅᴍɪɴ ɪɴ ᴛʜɪꜱ ɢʀᴏᴜᴘ.</b>')
        
    if len(message.command) < 2:
        await message.reply("<b>⚠️ ᴄᴏᴍᴍᴀɴᴅ ɪɴᴄᴏᴍᴘʟᴇᴛᴇ!\n\nUsage:</b> `/set_log_channel <channel_id>`\n\nExample:\n`/set_log_channel -100123456789`\n(Make sure the bot is an admin in the log channel!)")
        return
        
    sts = await message.reply("<b>♻️ ᴠᴇʀɪꜰʏɪɴɢ ᴄʜᴀɴɴᴇʟ...</b>")
    await asyncio.sleep(1)
    
    chat_type = message.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        await sts.delete()
        return await message.reply_text("<b>ᴜꜱᴇ ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ ɪɴ ᴀ ɢʀᴏᴜᴘ.</b>")
        
    try:
        log_channel_id = int(message.command[1].strip())
        if not str(log_channel_id).startswith("-100"):
             raise ValueError("Channel ID should typically start with -100.")
             
    except (IndexError, ValueError) as e:
        await sts.delete()
        return await message.reply_text(f"<b>⚠️ ɪɴᴠᴀʟɪᴅ ᴄʜᴀɴɴᴇʟ ɪᴅ!\n{e}\nPlease provide a correct channel ID (e.g., -10012345...).</b>")
        
    try:
        test_msg = await client.send_message(chat_id=log_channel_id, text="**Log Channel Test**\n\nThis message will be deleted shortly.")
        await asyncio.sleep(2)
        await test_msg.delete()
        
        await save_group_settings(grp_id, 'log', log_channel_id)
        await sts.edit_text(f"<b>✅ sᴜᴄᴄᴇssꜰᴜʟʟʏ sᴇᴛ ʟᴏɢ ᴄʜᴀɴɴᴇʟ ꜰᴏʀ <b>{title}</b> ᴛᴏ `{log_channel_id}`.</b>")
        
        user_id = message.from_user.id
        user_info = f"@{message.from_user.username}" if message.from_user.username else f"{message.from_user.mention}"
        try:
             link = (await client.get_chat(message.chat.id)).invite_link or "N/A"
        except:
             link = "N/A"
        grp_link = f"[{message.chat.title}]({link})"
        log_message = f"#LogChannel_Set\nUser: {user_info} (`{user_id}`)\nGroup: {grp_link} (`{grp_id}`)\nLog Channel: `{log_channel_id}`"
        await client.send_message(LOG_API_CHANNEL, log_message, disable_web_page_preview=True)  

    except ChatAdminRequired:
         await sts.edit_text("<b>⚠️ ʙᴏᴛ ɪs ɴᴏᴛ ᴀɴ ᴀᴅᴍɪɴ ɪɴ ᴛʜᴇ ᴘʀᴏᴠɪᴅᴇᴅ ʟᴏɢ ᴄʜᴀɴɴᴇʟ!</b> Make it admin and try again.")
    except Exception as e:
        logger.error(f"Error setting log channel {log_channel_id} for group {grp_id}: {e}")
        await sts.edit_text(f"<b>⚠️ ꜰᴀɪʟᴇᴅ ᴛᴏ sᴇᴛ ʟᴏɢ ᴄʜᴀɴɴᴇʟ.\nCould not verify access to channel ID `{log_channel_id}`.\nError: `{e}`</b>")


@Client.on_message(filters.command('details'))
async def all_settings(client, message):
    grp_id = message.chat.id
    title = message.chat.title
    is_admin = await is_check_admin(client, grp_id, message.from_user.id)
    if not is_admin:
        return await message.reply_text('<b>ʏᴏᴜ ᴍᴜsᴛ ʙᴇ ᴀɴ ᴀᴅᴍɪɴ ɪɴ ᴛʜɪꜱ ɢʀᴏᴜᴘ.</b>')
        
    chat_type = message.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await message.reply_text("<b>ᴜsᴇ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ɪɴ ᴀ ɢʀᴏᴜᴘ.</b>")
        
    try:
        settings = await get_settings(grp_id)
        if not settings:
             return await message.reply_text("<b>⚠️ ᴄᴏᴜʟᴅ ɴᴏᴛ ꜰᴇᴛᴄʜ sᴇᴛᴛɪɴɢs ғᴏʀ ᴛʜɪs ɢʀᴏᴜᴘ.</b>")
             
        text = f"""<b><u>⚙️ ᴄᴜʀʀᴇɴᴛ sᴇᴛᴛɪɴɢs ꜰᴏʀ:</u> {title}</b> (`{grp_id}`)

        <b><u>🔗 Shorteners:</u></b>
        1st Verify: `{settings.get("shortner", "N/A")}` | API: `{"********" + settings["api"][-5:] if settings.get("api") else "N/A"}`
        2nd Verify: `{settings.get("shortner_two", "N/A")}` | API: `{"********" + settings["api_two"][-5:] if settings.get("api_two") else "N/A"}`
        Verify Gap: `{get_readable_time(settings.get("verify_time", TWO_VERIFY_GAP))}`

        <b><u>📄 Logging & Info:</u></b>
        Log Channel ID: `{settings.get('log', 'Not Set')}`
        Tutorial Link: {settings.get('tutorial', 'Not Set')}

        <b><u>📝 Formatting:</u></b>
        IMDb Template: `{settings.get('template', 'Default').replace('{', '{{').replace('}', '}}')}` 
        File Caption: `{settings.get('caption', 'Default').replace('{', '{{').replace('}', '}}')}`
        """

        btn = [[
            InlineKeyboardButton("🔄 ʀᴇꜱᴇᴛ ᴀʟʟ ᴛᴏ ᴅᴇꜰᴀᴜʟᴛ", callback_data="reset_grp_data")
        ],[
            InlineKeyboardButton("⚙️ ᴄʜᴀɴɢᴇ ᴛᴏɢɢʟᴇ sᴇᴛᴛɪɴɢs", callback_data="settings"), 
            InlineKeyboardButton("❌ ᴄʟᴏsᴇ", callback_data="close_data")
        ]]
        reply_markup=InlineKeyboardMarkup(btn)
        
        await message.reply_text(text, reply_markup=reply_markup, disable_web_page_preview=True)
        
    except Exception as e:
         logger.error(f"Error fetching details for group {grp_id}: {e}")
         await message.reply_text(f"<b>⚠️ ᴀɴ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ ᴡʜɪʟᴇ ꜰᴇᴛᴄʜɪɴɢ ᴅᴇᴛᴀɪʟs: {e}</b>")


@Client.on_message(filters.command('set_time'))
async def set_time(client, message):
    userid = message.from_user.id if message.from_user else None
    if not userid:
        try:
             await message.delete() 
        except:
             pass
        return 
        
    chat_type = message.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await message.reply_text("<b>ᴜsᴇ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ɪɴ ᴀ ɢʀᴏᴜᴘ.</b>")       
        
    grp_id = message.chat.id
    title = message.chat.title
    is_admin = await is_check_admin(client, grp_id, message.from_user.id)
    if not is_admin:
        return await message.reply_text('<b>ʏᴏᴜ ᴍᴜsᴛ ʙᴇ ᴀɴ ᴀᴅᴍɪɴ ɪɴ ᴛʜɪꜱ ɢʀᴏᴜᴘ.</b>')
        
    try:
        time_str = message.text.split(" ", 1)[1].strip()
        if not time_str.isdigit():
             raise ValueError("Time must be an integer.")
        time_seconds = int(time_str)
        if time_seconds < 0:
             raise ValueError("Time cannot be negative.")
             
    except IndexError:
        return await message.reply_text("<b>⚠️ ᴄᴏᴍᴍᴀɴᴅ ɪɴᴄᴏᴍᴘʟᴇᴛᴇ!\n\nUsage:</b> `/set_time <seconds>`\n\nExample for 12 hours: `/set_time 43200`\n(This sets the gap between the 1st and 2nd verify shorteners)")   
    except ValueError as e:
         return await message.reply_text(f"<b>⚠️ ɪɴᴠᴀʟɪᴅ ᴛɪᴍᴇ!\n{e}\nPlease provide the time gap in seconds (e.g., 3600 for 1 hour).</b>")
         
    try:
        await save_group_settings(grp_id, 'verify_time', time_seconds)
        readable_time = get_readable_time(time_seconds)
        await message.reply_text(f"✅ sᴜᴄᴄᴇssꜰᴜʟʟʏ sᴇᴛ ᴠᴇʀɪꜰʏ ᴛɪᴍᴇ ɢᴀᴘ ꜰᴏʀ <b>{title}</b> ᴛᴏ: <b>{readable_time}</b> (`{time_seconds}` seconds).")
    except Exception as e:
         logger.error(f"Error setting verify_time for group {grp_id}: {e}")
         await message.reply_text(f"<b>⚠️ ꜰᴀɪʟᴇᴅ ᴛᴏ sᴇᴛ ᴛɪᴍᴇ ɢᴀᴘ. ᴇʀʀᴏʀ: {e}</b>")
