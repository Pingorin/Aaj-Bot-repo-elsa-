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
                  DELETE_TIME, REFERRAL_TARGET, JOIN_REQUEST_FSUB) # Added JOIN_REQUEST_FSUB
from utils import get_settings, save_group_settings, is_req_subscribed, get_size, get_shortlink, is_check_admin, get_status, temp, get_readable_time
from pyrogram.errors import ChatAdminRequired # Added ChatAdminRequired
import re
import json
import base64

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@Client.on_message(filters.command("start") & filters.incoming)
async def start(client: Client, message):
    m = message
    user_id = m.from_user.id

    # --- Handle Referral Link (REMOVED as per group join referral logic) ---

    # --- Handle Verification Callback ---
    if len(m.command) == 2 and m.command[1].startswith('notcopy'):
        _, userid, verify_id, file_id = m.command[1].split("_", 3)
        user_id_from_link = int(userid) # Renamed to avoid confusion
        grp_id = temp.CHAT.get(user_id_from_link, 0) # Use ID from link to get context
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
             await message.reply("<b>This verification link has already been used.</b>")
             # Optionally send the file link again if needed
             btn = [[InlineKeyboardButton("✅ Click Here To Get File ✅", url=f"https://t.me/{temp.U_NAME}?start=file_{grp_id}_{file_id}")]]
             await m.reply_photo(photo=(VERIFY_IMG), caption="Link already used. Click below if you still need the file.", reply_markup=InlineKeyboardMarkup(btn))
             return

        ist_timezone = pytz.timezone('Asia/Kolkata')
        key = "second_time_verified" if await db.user_verified(user_id_from_link) else "last_verified" # Check 2nd verification status
        current_time = datetime.now(tz=ist_timezone)
        result = await db.update_notcopy_user(user_id_from_link, {key:current_time})
        await db.update_verify_id_info(user_id_from_link, verify_id, {"verified":True})
        num =  2 if key == "second_time_verified" else 1
        msg_text = script.SECOND_VERIFY_COMPLETE_TEXT if key == "second_time_verified" else script.VERIFY_COMPLETE_TEXT

        # Log verification
        try:
             log_chat_id = settings.get('log', LOG_CHANNEL) # Use group specific or default log
             await client.send_message(log_chat_id, script.VERIFIED_LOG_TEXT.format(
                  m.from_user.mention, user_id_from_link,
                  datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%d %B %Y %I:%M %p'), num
             ))
        except Exception as log_e:
             logger.error(f"Failed to send verification log: {log_e}")

        btn = [[
            InlineKeyboardButton("✅ Click Here To Get File ✅", url=f"https://t.me/{temp.U_NAME}?start=file_{grp_id}_{file_id}"),
        ]]
        reply_markup=InlineKeyboardMarkup(btn)
        await m.reply_photo(
            photo=(VERIFY_IMG),
            caption=msg_text.format(message.from_user.mention, get_readable_time(settings.get('verify_time', TWO_VERIFY_GAP))), # Use setting
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
        return

    # --- Group Start Message ---
    if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        is_bot_admin = await is_check_admin(client, message.chat.id, client.me.id) # Check if bot is admin
        status = get_status()
        reply_text = f"<b>🔥 Yes {status}, I'm alive!</b>"
        if not is_bot_admin:
             reply_text += "\n\n⚠️ Promote me as admin for full functionality!"

        aks=await message.reply_text(reply_text)
        await asyncio.sleep(60) # Reduced sleep time
        try: await aks.delete()
        except: pass
        try: await m.delete()
        except: pass

        # Add chat to DB if new
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
        # We now add the user *without* any referral info here.
        # Referral info will be handled when they join the group.
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

    # Handle simple deep links like 'subscribe', 'help', etc.
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
            caption=script.PREMIUM_TEXT.format(mention=message.from_user.mention), # Added mention
            reply_markup=InlineKeyboardMarkup(btn)
        )
        return

    # --- File/Batch Request Deep Link ---
    pre, grp_id_str, file_id = "", "", ""
    is_batch = False
    batch_key = ""

    try:
        if data.startswith("allfiles_"):
            is_batch = True
            _, batch_key = data.split("_", 1)
            # Fetch associated files (grp_id needed for settings, but not directly in key)
            files_to_send = temp.FILES_ID.get(batch_key)
            if not files_to_send:
                await message.reply("Batch link expired or invalid.")
                return
            # Need grp_id context for settings, retrieve from CHAT dict if possible
            grp_id = temp.CHAT.get(user_id)
            if not grp_id:
                # Attempt to get grp_id from the first file if stored (depends on structure)
                # This is less reliable, better to ensure context exists
                # Or require grp_id in the batch link itself (e.g., allfiles_grpID_key)
                await message.reply("Could not determine group context for this batch link. Please request from group again.")
                return
            grp_id_str = str(grp_id) # Set for consistency

        elif data.startswith("file_"):
            pre, grp_id_str, file_id = data.split('_', 2)
            grp_id = int(grp_id_str) # Needed for settings
        else:
             # Try decoding Base64 (legacy?) - Needs testing if still used
             try:
                 decoded_data = (base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))).decode("ascii")
                 pre, file_id = decoded_data.split("_", 1)
                 # Base64 links likely won't have grp_id, cannot proceed with verification/fsub
                 await message.reply("Unsupported link format.")
                 return
             except:
                 await message.reply("Invalid deep link.")
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


    # --- Join Request Check (Before Verification) ---
    if (JOIN_REQUEST_FSUB and AUTH_CHANNEL and
        not await db.has_premium_access(user_id) and
        not await db.check_referral_access(user_id) and
        not await db.has_requested_join(user_id)):
        try:
            invite_link = await client.create_chat_invite_link(int(AUTH_CHANNEL), creates_join_request=True)
            btn = [
                [InlineKeyboardButton("➡️ Send Join Request", url=invite_link.invite_link)],
                [InlineKeyboardButton("🔄 Try Again", url=f"https://t.me/{temp.U_NAME}?start={data}")]
            ]
            await message.reply_text(script.JOIN_REQUEST_TEXT, reply_markup=InlineKeyboardMarkup(btn))
            return
        except ChatAdminRequired:
            logger.error(f"Bot must be admin in AUTH_CHANNEL ({AUTH_CHANNEL}) to create invite links.")
            await message.reply_text("❗ Config Error: Cannot create join link. Contact admin.")
            return
        except Exception as e:
            logger.error(f"Error creating join request link: {e}")
            await message.reply_text("❗ Error generating join link. Try again.")
            return

    # --- Verification Check (Only if not premium/referral) ---
    if not await db.has_premium_access(user_id) and not await db.check_referral_access(user_id):
        user_verified = await db.is_user_verified(user_id)
        is_second_shortener = await db.use_second_shortener(user_id, settings.get('verify_time', TWO_VERIFY_GAP))

        if settings.get("is_verify", IS_VERIFY) and (not user_verified or is_second_shortener):
            # For batch, use a placeholder or handle differently? Using first file_id for now.
            target_file_id = file_id if not is_batch else files_to_send[0].file_id
            if not target_file_id:
                 await message.reply("Error: Could not determine file for verification link.")
                 return

            verify_id_suffix = batch_key if is_batch else file_id # Link should bring user back
            start_param = f"allfiles_{batch_key}" if is_batch else f"file_{grp_id_str}_{file_id}"

            verify_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=7))
            await db.create_verify_id(user_id, verify_id)
            temp.CHAT[user_id] = grp_id
            verify_link = await get_shortlink(f"https://telegram.me/{temp.U_NAME}?start=notcopy_{user_id}_{verify_id}_{start_param}", grp_id, is_second_shortener) # Pass original start param
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

    # --- Send File(s) ---
    if is_batch:
         # Send all files from the batch
         total_files = len(files_to_send)
         sent_count = 0
         failed_count = 0
         prog = await message.reply(f"Sending batch... ({sent_count}/{total_files})")
         for file_obj in files_to_send:
              CAPTION = settings.get('caption', script.FILE_CAPTION)
              f_caption = CAPTION.format(
                   file_name = file_obj.file_name,
                   file_size = get_size(file_obj.file_size),
                   file_caption= file_obj.caption if file_obj.caption else ""
              )
              f_id = file_obj.file_id
              btn = [[ InlineKeyboardButton("✛ Stream/Download ✛", callback_data=f'stream#{f_id}') ]] # Button per file
              try:
                   await client.send_cached_media(
                       chat_id=user_id, file_id=f_id, caption=f_caption,
                       protect_content=settings.get('file_secure', False),
                       reply_markup=InlineKeyboardMarkup(btn)
                   )
                   sent_count += 1
                   await asyncio.sleep(1) # Small delay between files
                   if sent_count % 10 == 0: # Update progress every 10 files
                        try: await prog.edit_text(f"Sending batch... ({sent_count}/{total_files})")
                        except: pass
              except FloodWait as fw:
                   await asyncio.sleep(fw.value + 2) # Wait a bit longer
                   await client.send_cached_media(chat_id=user_id, file_id=f_id, caption=f_caption, protect_content=settings.get('file_secure', False), reply_markup=InlineKeyboardMarkup(btn))
                   sent_count += 1
              except Exception as send_error:
                   logger.error(f"Failed sending file {f_id} in batch to {user_id}: {send_error}")
                   failed_count += 1

         try: await prog.delete()
         except: pass
         await message.reply(f"Batch sent: {sent_count} successful, {failed_count} failed.")
         # Clean up batch key? Optional.
         # if batch_key in temp.FILES_ID: del temp.FILES_ID[batch_key]
         return

    else:
        # Send single file
        files_ = await get_file_details(file_id)
        if not files_:
            # Try decoding base64 again if needed (legacy check)
            try:
                decoded_data = (base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))).decode("ascii")
                pre, file_id = decoded_data.split("_", 1)
                files_ = await get_file_details(file_id)
                if not files_:
                     return await message.reply('<b>⚠️ File not found. It might have been deleted.</b>')
            except:
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
             # Auto-delete is handled in pm_filter usually, not needed here unless you want specific behaviour
        except Exception as send_error:
             logger.error(f"Error sending file {file_id} to {user_id}: {send_error}")
             await message.reply_text("<b>❌ Sorry, couldn't send the file. Please try again later.</b>")


@Client.on_message(filters.command('delete') & filters.user(ADMINS))
async def delete(bot, message):
    """Delete file from database"""
    reply = message.reply_to_message
    if not reply:
        await message.reply('Reply to the file message you want to delete.')
        return

    msg = await message.reply("Processing...⏳", quote=True)

    media = getattr(reply, reply.media.value, None)
    if not media:
         await msg.edit('<b>This is not a supported media message.</b>')
         return

    file_id, file_ref = unpack_new_file_id(media.file_id) # Use helper function
    result = await Media.collection.delete_one({'_id': file_id})

    if result.deleted_count:
        await msg.edit('<b>✅️ File successfully deleted from database!</b>')
    else:
        # Fallback: Try deleting by filename, size, mime_type (less reliable with renamed files)
        file_name_search = re.sub(r"(_|\-|\.|\+)", " ", str(media.file_name)) # Use cleaned name for search
        result = await Media.collection.delete_many({
            'file_name': file_name_search,
            'file_size': media.file_size,
            'mime_type': media.mime_type
            })
        if result.deleted_count:
            await msg.edit(f'<b>✅️ File successfully deleted (found by properties)! Deleted {result.deleted_count} matching entries.</b>')
        else:
            await msg.edit('<b>⚠️ File not found in database using file_id or properties.</b>')

@Client.on_message(filters.command('deleteall') & filters.user(ADMINS))
async def delete_all_index(bot, message):
    if str(message.from_user.id) not in ADMINS: # Ensure check works for string ADMINS
        return await message.reply('ᴏɴʟʏ ᴛʜᴇ ʙᴏᴛ ᴏᴡɴᴇʀ ᴄᴀɴ ᴜsᴇ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ... 😑')

    files_count = await Media.count_documents()
    if int(files_count) == 0:
        return await message.reply_text('The files database is already empty!')

    btn = [[ InlineKeyboardButton(text="YES, Delete All!", callback_data="all_files_delete") ],
           [ InlineKeyboardButton(text="CANCEL", callback_data="close_data") ]]
    await message.reply_text(
        f'<b>⚠️ This will delete ALL {files_count} indexed files irreversibly.\nAre you absolutely sure?</b>',
        reply_markup=InlineKeyboardMarkup(btn)
    )

@Client.on_message(filters.command('settings'))
async def settings_cmd(client, message): # Renamed to avoid conflict
    user_id = message.from_user.id if message.from_user else None
    if not user_id:
        return await message.reply("<b>💔 Anonymous admins cannot use this command.</b>")

    chat_type = message.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await message.reply_text("<code>Use this command in a group.</code>")

    grp_id = message.chat.id
    if not await is_check_admin(client, grp_id, message.from_user.id):
        return await message.reply_text('<b>You are not an admin in this group.</b>')

    settings = await get_settings(grp_id)
    title = message.chat.title

    # Use .get() for safety
    buttons = [[
        InlineKeyboardButton('Auto Filter', callback_data=f'setgs#auto_filter#{settings.get("auto_filter", True)}#{grp_id}'),
        InlineKeyboardButton('ON ✔️' if settings.get("auto_filter", True) else 'OFF ✗', callback_data=f'setgs#auto_filter#{settings.get("auto_filter", True)}#{grp_id}')
    ],[
        InlineKeyboardButton('File Secure', callback_data=f'setgs#file_secure#{settings.get("file_secure", False)}#{grp_id}'),
        InlineKeyboardButton('ON ✔️' if settings.get("file_secure", False) else 'OFF ✗', callback_data=f'setgs#file_secure#{settings.get("file_secure", False)}#{grp_id}')
    ],[
        InlineKeyboardButton('IMDB', callback_data=f'setgs#imdb#{settings.get("imdb", True)}#{grp_id}'),
        InlineKeyboardButton('ON ✔️' if settings.get("imdb", True) else 'OFF ✗', callback_data=f'setgs#imdb#{settings.get("imdb", True)}#{grp_id}')
    ],[
        InlineKeyboardButton('Spell Check', callback_data=f'setgs#spell_check#{settings.get("spell_check", True)}#{grp_id}'),
        InlineKeyboardButton('ON ✔️' if settings.get("spell_check", True) else 'OFF ✗', callback_data=f'setgs#spell_check#{settings.get("spell_check", True)}#{grp_id}')
    ],[
        InlineKeyboardButton('Auto Delete', callback_data=f'setgs#auto_delete#{settings.get("auto_delete", False)}#{grp_id}'),
        InlineKeyboardButton(f'{get_readable_time(DELETE_TIME)}' if settings.get("auto_delete", False) else 'OFF ✗', callback_data=f'setgs#auto_delete#{settings.get("auto_delete", False)}#{grp_id}')
    ],[
        InlineKeyboardButton('Result Mode', callback_data=f'setgs#link#{settings.get("link", True)}#{str(grp_id)}'),
        InlineKeyboardButton('Link' if settings.get("link", True) else 'Button', callback_data=f'setgs#link#{settings.get("link", True)}#{str(grp_id)}')
    ],[
        InlineKeyboardButton('Verify', callback_data=f'setgs#is_verify#{settings.get("is_verify", True)}#{grp_id}'),
        InlineKeyboardButton('ON ✔️' if settings.get("is_verify", True) else 'OFF ✗', callback_data=f'setgs#is_verify#{settings.get("is_verify", True)}#{grp_id}')
    ],[
        InlineKeyboardButton('☕️ Close ☕️', callback_data='close_data')
    ]]
    await message.reply_text(
        text=f"Change settings for <b>'{title}'</b> ✨",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode=enums.ParseMode.HTML
    )


@Client.on_message(filters.command('set_template') & filters.group)
async def save_template(client, message):
    grp_id = message.chat.id
    title = message.chat.title
    if not await is_check_admin(client, grp_id, message.from_user.id):
        return await message.reply_text('<b>You are not an admin in this group.</b>')
    try:
        template = message.text.split(" ", 1)[1]
    except IndexError:
        return await message.reply_text("<b>Command incomplete! Use /set_template {template_text}</b>\n\nUse keywords like `{title}`, `{year}`, `{rating}`, etc.")
    await save_group_settings(grp_id, 'template', template)
    await message.reply_text(f"✅ Successfully changed IMDB template for {title}.", disable_web_page_preview=True)

@Client.on_message(filters.command("send") & filters.user(ADMINS))
async def send_msg(bot, message):
    if not message.reply_to_message:
        return await message.reply_text("<b>Reply to a message to send it. Usage: /send user_id1 [user_id2...]</b>")

    target_ids_str = message.text.split(" ")[1:]
    if not target_ids_str:
        return await message.reply_text("<b>Please provide one or more user IDs separated by spaces.</b>")

    target_ids = []
    for uid_str in target_ids_str:
        try:
            target_ids.append(int(uid_str.strip()))
        except ValueError:
            await message.reply_text(f"⚠️ Invalid User ID: `{uid_str}`. Skipping.")
            continue

    if not target_ids:
        return await message.reply_text("<b>No valid user IDs provided.</b>")

    out = "Sending Report:\n\n"
    success_count = 0
    fail_count = 0
    start_time = time.time()
    status_msg = await message.reply_text(f"Sending to {len(target_ids)} users...")

    for i, target_id in enumerate(target_ids):
        try:
            user = await bot.get_users(target_id) # Verify user ID
            await message.reply_to_message.copy(int(user.id))
            out += f"✅ Sent to: {user.mention} (`{user.id}`)\n"
            success_count += 1
        except UserIsBlocked:
            out += f"❌ Failed (Blocked): `{target_id}`\n"
            fail_count += 1
        except Exception as e:
            out += f"❌ Failed: `{target_id}` - Error: `{str(e)}`\n"
            fail_count += 1

        await asyncio.sleep(1) # Small delay

        if i % 10 == 0: # Update status occasionally
            try:
                await status_msg.edit_text(f"Sending to {len(target_ids)} users...\nSent: {success_count}, Failed: {fail_count}")
            except: pass # Ignore modification errors

    time_taken = get_readable_time(time.time() - start_time)
    await status_msg.delete() # Delete progress message
    final_report = f"<b><u>Send Report</u></b>\nTime Taken: {time_taken}\n\nSuccessful: `{success_count}`\nFailed: `{fail_count}`\n\n" + out
    try:
        await message.reply_text(final_report)
    except MessageTooLong: # Send as file if too long
        with open("send_report.txt", "w") as f:
            f.write(final_report.replace('<b>','').replace('</b>','').replace('<code>','').replace('</code>','')) # Basic clean for text file
        await message.reply_document("send_report.txt", caption=f"Send Report (Too Long)\nTime: {time_taken} | Success: {success_count} | Failed: {fail_count}")
        os.remove("send_report.txt")


@Client.on_message(filters.regex("#request") & filters.group)
async def send_request(bot, message):
    if not REQUEST_CHANNEL:
         return await message.reply("Request feature is currently disabled.")
    try:
        request = message.text.split("#request", 1)[1].strip()
        if not request:
             raise IndexError # Trigger error if request text is empty
    except IndexError:
        await message.reply_text("<b>‼️ Please write your request after #request tag. Example: `#request Movie Name (Year)`</b>")
        return

    # Check for flood control (e.g., one request per user per hour) - Optional
    # ...

    buttons = [[
        InlineKeyboardButton('👀 View Request Context', url=f"{message.link}") # Link to original message
    ],[
        InlineKeyboardButton('⚙ Show Options', callback_data=f'show_options#{message.from_user.id}#{message.id}')
    ]]
    try:
        sent_request = await bot.send_message(
            REQUEST_CHANNEL,
            script.REQUEST_TXT.format(message.from_user.mention, message.from_user.id, request),
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        btn = [[ InlineKeyboardButton('✨ View Your Request Status ✨', url=f"{sent_request.link}") ]] # Link to msg in req channel
        await message.reply_text("<b>✅ Request successfully submitted! Please wait for an admin to process it.</b>", reply_markup=InlineKeyboardMarkup(btn))
    except Exception as e:
        logger.error(f"Failed to send request to channel {REQUEST_CHANNEL}: {e}")
        await message.reply_text("<b>❌ Sorry, could not submit your request. Please try again later or contact support.</b>")


@Client.on_message(filters.command("search") & filters.user(ADMINS) & filters.private)
async def search_files_cmd(bot, message): # Renamed function
    try:
        keyword = message.text.split(" ", 1)[1]
    except IndexError:
        return await message.reply_text(f"<b>Hey {message.from_user.mention}, provide a keyword to search for files to delete. /search keyword</b>")

    files, total = await get_bad_files(keyword) # Use get_bad_files? Seems intended for finding files to delete
    if int(total) == 0:
        await message.reply_text('<i>No files found with this keyword 😐</i>')
        return

    file_list_text = f"🔍 Files found for '{keyword}' ({total} total):\n\n"
    for index, item in enumerate(files):
        # file_list_text += f"{index + 1}. `{item.file_name}` (Size: {get_size(item.file_size)}, ID: `{item.file_id}`)\n"
        file_list_text += f"{index + 1}. `{item.file_name}`\n" # Simplified list

    try:
        await message.reply_text(file_list_text)
    except MessageTooLong:
        with open("search_results.txt", "w") as file:
            # Recreate list without markdown for file
            file_data_txt = f"Files found for '{keyword}' ({total} total):\n\n"
            for index, item in enumerate(files):
                 file_data_txt += f"{index + 1}. {item.file_name} (Size: {get_size(item.file_size)}, ID: {item.file_id})\n"
            file.write(file_data_txt)
        await message.reply_document(
            document="search_results.txt",
            caption=f"<b>♻️ Found {total} files matching '{keyword}'. List attached.</b>",
        )
        os.remove("search_results.txt")


@Client.on_message(filters.command("deletefiles") & filters.user(ADMINS) & filters.private)
async def deletemultiplefiles(bot, message):
    try:
        keyword = message.text.split(" ", 1)[1]
    except IndexError:
       return await message.reply_text(f"<b>Use /deletefiles keyword</b>")

    files, total = await get_bad_files(keyword)
    if int(total) == 0:
        await message.reply_text('<i>No files found with this keyword to delete 😐</i>')
        return

    btn = [[ InlineKeyboardButton("YES, Delete Them! ✅", callback_data=f"killfilesak#{keyword}") ],
           [ InlineKeyboardButton("CANCEL 😢", callback_data="close_data") ]]
    await message.reply_text(
        text=f"<b>Found {total} files matching '{keyword}'.\n\n⚠️ Do you want to permanently delete ALL of them? This cannot be undone!</b>",
        reply_markup=InlineKeyboardMarkup(btn),
    )

# del_file command seems redundant if deletefiles uses keywords. Keeping for specific filename deletion.
@Client.on_message(filters.command("del_file") & filters.user(ADMINS) & filters.private)
async def delete_specific_files(bot, message): # Renamed
    try:
        # Assumes filenames are provided, separated by comma
        filenames_to_delete = [name.strip() for name in message.text.split(" ", 1)[1].split(",")]
        if not filenames_to_delete or all(not name for name in filenames_to_delete):
             raise IndexError
    except IndexError:
        return await message.reply_text("<b>Usage: /del_file filename1[,filename2,...]</b>\nProvide exact filenames separated by commas.")

    deleted_files_count = 0
    not_found_files = []
    error_files = []

    status_msg = await message.reply(f"Processing {len(filenames_to_delete)} filenames...")

    for filename in filenames_to_delete:
        if not filename: continue # Skip empty names
        try:
            # Use delete_many to catch potential duplicates with the same name
            result = await Media.collection.delete_many({'file_name': filename})
            if result.deleted_count > 0:
                deleted_files_count += result.deleted_count
            else:
                not_found_files.append(filename)
        except Exception as e:
            logger.error(f"Error deleting file '{filename}': {e}")
            error_files.append(filename)

    await status_msg.delete()
    reply_text = ""
    if deleted_files_count > 0:
        reply_text += f'<b>✅ Successfully deleted {deleted_files_count} file entries.</b>\n'
    if not_found_files:
        reply_text += f'<b>⚠️ Files not found:</b> <code>{", ".join(not_found_files)}</code>\n'
    if error_files:
        reply_text += f'<b>❌ Errors occurred for:</b> <code>{", ".join(error_files)}</code>\n'

    if not reply_text: # Should not happen if input was valid
         reply_text = "No action taken."

    await message.reply_text(reply_text)


@Client.on_message(filters.command('set_caption') & filters.group)
async def save_caption(client, message):
    grp_id = message.chat.id
    title = message.chat.title
    if not await is_check_admin(client, grp_id, message.from_user.id):
        return await message.reply_text('<b>You are not an admin in this group.</b>')
    try:
        caption = message.text.split(" ", 1)[1]
    except IndexError:
        return await message.reply_text("<b>Command incomplete! Use /set_caption {caption_text}</b>\n\nUse keywords: `{file_name}`, `{file_size}`, `{file_caption}`")
    await save_group_settings(grp_id, 'caption', caption)
    await message.reply_text(f"✅ Successfully changed file caption for {title}.", disable_web_page_preview=True)

@Client.on_message(filters.command('set_tutorial') & filters.group)
async def save_tutorial(client, message):
    grp_id = message.chat.id
    title = message.chat.title
    if not await is_check_admin(client, grp_id, message.from_user.id):
        return await message.reply_text('<b>You are not an admin in this group.</b>')
    try:
        tutorial = message.text.split(" ", 1)[1]
        # Basic URL validation
        if not tutorial.startswith("http://") and not tutorial.startswith("https://"):
             raise ValueError("Invalid URL format")
    except IndexError:
        return await message.reply_text("<b>Command incomplete! Use /set_tutorial https://your-link.com</b>")
    except ValueError:
         return await message.reply_text("<b>Invalid URL format. Please provide a valid link starting with http:// or https://</b>")

    await save_group_settings(grp_id, 'tutorial', tutorial)
    await message.reply_text(f"<b>✅ Successfully changed tutorial link for {title}.</b>", disable_web_page_preview=True)

@Client.on_message(filters.command('set_shortner') & filters.group)
async def set_shortner(c, m):
    grp_id = m.chat.id
    title = m.chat.title
    if not await is_check_admin(c, grp_id, m.from_user.id):
        return await m.reply_text('<b>You are not an admin in this group.</b>')
    if len(m.command) != 3:
        await m.reply("<b>Usage: /set_shortner yoursite.com your_api_key</b>")
        return

    sts = await m.reply("<b>♻️ Checking API...</b>")
    URL = m.command[1].strip().rstrip('/') # Clean URL
    API = m.command[2].strip()

    # Basic check if URL looks like a domain
    if '.' not in URL or '/' in URL.split('//', 1)[-1]: # Check for domain structure
        await sts.edit("<b>⚠️ Invalid URL format. Provide domain name only (e.g., mysite.net)</b>")
        return

    test_url = f"https://{URL}/api?api={API}&url=https://telegram.dog" # Simple test URL
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(test_url) as resp:
                if resp.status != 200:
                    raise Exception(f"API Check Failed (Status: {resp.status})")
                data = await resp.json()
                if data.get('status') == 'success' and data.get('shortenedUrl'):
                    SHORT_LINK = data['shortenedUrl']
                    await save_group_settings(grp_id, 'shortner', URL)
                    await save_group_settings(grp_id, 'api', API)
                    await sts.edit(f"<b><u>✅ 1st Shortener Set Successfully!</u>\n\nSite: `{URL}`\nAPI: `{API}`\nDemo: {SHORT_LINK}</b>", disable_web_page_preview=True)

                    # Log the change
                    try:
                        user_info = f"@{m.from_user.username}" if m.from_user.username else f"{m.from_user.mention}"
                        link = await c.export_chat_invite_link(m.chat.id)
                        grp_link = f"[{title}]({link})" if link else title
                        log_message = f"#Shortner1_Set\nUser: {user_info} (`{m.from_user.id}`)\nGroup: {grp_link} (`{grp_id}`)\nDomain: `{URL}`\nAPI: `{API}`"
                        await c.send_message(LOG_API_CHANNEL, log_message, disable_web_page_preview=True)
                    except Exception as log_e:
                        logger.error(f"Error logging shortener set: {log_e}")

                else:
                    error_msg = data.get('message', 'Unknown API Error')
                    await sts.edit(f"<b><u>❌ API Check Failed!</u>\n\nSite: `{URL}`\nAPI: `{API}`\nError: `{error_msg}`\n\nDefault shortener restored.</b>")
                    # Restore defaults if check fails
                    await save_group_settings(grp_id, 'shortner', SHORTENER_WEBSITE)
                    await save_group_settings(grp_id, 'api', SHORTENER_API)

    except Exception as e:
        logger.error(f"Error setting shortener 1: {e}")
        await sts.edit(f"<b><u>❌ Error Occurred!</u>\n\nError: `{e}`\n\nDefault shortener restored. Check your site/API or contact support.</b>")
        await save_group_settings(grp_id, 'shortner', SHORTENER_WEBSITE)
        await save_group_settings(grp_id, 'api', SHORTENER_API)


@Client.on_message(filters.command('set_shortner_2') & filters.group)
async def set_shortner_2(c, m):
    grp_id = m.chat.id
    title = m.chat.title
    if not await is_check_admin(c, grp_id, m.from_user.id):
        return await m.reply_text('<b>You are not an admin in this group.</b>')
    if len(m.command) != 3:
        await m.reply("<b>Usage: /set_shortner_2 yoursite2.com your_api_key2</b>")
        return

    sts = await m.reply("<b>♻️ Checking API...</b>")
    URL = m.command[1].strip().rstrip('/')
    API = m.command[2].strip()

    if '.' not in URL or '/' in URL.split('//', 1)[-1]:
        await sts.edit("<b>⚠️ Invalid URL format. Provide domain name only.</b>")
        return

    test_url = f"https://{URL}/api?api={API}&url=https://telegram.dog"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(test_url) as resp:
                if resp.status != 200:
                    raise Exception(f"API Check Failed (Status: {resp.status})")
                data = await resp.json()
                if data.get('status') == 'success' and data.get('shortenedUrl'):
                    SHORT_LINK = data['shortenedUrl']
                    await save_group_settings(grp_id, 'shortner_two', URL)
                    await save_group_settings(grp_id, 'api_two', API)
                    await sts.edit(f"<b><u>✅ 2nd Shortener Set Successfully!</u>\n\nSite: `{URL}`\nAPI: `{API}`\nDemo: {SHORT_LINK}</b>", disable_web_page_preview=True)

                    # Log the change
                    try:
                        user_info = f"@{m.from_user.username}" if m.from_user.username else f"{m.from_user.mention}"
                        link = await c.export_chat_invite_link(m.chat.id)
                        grp_link = f"[{title}]({link})" if link else title
                        log_message = f"#Shortner2_Set\nUser: {user_info} (`{m.from_user.id}`)\nGroup: {grp_link} (`{grp_id}`)\nDomain: `{URL}`\nAPI: `{API}`"
                        await c.send_message(LOG_API_CHANNEL, log_message, disable_web_page_preview=True)
                    except Exception as log_e:
                        logger.error(f"Error logging shortener 2 set: {log_e}")

                else:
                    error_msg = data.get('message', 'Unknown API Error')
                    await sts.edit(f"<b><u>❌ API Check Failed!</u>\n\nSite: `{URL}`\nAPI: `{API}`\nError: `{error_msg}`\n\nDefault 2nd shortener restored.</b>")
                    await save_group_settings(grp_id, 'shortner_two', SHORTENER_WEBSITE2)
                    await save_group_settings(grp_id, 'api_two', SHORTENER_API2)

    except Exception as e:
        logger.error(f"Error setting shortener 2: {e}")
        await sts.edit(f"<b><u>❌ Error Occurred!</u>\n\nError: `{e}`\n\nDefault 2nd shortener restored. Check your site/API or contact support.</b>")
        await save_group_settings(grp_id, 'shortner_two', SHORTENER_WEBSITE2)
        await save_group_settings(grp_id, 'api_two', SHORTENER_API2)


@Client.on_message(filters.command('set_log_channel') & filters.group)
async def set_log(client, message):
    grp_id = message.chat.id
    title = message.chat.title
    if not await is_check_admin(client, grp_id, message.from_user.id):
        return await message.reply_text('<b>You are not an admin in this group.</b>')
    if len(message.command) != 2:
        await message.reply("<b>Usage: /set_log_channel -100xxxxxxxxxx</b>")
        return

    try:
        log_channel_id = int(message.command[1])
        # Check if ID format looks like a channel/supergroup ID
        if not str(log_channel_id).startswith("-100"):
             raise ValueError("ID should start with -100")
    except ValueError:
        return await message.reply_text('<b>Invalid Channel ID format. Must be an integer starting with -100.</b>')

    sts = await message.reply("<b>♻️ Checking channel access...</b>")
    try:
       test_msg = await client.send_message(chat_id=log_channel_id, text="<b>Testing log channel access...</b>")
       await asyncio.sleep(2)
       await test_msg.delete()
    except Exception as e:
        return await sts.edit(f'<b>❌ Error accessing channel ID `{log_channel_id}`.\nMake sure the bot is an admin there.\n\nError: `{e}`</b>')

    await save_group_settings(grp_id, 'log', log_channel_id)
    await sts.edit(f"<b>✅ Successfully set Log Channel for {title} to `{log_channel_id}`.</b>")

    # Log the change
    try:
        user_info = f"@{message.from_user.username}" if message.from_user.username else f"{message.from_user.mention}"
        link = await client.export_chat_invite_link(message.chat.id)
        grp_link = f"[{title}]({link})" if link else title
        log_message = f"#LogChannel_Set\nUser: {user_info} (`{message.from_user.id}`)\nGroup: {grp_link} (`{grp_id}`)\nLog Channel: `{log_channel_id}`"
        await client.send_message(LOG_API_CHANNEL, log_message, disable_web_page_preview=True)
    except Exception as log_e:
        logger.error(f"Error logging log channel set: {log_e}")

@Client.on_message(filters.command('details') & filters.group)
async def all_settings(client, message):
    grp_id = message.chat.id
    title = message.chat.title
    if not await is_check_admin(client, grp_id, message.from_user.id):
        return await message.reply_text('<b>You are not an admin in this group.</b>')

    settings = await get_settings(grp_id) # Fetches current or default settings

    text = f"""<b><u>⚙️ Current Settings For:</u> {title}</b>

<b><u>Shorteners:</u></b>
1st Verify Site: <code>{settings.get('shortner', 'N/A')}</code>
1st Verify API: <code>{settings.get('api', 'N/A')}</code>
2nd Verify Site: <code>{settings.get('shortner_two', 'N/A')}</code>
2nd Verify API: <code>{settings.get('api_two', 'N/A')}</code>

<b><u>Channels & Links:</u></b>
Log Channel ID: <code>{settings.get('log', 'N/A')}</code>
Tutorial Link: {settings.get('tutorial', 'N/A')}

<b><u>Formatting:</u></b>
IMDB Template: <code>{settings.get('template', 'N/A')}</code>
File Caption: <code>{settings.get('caption', 'N/A')}</code>
"""

    btn = [[ InlineKeyboardButton("🔄 Reset All To Default", callback_data="reset_grp_data") ],
           [ InlineKeyboardButton("⚙ Modify Settings", callback_data="open_settings_panel") ], # Add button to open /settings panel
           [ InlineKeyboardButton("🗑 Close", callback_data="close_data") ]]
    reply_markup=InlineKeyboardMarkup(btn)
    dlt=await message.reply_text(text, reply_markup=reply_markup, disable_web_page_preview=True)
    # Optional: Auto-delete details message
    # await asyncio.sleep(300)
    # try: await dlt.delete()
    # except: pass


@Client.on_message(filters.command('set_time') & filters.group)
async def set_time(client, message):
    if not await is_check_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text('<b>You are not an admin in this group.</b>')

    try:
        time_str = message.text.split(" ", 1)[1]
        # Convert to seconds using existing helper
        time_seconds = await get_seconds(time_str)
        if time_seconds <= 0:
             raise ValueError("Time must be positive")
    except IndexError:
        return await message.reply_text("<b>Command incomplete! Use /set_time [duration]</b>\nExample: `/set_time 10min` or `/set_time 1hour`")
    except ValueError:
         return await message.reply_text("<b>Invalid time format! Use numbers followed by 'min', 'hour', or 'day'.</b>\nExample: `/set_time 10min` or `/set_time 1hour`")

    await save_group_settings(message.chat.id, 'verify_time', time_seconds)
    await message.reply_text(f"✅ Successfully set 2nd verify gap for {message.chat.title} to <b>{get_readable_time(time_seconds)}</b>.")

# Add callback handler for the new 'open_settings_panel' button in /details
@Client.on_callback_query(filters.regex('^open_settings_panel'))
async def open_settings_panel_callback(client, query):
     if not await is_check_admin(client, query.message.chat.id, query.from_user.id):
          return await query.answer("Only admins can modify settings.", show_alert=True)
     # Call the existing settings function programmatically
     await query.answer("Opening settings panel...")
     await settings_cmd(client, query.message) # Reuse the /settings command logic

