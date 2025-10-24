import os, requests
import logging
import random
import asyncio
import string
import pytz
from datetime import datetime
from Script import script
from pyrogram import Client, filters, enums
from pyrogram.errors import ChatAdminRequired, FloodWait, UserIsBlocked # Added UserIsBlocked for later use
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database.ia_filterdb import Media, get_file_details, get_bad_files, unpack_new_file_id
from database.users_chats_db import db
from info import (ADMINS, LOG_CHANNEL, USERNAME, VERIFY_IMG, IS_VERIFY, FILE_CAPTION,
                  AUTH_CHANNEL, SHORTENER_WEBSITE, SHORTENER_API, SHORTENER_WEBSITE2,
                  SHORTENER_API2, LOG_API_CHANNEL, TWO_VERIFY_GAP, QR_CODE,
                  DELETE_TIME, REFERRAL_TARGET, JOIN_REQUEST_FSUB,
                  AUTH_CHANNEL_2, JOIN_REQUEST_FSUB_2) # Added second channel flags
from utils import get_settings, save_group_settings, is_req_subscribed, get_size, get_shortlink, is_check_admin, get_status, temp, get_readable_time
from pyrogram.errors import ChatAdminRequired # Added ChatAdminRequired
import re
import json
import base64
import aiohttp # Added for shortener check

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@Client.on_message(filters.command("start") & filters.incoming)
async def start(client: Client, message):
    m = message
    user_id = m.from_user.id

    # --- Handle Verification Callback ---
    if len(m.command) == 2 and m.command[1].startswith('notcopy'):
        try:
            _, userid_str, verify_id, start_param = m.command[1].split("_", 3) # Get original start param
            user_id_from_link = int(userid_str)
        except ValueError:
            logger.warning(f"Invalid 'notcopy' format: {m.command[1]}")
            await message.reply("Invalid verification link format.")
            return

        grp_id = temp.CHAT.get(user_id_from_link, 0)
        if not grp_id:
             logger.warning(f"Group ID context not found for user {user_id_from_link} in 'notcopy' callback.")
             await message.reply("Could not find the original request context. Please try requesting the file again.")
             return

        settings = await get_settings(grp_id)
        verify_id_info = await db.get_verify_id_info(user_id_from_link, verify_id)

        if not verify_id_info:
             await message.reply("<b>Invalid verification link. It might have expired or is incorrect.</b>")
             return
        if verify_id_info.get("verified", False):
             # Determine file_id or batch_key from start_param
             file_or_batch_id = ""
             if start_param.startswith("file_"):
                  try: file_or_batch_id = start_param.split('_')[-1]
                  except: pass
             elif start_param.startswith("allfiles_"):
                  try: file_or_batch_id = start_param.split('_')[-1]
                  except: pass

             btn = [[InlineKeyboardButton("✅ Click Here To Get Content ✅", url=f"https://t.me/{temp.U_NAME}?start={start_param}")]]
             await m.reply_photo(photo=(VERIFY_IMG), caption="Link already used. Click below if you still need the content.", reply_markup=InlineKeyboardMarkup(btn))
             return

        ist_timezone = pytz.timezone('Asia/Kolkata')
        key = "second_time_verified" if await db.user_verified(user_id_from_link) else "last_verified"
        current_time = datetime.now(tz=ist_timezone)
        await db.update_notcopy_user(user_id_from_link, {key:current_time})
        await db.update_verify_id_info(user_id_from_link, verify_id, {"verified":True})
        num =  2 if key == "second_time_verified" else 1
        msg_text = script.SECOND_VERIFY_COMPLETE_TEXT if key == "second_time_verified" else script.VERIFY_COMPLETE_TEXT

        try:
             log_chat_id = settings.get('log', LOG_CHANNEL)
             await client.send_message(log_chat_id, script.VERIFIED_LOG_TEXT.format(
                  m.from_user.mention, user_id_from_link,
                  datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%d %B %Y %I:%M %p'), num
             ))
        except Exception as log_e:
             logger.error(f"Failed to send verification log: {log_e}")

        # Use the original start_param to reconstruct the correct link
        btn = [[
            InlineKeyboardButton("✅ Click Here To Get Content ✅", url=f"https://t.me/{temp.U_NAME}?start={start_param}"),
        ]]
        reply_markup=InlineKeyboardMarkup(btn)
        await m.reply_photo(
            photo=(VERIFY_IMG),
            caption=msg_text.format(message.from_user.mention, get_readable_time(settings.get('verify_time', TWO_VERIFY_GAP))),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
        return

    # --- Group Start Message ---
    if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        is_bot_admin = False
        try:
             member = await client.get_chat_member(message.chat.id, client.me.id)
             is_bot_admin = member.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]
        except Exception:
             pass # Bot might not be in chat anymore or other errors

        status = get_status()
        reply_text = f"<b>🔥 Yes {status}, I'm alive!</b>"
        if not is_bot_admin:
             reply_text += "\n\n⚠️ Promote me as admin for full functionality!"

        aks=await message.reply_text(reply_text)
        await asyncio.sleep(60)
        try: await aks.delete()
        except: pass
        try: await m.delete()
        except: pass

        if (str(message.chat.id)).startswith("-100") and not await db.get_chat(message.chat.id):
            total=await client.get_chat_members_count(message.chat.id)
            try:
                 group_link = await message.chat.export_invite_link()
            except ChatAdminRequired:
                 group_link = "N/A (Bot not admin)"
            user = message.from_user.mention if message.from_user else "Dear"
            try:
                 await client.send_message(LOG_CHANNEL, script.NEW_GROUP_TXT.format(
                      temp.B_LINK, message.chat.title, message.chat.id,
                      message.chat.username or 'None', group_link, total, user
                 ))
            except Exception as log_e:
                 logger.error(f"Failed to log new group: {log_e}")
            await db.add_chat(message.chat.id, message.chat.title)
        return

    # --- PM Start Message & New User Handling ---
    if not await db.is_user_exist(message.from_user.id):
        await db.add_user(message.from_user.id, message.from_user.first_name)
        try:
             await client.send_message(LOG_CHANNEL, script.NEW_USER_TXT.format(temp.B_LINK, message.from_user.id, message.from_user.mention))
        except Exception as log_e:
             logger.error(f"Failed to log new user: {log_e}")

    # --- Generic PM Start (No Deep Link) ---
    if len(message.command) == 1:
        buttons = [[
            InlineKeyboardButton('⇆ Add Me To Your Groups ⇆', url=f'http://t.me/{temp.U_NAME}?startgroup=start')
        ],[
            InlineKeyboardButton('⚙ Features', callback_data='features'),
            InlineKeyboardButton('💸 Premium', callback_data='buy_premium')
        ],[
            InlineKeyboardButton(script.REFERRAL_BUTTON_TEXT, callback_data='referral')
        ],[
            InlineKeyboardButton('🚫 Earn Money With Bot 🚫', callback_data='earn')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await message.reply_text(script.START_TXT.format(message.from_user.mention, get_status(), message.from_user.id),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
        return

    # --- Handling Deep Links ---
    data = message.command[1]

    # Handle simple deep links
    if data in ["subscribe", "error", "okay", "help"]:
        buttons = [[
            InlineKeyboardButton('⇆ Add Me To Your Groups ⇆', url=f'http://t.me/{temp.U_NAME}?startgroup=start')
        ],[
            InlineKeyboardButton('⚙ Features', callback_data='features'),
            InlineKeyboardButton('💸 Premium', callback_data='buy_premium')
        ],[
            InlineKeyboardButton(script.REFERRAL_BUTTON_TEXT, callback_data='referral')
        ],[
            InlineKeyboardButton('🚫 Earn Money With Bot 🚫', callback_data='earn')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await message.reply_text(
            text=script.START_TXT.format(message.from_user.mention, get_status(), message.from_user.id),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
        return

    # Handle premium deep link
    if data == "buy_premium":
        btn = [[
            InlineKeyboardButton('📸 Send Screenshot 📸', url=USERNAME)
        ],[
            InlineKeyboardButton('🗑 Close 🗑', callback_data='close_data')
        ]]
        await message.reply_photo(
            photo=(QR_CODE),
            caption=script.PREMIUM_TEXT.format(mention=message.from_user.mention),
            reply_markup=InlineKeyboardMarkup(btn)
        )
        return

    # --- File/Batch Request Deep Link ---
    pre, grp_id_str, file_id = "", "", ""
    is_batch = False
    batch_key = ""
    files_to_send = None # Initialize

    try:
        if data.startswith("allfiles_"):
            is_batch = True
            _, batch_key = data.split("_", 1)
            files_to_send = temp.FILES_ID.get(batch_key)
            if not files_to_send:
                await message.reply("Batch link expired or invalid.")
                return
            grp_id = temp.CHAT.get(user_id) # Get context from user who clicked verification
            if not grp_id:
                await message.reply("Could not determine group context. Please request again.")
                return
            grp_id_str = str(grp_id)

        elif data.startswith("file_"):
            pre, grp_id_str, file_id = data.split('_', 2)
            grp_id = int(grp_id_str)
        else:
             await message.reply("Invalid or unsupported link format.")
             return

    except Exception as e:
        logger.error(f"Error parsing deep link data '{data}': {e}")
        await message.reply('Invalid link format.')
        return

    # --- Get Group Settings ---
    try:
        grp_id = int(grp_id_str)
        settings = await get_settings(grp_id)
    except ValueError:
         await message.reply("Invalid group ID in link.")
         return
    except Exception as e:
         logger.error(f"Error getting settings for group {grp_id_str}: {e}")
         await message.reply("Could not load settings for this request.")
         return


    # --- 1. JOIN REQUEST CHECK (Channel 1) ---
    if (JOIN_REQUEST_FSUB and AUTH_CHANNEL and
        not await db.has_premium_access(user_id) and
        not await db.check_referral_access(user_id) and
        not await db.has_requested_join(user_id)):
        try:
            invite_link = await client.create_chat_invite_link(int(AUTH_CHANNEL), creates_join_request=True)
            btn = [
                [InlineKeyboardButton("➡️ Send Join Request (Channel 1)", url=invite_link.invite_link)],
                [InlineKeyboardButton("🔄 Try Again", url=f"https://t.me/{temp.U_NAME}?start={data}")]
            ]
            await message.reply_text(script.JOIN_REQUEST_TEXT, reply_markup=InlineKeyboardMarkup(btn))
            return
        except ChatAdminRequired:
            logger.error(f"Bot must be admin in AUTH_CHANNEL ({AUTH_CHANNEL})")
            await message.reply_text("❗ Config Error (CH1). Contact admin.")
            return
        except Exception as e:
            logger.error(f"Error creating join request link (CH1): {e}")
            await message.reply_text("❗ Error generating join link (CH1). Try again.")
            return

    # --- 2. JOIN REQUEST CHECK (Channel 2) ---
    if (JOIN_REQUEST_FSUB_2 and AUTH_CHANNEL_2 and
        not await db.has_premium_access(user_id) and
        not await db.check_referral_access(user_id) and
        not await db.has_requested_join_2(user_id)):
        try:
            invite_link_2 = await client.create_chat_invite_link(int(AUTH_CHANNEL_2), creates_join_request=True)
            btn_2 = [
                [InlineKeyboardButton("➡️ Send Join Request (Channel 2)", url=invite_link_2.invite_link)],
                [InlineKeyboardButton("🔄 Try Again", url=f"https://t.me/{temp.U_NAME}?start={data}")]
            ]
            await message.reply_text(script.JOIN_REQUEST_TEXT_2, reply_markup=InlineKeyboardMarkup(btn_2))
            return
        except ChatAdminRequired:
            logger.error(f"Bot must be admin in AUTH_CHANNEL_2 ({AUTH_CHANNEL_2})")
            await message.reply_text("❗ Config Error (CH2). Contact admin.")
            return
        except Exception as e:
            logger.error(f"Error creating join request link (CH2): {e}")
            await message.reply_text("❗ Error generating join link (CH2). Try again.")
            return

    # --- 3. VERIFICATION CHECK (Only if not premium/referral) ---
    if not await db.has_premium_access(user_id) and not await db.check_referral_access(user_id):
        user_verified = await db.is_user_verified(user_id)
        is_second_shortener = await db.use_second_shortener(user_id, settings.get('verify_time', TWO_VERIFY_GAP))

        if settings.get("is_verify", IS_VERIFY) and (not user_verified or is_second_shortener):
            # Use original 'data' param for callback context
            start_param_for_verify = data

            verify_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=7))
            await db.create_verify_id(user_id, verify_id)
            temp.CHAT[user_id] = grp_id # Store context
            verify_link = await get_shortlink(f"https://telegram.me/{temp.U_NAME}?start=notcopy_{user_id}_{verify_id}_{start_param_for_verify}", grp_id, is_second_shortener)
            buttons = [[
                InlineKeyboardButton(text="✅️ Verify ✅️", url=verify_link),
                InlineKeyboardButton(text="⁉️ How To Verify ⁉️", url=settings.get('tutorial', '#'))
            ],[
                InlineKeyboardButton("😁 Buy Subscription - Skip Verify 😁", callback_data='buy_premium')
            ]]
            reply_markup=InlineKeyboardMarkup(buttons)
            msg_text = script.SECOND_VERIFICATION_TEXT if is_second_shortener else script.VERIFICATION_TEXT
            await m.reply_text(
                text=msg_text.format(message.from_user.mention, get_status()),
                protect_content=False,
                reply_markup=reply_markup,
                parse_mode=enums.ParseMode.HTML
            )
            return

    # --- 4. SEND FILE(S) ---
    if is_batch:
         if not files_to_send: # Should have been caught earlier, but double check
              await message.reply("Batch files not found.")
              return
         total_files = len(files_to_send)
         sent_count = 0
         failed_count = 0
         prog = await message.reply(f"🚀 Sending batch... (0/{total_files})")
         for file_obj in files_to_send:
              CAPTION = settings.get('caption', script.FILE_CAPTION)
              f_caption = CAPTION.format(
                   file_name = file_obj.file_name,
                   file_size = get_size(file_obj.file_size),
                   file_caption= file_obj.caption if file_obj.caption else ""
              )
              f_id = file_obj.file_id
              btn = [[ InlineKeyboardButton("✛ Stream/Download ✛", callback_data=f'stream#{f_id}') ]]
              try:
                   await client.send_cached_media(
                       chat_id=user_id, file_id=f_id, caption=f_caption,
                       protect_content=settings.get('file_secure', False),
                       reply_markup=InlineKeyboardMarkup(btn)
                   )
                   sent_count += 1
                   await asyncio.sleep(1.5) # Slightly longer delay for batches
                   if sent_count % 10 == 0:
                        try: await prog.edit_text(f"🚀 Sending batch... ({sent_count}/{total_files})")
                        except: pass
              except FloodWait as fw:
                   logger.warning(f"FloodWait sending batch file: sleeping for {fw.value}s")
                   await asyncio.sleep(fw.value + 5)
                   try: # Retry after sleep
                        await client.send_cached_media(chat_id=user_id, file_id=f_id, caption=f_caption, protect_content=settings.get('file_secure', False), reply_markup=InlineKeyboardMarkup(btn))
                        sent_count += 1
                   except Exception as retry_e:
                        logger.error(f"Failed retry sending file {f_id} in batch to {user_id}: {retry_e}")
                        failed_count += 1
              except Exception as send_error:
                   logger.error(f"Failed sending file {f_id} in batch to {user_id}: {send_error}")
                   failed_count += 1

         try: await prog.delete()
         except: pass
         await message.reply(f"✅ Batch complete!\nSent: {sent_count}/{total_files}\nFailed: {failed_count}")
         if batch_key in temp.FILES_ID: del temp.FILES_ID[batch_key] # Clean up temp storage
         return

    else: # Send single file
        files_ = await get_file_details(file_id)
        if not files_:
             return await message.reply('<b>⚠️ File not found. It might have been deleted.</b>')

        files = files_[0]
        CAPTION = settings.get('caption', script.FILE_CAPTION)
        f_caption = CAPTION.format(
             file_name = files.file_name,
             file_size = get_size(files.file_size),
             file_caption=files.caption if files.caption else ""
        )
        btn = [[ InlineKeyboardButton("✛ Stream/Download ✛", callback_data=f'stream#{file_id}') ]]
        try:
             await client.send_cached_media(
                 chat_id=message.from_user.id,
                 file_id=file_id,
                 caption=f_caption,
                 protect_content=settings.get('file_secure', False),
                 reply_markup=InlineKeyboardMarkup(btn)
             )
        except FloodWait as fw:
             logger.warning(f"FloodWait sending single file: sleeping for {fw.value}s")
             await asyncio.sleep(fw.value + 2)
             # Retry sending after sleep
             try:
                  await client.send_cached_media(
                      chat_id=message.from_user.id, file_id=file_id, caption=f_caption,
                      protect_content=settings.get('file_secure', False), reply_markup=InlineKeyboardMarkup(btn)
                  )
             except Exception as retry_e:
                  logger.error(f"Failed retry sending file {file_id} to {user_id}: {retry_e}")
                  await message.reply_text("<b>❌ Sorry, couldn't send the file after waiting. Please try again.</b>")
        except Exception as send_error:
             logger.error(f"Error sending file {file_id} to {user_id}: {send_error}")
             await message.reply_text("<b>❌ Sorry, couldn't send the file. Please try again later.</b>")


@Client.on_message(filters.command('delete') & filters.user(ADMINS))
async def delete(bot, message):
    reply = message.reply_to_message
    if not reply:
        await message.reply('Reply to the file message you want to delete.')
        return

    msg = await message.reply("⏳ Processing...", quote=True)

    media = getattr(reply, reply.media.value, None) if reply.media else None
    if not media:
         # Handle potential service messages like 'pinned message'
         if reply.service:
              await msg.edit('Cannot delete service messages.')
         else:
              await msg.edit('<b>Reply to a message containing the file to delete.</b>')
         return

    try:
        file_id_to_delete, _ = unpack_new_file_id(media.file_id)
        result = await Media.collection.delete_one({'_id': file_id_to_delete})

        if result.deleted_count:
            await msg.edit('<b>✅️ File successfully deleted from database!</b>')
        else:
            await msg.edit('<b>⚠️ File not found in database using file_id.</b>')
    except Exception as e:
         logger.error(f"Error during file deletion: {e}")
         await msg.edit(f"<b>❌ Error deleting file: {e}</b>")


@Client.on_message(filters.command('deleteall') & filters.user(ADMINS))
async def delete_all_index(bot, message):
    if str(message.from_user.id) not in ADMINS:
        return await message.reply('Owners only.')

    files_count = await Media.count_documents()
    if int(files_count) == 0:
        return await message.reply_text('Database is already empty!')

    btn = [[ InlineKeyboardButton(text="YES, Delete All!", callback_data="all_files_delete") ],
           [ InlineKeyboardButton(text="CANCEL", callback_data="close_data") ]]
    await message.reply_text(
        f'<b>⚠️ Delete ALL {files_count} files? Irreversible!\nAre you sure?</b>',
        reply_markup=InlineKeyboardMarkup(btn)
    )

@Client.on_message(filters.command('settings'))
async def settings_cmd(client, message):
    user_id = message.from_user.id if message.from_user else None
    if not user_id:
        return await message.reply("<b>💔 Anonymous admins cannot use this.</b>")

    chat_type = message.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await message.reply_text("<code>Use in group.</code>")

    grp_id = message.chat.id
    if not await is_check_admin(client, grp_id, message.from_user.id):
        return await message.reply_text('<b>Group admins only.</b>')

    settings = await get_settings(grp_id)
    title = message.chat.title

    buttons = [[
        InlineKeyboardButton('Auto Filter', callback_data=f'setgs#auto_filter#{settings.get("auto_filter", True)}#{grp_id}'),
        InlineKeyboardButton('On ✔️' if settings.get("auto_filter", True) else 'Off ✗', callback_data=f'setgs#auto_filter#{settings.get("auto_filter", True)}#{grp_id}')
    ],[
        InlineKeyboardButton('File Secure', callback_data=f'setgs#file_secure#{settings.get("file_secure", False)}#{grp_id}'),
        InlineKeyboardButton('On ✔️' if settings.get("file_secure", False) else 'Off ✗', callback_data=f'setgs#file_secure#{settings.get("file_secure", False)}#{grp_id}')
    ],[
        InlineKeyboardButton('IMDB', callback_data=f'setgs#imdb#{settings.get("imdb", True)}#{grp_id}'),
        InlineKeyboardButton('On ✔️' if settings.get("imdb", True) else 'Off ✗', callback_data=f'setgs#imdb#{settings.get("imdb", True)}#{grp_id}')
    ],[
        InlineKeyboardButton('Spell Check', callback_data=f'setgs#spell_check#{settings.get("spell_check", True)}#{grp_id}'),
        InlineKeyboardButton('On ✔️' if settings.get("spell_check", True) else 'Off ✗', callback_data=f'setgs#spell_check#{settings.get("spell_check", True)}#{grp_id}')
    ],[
        InlineKeyboardButton('Auto Delete', callback_data=f'setgs#auto_delete#{settings.get("auto_delete", False)}#{grp_id}'),
        InlineKeyboardButton(f'{get_readable_time(DELETE_TIME)}' if settings.get("auto_delete", False) else 'Off ✗', callback_data=f'setgs#auto_delete#{settings.get("auto_delete", False)}#{grp_id}')
    ],[
        InlineKeyboardButton('Result Mode', callback_data=f'setgs#link#{settings.get("link", True)}#{str(grp_id)}'),
        InlineKeyboardButton('Link' if settings.get("link", True) else 'Button', callback_data=f'setgs#link#{settings.get("link", True)}#{str(grp_id)}')
    ],[
        InlineKeyboardButton('Verify', callback_data=f'setgs#is_verify#{settings.get("is_verify", True)}#{grp_id}'),
        InlineKeyboardButton('On ✔️' if settings.get("is_verify", True) else 'Off ✗', callback_data=f'setgs#is_verify#{settings.get("is_verify", True)}#{grp_id}')
    ],[
        InlineKeyboardButton('☕️ Close ☕️', callback_data='close_data')
    ]]
    await message.reply_text(
        text=f"⚙️ Settings for <b>'{title}'</b>",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode=enums.ParseMode.HTML
    )


@Client.on_message(filters.command('set_template') & filters.group)
async def save_template(client, message):
    grp_id = message.chat.id
    title = message.chat.title
    if not await is_check_admin(client, grp_id, message.from_user.id):
        return await message.reply_text('<b>Group admins only.</b>')
    try:
        template = message.text.split(" ", 1)[1]
    except IndexError:
        return await message.reply_text("<b>Usage: /set_template {template}</b>\nKeywords: {title}, {year}, {rating}, etc.")
    await save_group_settings(grp_id, 'template', template)
    await message.reply_text(f"✅ IMDB template updated for {title}.", disable_web_page_preview=True)

@Client.on_message(filters.command("send") & filters.user(ADMINS))
async def send_msg(bot, message):
    if not message.reply_to_message:
        return await message.reply_text("<b>Reply to message. Usage: /send id1 [id2...]</b>")

    target_ids_str = message.text.split(" ")[1:]
    if not target_ids_str: return await message.reply_text("<b>Provide user IDs.</b>")

    target_ids = []
    invalid_ids = []
    for uid_str in target_ids_str:
        try: target_ids.append(int(uid_str.strip()))
        except ValueError: invalid_ids.append(uid_str)

    if invalid_ids:
        await message.reply_text(f"⚠️ Invalid IDs skipped: `{', '.join(invalid_ids)}`")
    if not target_ids: return await message.reply_text("<b>No valid IDs provided.</b>")

    out = "Sending Report:\n\n"
    success_count = 0
    fail_count = 0
    start_time = time.time()
    status_msg = await message.reply_text(f"🚀 Sending to {len(target_ids)} users...")

    for i, target_id in enumerate(target_ids):
        try:
            user = await bot.get_users(target_id)
            await message.reply_to_message.copy(int(user.id))
            out += f"✅ {user.mention} (`{user.id}`)\n"
            success_count += 1
        except UserIsBlocked: out += f"❌ Blocked: `{target_id}`\n"; fail_count += 1
        except Exception as e: out += f"❌ Failed `{target_id}`: {e}\n"; fail_count += 1
        await asyncio.sleep(1.2) # Slightly longer delay

        if (i + 1) % 15 == 0: # Update every 15 users
            try: await status_msg.edit_text(f"🚀 Sending... {i+1}/{len(target_ids)}\n✅ Success: {success_count} | ❌ Failed: {fail_count}")
            except: pass

    time_taken = get_readable_time(time.time() - start_time)
    await status_msg.delete()
    final_report = f"<b><u>✉️ Send Report</u></b>\n⏱️ Time: {time_taken}\n\nTotal: `{len(target_ids)}`\n✅ Success: `{success_count}`\n❌ Failed: `{fail_count}`\n\n" + out
    try: await message.reply_text(final_report)
    except MessageTooLong:
        with open("send_report.txt", "w") as f: f.write(re.sub('<.*?>', '', final_report)) # Strip HTML for txt
        await message.reply_document("send_report.txt", caption=f"Send Report\n⏱️ {time_taken} | ✅ {success_count} | ❌ {fail_count}")
        os.remove("send_report.txt")


@Client.on_message(filters.regex(r"^#request\s+.+") & filters.group) # Ensure text after tag
async def send_request(bot, message):
    if not REQUEST_CHANNEL: return await message.reply("Request feature disabled.")

    request = message.text.split("#request", 1)[1].strip()
    if len(request) < 3: # Basic length check
         return await message.reply_text("<b>‼️ Request too short. Example: `#request Movie Name (Year)`</b>")

    buttons = [[ InlineKeyboardButton('👀 View Context', url=f"{message.link}") ],
               [ InlineKeyboardButton('⚙ Show Options', callback_data=f'show_options#{message.from_user.id}#{message.id}') ]]
    try:
        sent_request = await bot.send_message(
            REQUEST_CHANNEL,
            script.REQUEST_TXT.format(message.from_user.mention, message.from_user.id, request),
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        btn = [[ InlineKeyboardButton('✨ View Status ✨', url=f"{sent_request.link}") ]]
        await message.reply_text("<b>✅ Request submitted! Wait for admin processing.</b>", reply_markup=InlineKeyboardMarkup(btn))
    except Exception as e:
        logger.error(f"Failed sending request to channel {REQUEST_CHANNEL}: {e}")
        await message.reply_text("<b>❌ Could not submit request. Contact support.</b>")


@Client.on_message(filters.command("search") & filters.user(ADMINS) & filters.private)
async def search_files_cmd(bot, message):
    try: keyword = message.text.split(" ", 1)[1]
    except IndexError: return await message.reply_text("<b>Usage: /search keyword</b>")

    files, total = await get_bad_files(keyword)
    if total == 0: return await message.reply_text('<i>No files found.</i>')

    file_list_text = f"🔍 Files for '{keyword}' ({total} total):\n\n"
    for index, item in enumerate(files):
        file_list_text += f"{index + 1}. `{item.file_name}`\n"

    try: await message.reply_text(file_list_text)
    except MessageTooLong:
        with open("search_results.txt", "w") as file:
            file_data_txt = f"Files for '{keyword}' ({total}):\n\n"
            for i, item in enumerate(files): file_data_txt += f"{i + 1}. {item.file_name} (ID: {item.file_id})\n"
            file.write(file_data_txt)
        await message.reply_document("search_results.txt", caption=f"<b>♻️ Found {total} files. List attached.</b>")
        os.remove("search_results.txt")


@Client.on_message(filters.command("deletefiles") & filters.user(ADMINS) & filters.private)
async def deletemultiplefiles(bot, message):
    try: keyword = message.text.split(" ", 1)[1]
    except IndexError: return await message.reply_text("<b>Usage: /deletefiles keyword</b>")

    files, total = await get_bad_files(keyword)
    if total == 0: return await message.reply_text('<i>No files found to delete.</i>')

    btn = [[ InlineKeyboardButton("YES, Delete Them! ✅", callback_data=f"killfilesak#{keyword}") ],
           [ InlineKeyboardButton("CANCEL 😢", callback_data="close_data") ]]
    await message.reply_text(f"<b>Found {total} files for '{keyword}'.\n\n⚠️ Delete ALL? Irreversible!</b>", reply_markup=InlineKeyboardMarkup(btn))


@Client.on_message(filters.command("del_file") & filters.user(ADMINS) & filters.private)
async def delete_specific_files(bot, message):
    try:
        filenames_to_delete = [name.strip() for name in message.text.split(" ", 1)[1].split(",") if name.strip()]
        if not filenames_to_delete: raise IndexError
    except IndexError: return await message.reply_text("<b>Usage: /del_file name1[,name2,...]</b>")

    deleted_count = 0
    not_found = []
    errors = []
    status_msg = await message.reply(f"Processing {len(filenames_to_delete)} filenames...")

    for filename in filenames_to_delete:
        try:
            result = await Media.collection.delete_many({'file_name': filename})
            if result.deleted_count > 0: deleted_count += result.deleted_count
            else: not_found.append(filename)
        except Exception as e: logger.error(f"Error deleting '{filename}': {e}"); errors.append(filename)

    await status_msg.delete()
    reply = ""
    if deleted_count > 0: reply += f'<b>✅ Deleted {deleted_count} entries.</b>\n'
    if not_found: reply += f'<b>⚠️ Not Found:</b> <code>{", ".join(not_found)}</code>\n'
    if errors: reply += f'<b>❌ Errors:</b> <code>{", ".join(errors)}</code>\n'
    await message.reply_text(reply if reply else "No action taken.")


@Client.on_message(filters.command('set_caption') & filters.group)
async def save_caption(client, message):
    grp_id = message.chat.id
    title = message.chat.title
    if not await is_check_admin(client, grp_id, message.from_user.id): return await message.reply_text('<b>Group admins only.</b>')
    try: caption = message.text.split(" ", 1)[1]
    except IndexError: return await message.reply_text("<b>Usage: /set_caption {caption}</b>\nKeywords: `{file_name}`, `{file_size}`, `{file_caption}`")
    await save_group_settings(grp_id, 'caption', caption)
    await message.reply_text(f"✅ Caption updated for {title}.", disable_web_page_preview=True)

@Client.on_message(filters.command('set_tutorial') & filters.group)
async def save_tutorial(client, message):
    grp_id = message.chat.id
    title = message.chat.title
    if not await is_check_admin(client, grp_id, message.from_user.id): return await message.reply_text('<b>Group admins only.</b>')
    try:
        tutorial = message.text.split(" ", 1)[1]
        if not tutorial.startswith("http"): raise ValueError("Invalid URL")
    except IndexError: return await message.reply_text("<b>Usage: /set_tutorial https://link.com</b>")
    except ValueError: return await message.reply_text("<b>Invalid URL. Must start with http/https.</b>")
    await save_group_settings(grp_id, 'tutorial', tutorial)
    await message.reply_text(f"<b>✅ Tutorial link updated for {title}.</b>", disable_web_page_preview=True)

@Client.on_message(filters.command('set_shortner') & filters.group)
async def set_shortner(c, m):
    grp_id = m.chat.id
    title = m.chat.title
    if not await is_check_admin(c, grp_id, m.from_user.id): return await m.reply_text('<b>Group admins only.</b>')
    if len(m.command) != 3: return await m.reply("<b>Usage: /set_shortner yoursite.com api_key</b>")

    sts = await m.reply("<b>♻️ Checking API...</b>")
    URL = m.command[1].strip().rstrip('/')
    API = m.command[2].strip()

    if '.' not in URL or '/' in URL.split('//', 1)[-1]: return await sts.edit("<b>⚠️ Invalid URL (domain only).</b>")

    test_url = f"https://{URL}/api?api={API}&url=https://telegram.dog"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(test_url, timeout=10) as resp: # Added timeout
                if resp.status != 200: raise Exception(f"Status: {resp.status}")
                data = await resp.json()
                if data.get('status') == 'success' and data.get('shortenedUrl'):
                    SHORT_LINK = data['shortenedUrl']
                    await save_group_settings(grp_id, 'shortner', URL)
                    await save_group_settings(grp_id, 'api', API)
                    await sts.edit(f"<b><u>✅ 1st Shortener Set!</u>\nSite: `{URL}` | API: `{API}`\nDemo: {SHORT_LINK}</b>", disable_web_page_preview=True)
                    try: # Log
                        user_info = f"@{m.from_user.username}" if m.from_user.username else m.from_user.mention
                        link = await c.export_chat_invite_link(m.chat.id)
                        grp_link = f"[{title}]({link})" if link else title
                        log = f"#Shortner1_Set\nUser: {user_info}(`{m.from_user.id}`)\nGrp: {grp_link}(`{grp_id}`)\nDomain: `{URL}`"
                        await c.send_message(LOG_API_CHANNEL, log, disable_web_page_preview=True)
                    except Exception as log_e: logger.error(f"Short1 log error: {log_e}")
                else:
                    error = data.get('message', 'Unknown API Error')
                    await sts.edit(f"<b><u>❌ API Check Failed!</u>\nError: `{error}`\nDefault restored.</b>")
                    await save_group_settings(grp_id, 'shortner', SHORTENER_WEBSITE)
                    await save_group_settings(grp_id, 'api', SHORTENER_API)
    except asyncio.TimeoutError:
         await sts.edit(f"<b><u>❌ API Check Timed Out!</u>\nSite: `{URL}`\nDefault restored. Check if site is up.</b>")
         await save_group_settings(grp_id, 'shortner', SHORTENER_WEBSITE)
         await save_group_settings(grp_id, 'api', SHORTENER_API)
    except Exception as e:
        logger.error(f"Set shortener 1 error: {e}")
        await sts.edit(f"<b><u>❌ Error!</u>\n`{e}`\nDefault restored. Contact support.</b>")
        await save_group_settings(grp_id, 'shortner', SHORTENER_WEBSITE)
        await save_group_settings(grp_id, 'api', SHORTENER_API)


@Client.on_message(filters.command('set_shortner_2') & filters.group)
async def set_shortner_2(c, m):
    grp_id = m.chat.id
    title = m.chat.title
    if not await is_check_admin(c, grp_id, m.from_user.id): return await m.reply_text('<b>Group admins only.</b>')
    if len(m.command) != 3: return await m.reply("<b>Usage: /set_shortner_2 yoursite2.com api_key2</b>")

    sts = await m.reply("<b>♻️ Checking API...</b>")
    URL = m.command[1].strip().rstrip('/')
    API = m.command[2].strip()

    if '.' not in URL or '/' in URL.split('//', 1)[-1]: return await sts.edit("<b>⚠️ Invalid URL (domain only).</b>")

    test_url = f"https://{URL}/api?api={API}&url=https://telegram.dog"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(test_url, timeout=10) as resp:
                if resp.status != 200: raise Exception(f"Status: {resp.status}")
                data = await resp.json()
                if data.get('status') == 'success' and data.get('shortenedUrl'):
                    SHORT_LINK = data['shortenedUrl']
                    await save_group_settings(grp_id, 'shortner_two', URL)
                    await save_group_settings(grp_id, 'api_two', API)
                    await sts.edit(f"<b><u>✅ 2nd Shortener Set!</u>\nSite: `{URL}` | API: `{API}`\nDemo: {SHORT_LINK}</b>", disable_web_page_preview=True)
                    try: # Log
                        user_info = f"@{m.from_user.username}" if m.from_user.username else m.from_user.mention
                        link = await c.export_chat_invite_link(m.chat.id)
                        grp_link = f"[{title}]({link})" if link else title
                        log = f"#Shortner2_Set\nUser: {user_info}(`{m.from_user.id}`)\nGrp: {grp_link}(`{grp_id}`)\nDomain: `{URL}`"
                        await c.send_message(LOG_API_CHANNEL, log, disable_web_page_preview=True)
                    except Exception as log_e: logger.error(f"Short2 log error: {log_e}")
                else:
                    error = data.get('message', 'Unknown API Error')
                    await sts.edit(f"<b><u>❌ API Check Failed!</u>\nError: `{error}`\nDefault restored.</b>")
                    await save_group_settings(grp_id, 'shortner_two', SHORTENER_WEBSITE2)
                    await save_group_settings(grp_id, 'api_two', SHORTENER_API2)
    except asyncio.TimeoutError:
         await sts.edit(f"<b><u>❌ API Check Timed Out!</u>\nSite: `{URL}`\nDefault restored.</b>")
         await save_group_settings(grp_id, 'shortner_two', SHORTENER_WEBSITE2)
         await save_group_settings(grp_id, 'api_two', SHORTENER_API2)
    except Exception as e:
        logger.error(f"Set shortener 2 error: {e}")
        await sts.edit(f"<b><u>❌ Error!</u>\n`{e}`\nDefault restored.</b>")
        await save_group_settings(grp_id, 'shortner_two', SHORTENER_WEBSITE2)
        await save_group_settings(grp_id, 'api_two', SHORTENER_API2)


@Client.on_message(filters.command('set_log_channel') & filters.group)
async def set_log(client, message):
    grp_id = message.chat.id
    title = message.chat.title
    if not await is_check_admin(client, grp_id, message.from_user.id): return await message.reply_text('<b>Group admins only.</b>')
    if len(message.command) != 2: return await message.reply("<b>Usage: /set_log_channel -100xxxxxxxxxx</b>")

    try:
        log_channel_id = int(message.command[1])
        if not str(log_channel_id).startswith("-100"): raise ValueError("ID format")
    except ValueError: return await message.reply_text('<b>Invalid ID. Must be integer starting -100.</b>')

    sts = await message.reply("<b>♻️ Checking channel access...</b>")
    try:
       test_msg = await client.send_message(log_channel_id, "<b>Testing log access...</b>")
       await asyncio.sleep(1)
       await test_msg.delete()
    except Exception as e: return await sts.edit(f'<b>❌ Error accessing `{log_channel_id}`.\nBot admin there?\nError: `{e}`</b>')

    await save_group_settings(grp_id, 'log', log_channel_id)
    await sts.edit(f"<b>✅ Log Channel set for {title} to `{log_channel_id}`.</b>")
    try: # Log
        user_info = f"@{message.from_user.username}" if message.from_user.username else message.from_user.mention
        link = await client.export_chat_invite_link(message.chat.id)
        grp_link = f"[{title}]({link})" if link else title
        log = f"#LogChannel_Set\nUser: {user_info}(`{message.from_user.id}`)\nGrp: {grp_link}(`{grp_id}`)\nLog CH: `{log_channel_id}`"
        await client.send_message(LOG_API_CHANNEL, log, disable_web_page_preview=True)
    except Exception as log_e: logger.error(f"Log channel set log error: {log_e}")

@Client.on_message(filters.command('details') & filters.group)
async def all_settings(client, message):
    grp_id = message.chat.id
    title = message.chat.title
    if not await is_check_admin(client, grp_id, message.from_user.id): return await message.reply_text('<b>Group admins only.</b>')

    settings = await get_settings(grp_id)
    text = f"""<b><u>⚙️ Settings For:</u> {title}</b> ({grp_id})

<b>Shorteners:</b>
1st: <code>{settings.get('shortner', 'N/A')}</code> | <code>{settings.get('api', 'N/A')}</code>
2nd: <code>{settings.get('shortner_two', 'N/A')}</code> | <code>{settings.get('api_two', 'N/A')}</code>
2nd Verify Gap: {get_readable_time(settings.get('verify_time', TWO_VERIFY_GAP))}

<b>Channels & Links:</b>
Log CH ID: <code>{settings.get('log', 'N/A')}</code>
Tutorial Link: {settings.get('tutorial', 'N/A')}

<b>Formatting:</b>
IMDB Template: Yes (use /get_template to view)
File Caption: Yes (use /get_caption to view)
"""
    btn = [[ InlineKeyboardButton("🔄 Reset All", callback_data="reset_grp_data") ],
           [ InlineKeyboardButton("⚙ Modify", callback_data="open_settings_panel") ],
           [ InlineKeyboardButton("🗑 Close", callback_data="close_data") ]]
    await message.reply_text(text, reply_markup=InlineKeyboardMarkup(btn), disable_web_page_preview=True)

# Add commands to view current template/caption
@Client.on_message(filters.command(['get_template', 'get_caption']) & filters.group)
async def get_format_cmd(client, message):
    grp_id = message.chat.id
    if not await is_check_admin(client, grp_id, message.from_user.id): return await message.reply_text('<b>Group admins only.</b>')
    
    settings = await get_settings(grp_id)
    cmd = message.command[0]
    key = 'template' if cmd == 'get_template' else 'caption'
    current_value = settings.get(key, 'Not Set')
    
    await message.reply_text(f"<b>Current {key.title()}:</b>\n\n<code>{current_value}</code>")


@Client.on_message(filters.command('set_time') & filters.group)
async def set_time(client, message):
    if not await is_check_admin(client, message.chat.id, message.from_user.id): return await message.reply_text('<b>Group admins only.</b>')
    try:
        time_str = message.text.split(" ", 1)[1]
        time_seconds = await get_seconds(time_str)
        if time_seconds <= 0: raise ValueError("Time must be positive")
    except IndexError: return await message.reply_text("<b>Usage: /set_time [duration]</b> (e.g., `/set_time 10min`)")
    except ValueError: return await message.reply_text("<b>Invalid format! Use num + unit (min/hour/day).</b>")

    await save_group_settings(message.chat.id, 'verify_time', time_seconds)
    await message.reply_text(f"✅ 2nd verify gap set for {message.chat.title} to <b>{get_readable_time(time_seconds)}</b>.")


@Client.on_callback_query(filters.regex('^open_settings_panel'))
async def open_settings_panel_callback(client, query):
     if not await is_check_admin(client, query.message.chat.id, query.from_user.id):
          return await query.answer("Only admins.", show_alert=True)
     await query.answer("Opening settings panel...")
     # Create a dummy message object to pass to settings_cmd
     dummy_message = query.message
     dummy_message.from_user = query.from_user # Ensure from_user is set correctly
     await settings_cmd(client, dummy_message)
