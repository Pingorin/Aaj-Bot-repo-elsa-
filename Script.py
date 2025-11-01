import os
class script(object):
    
    START_TXT = """<b>ʜᴇʏ {} {},
    
ɪ'ᴍ ᴀ ᴘᴏᴡᴇʀꜰᴜʟ ᴀᴜᴛᴏ ꜰɪʟᴛᴇʀ ᴡɪᴛʜ ᴀᴅᴠᴀɴᴄᴇ ᴇᴀʀɴ ʙᴏᴛ. ʏᴏᴜ ᴄᴀɴ ᴜꜱᴇ ᴍᴇ ɪɴ ʏᴏᴜʀ ɢʀᴏᴜᴘ ɪ ᴡɪʟʟ ɢɪᴠᴇ ᴀɴʏ ᴍᴏᴠɪᴇꜱ ᴏʀ ꜱᴇʀɪᴇꜱ ɪɴ ɢʀᴏᴜᴘ ʙʏ ʏᴏᴜʀ ᴄᴏɴɴᴇᴄᴛᴇᴅ ꜱʜᴏʀᴛɴᴇʀ...💰

ʏᴏᴜʀ ɪᴅ - <code>{}</code></b>"""
    
    HELP_TXT = """<b>ᴄʟɪᴄᴋ ᴏɴ ᴛʜᴇ ʙᴜᴛᴛᴏɴꜱ ʙᴇʟᴏᴡ ᴛᴏ ɢᴇᴛ ᴅᴏᴄᴜᴍᴇɴᴛᴀᴛɪᴏɴ ᴀʙᴏᴜᴛ ꜱᴘᴇᴄɪꜰɪᴄ ᴍᴏᴅᴜʟᴇꜱ..</b>"""
    
    TELE_TXT = """<b>/telegraph - sᴇɴᴅ ᴍᴇ ᴘɪᴄᴛᴜʀᴇ ᴏʀ ᴠɪᴅᴇᴏ ᴜɴᴅᴇʀ (5ᴍʙ)

ɴᴏᴛᴇ - ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ᴡᴏʀᴋ ɪɴ ʙᴏᴛʜ ɢʀᴏᴜᴘs ᴀɴᴅ ʙᴏᴛ ᴘᴍ</b>"""
 
    STATUS_TXT = """<b><u>🗃 ᴅᴀᴛᴀʙᴀsᴇ 1 🗃</u>

» ᴛᴏᴛᴀʟ ᴜsᴇʀs - <code>{}</code>
» ᴛᴏᴛᴀʟ ɢʀᴏᴜᴘs - <code>{}</code>
» ᴜsᴇᴅ sᴛᴏʀᴀɢᴇ - <code>{} / {}</code>

<u>🗳 ᴅᴀᴛᴀʙᴀsᴇ 2 🗳</u></b>

» ᴛᴏᴛᴀʟ ꜰɪʟᴇs - <code>{}</code>
» ᴜsᴇᴅ sᴛᴏʀᴀɢᴇ - <code>{} / {}</code>

<u>🤖 ʙᴏᴛ ᴅᴇᴛᴀɪʟs 🤖</u>

» ᴜᴘᴛɪᴍᴇ - <code>{}</code>
» ʀᴀᴍ - <code>{}%</code>
» ᴄᴘᴜ - <code>{}%</code></b>"""

    NEW_USER_TXT = """<b>#New_User {}

≈ ɪᴅ:- <code>{}</code>
≈ ɴᴀᴍᴇ:- {}</b>"""

    NEW_GROUP_TXT = """#New_Group {}

Group name - {}
Id - <code>{}</code>
Group username - @{}
Group link - {}
Total members - <code>{}</code>
User - {}"""

    REQUEST_TXT = """<b>📜 ᴜꜱᴇʀ - {}
📇 ɪᴅ - <code>{}</code>

🎁 ʀᴇǫᴜᴇꜱᴛ ᴍꜱɢ - <code>{}</code></b>"""  
    
    REFERRAL_TXT = """👋 Hey {user_mention}!

Invite your friends to our group and get **1 Month of FREE Premium Access**!

**Your Personal Invite Link:**
`{referral_link}`

Share this link with your friends. When **{target}** users join the group using your link, you'll automatically receive 1 month of premium access (no more link shorteners!).

You have currently invited **{current_count}** / {target} users.
"""

    IMDB_TEMPLATE_TXT = """<b>📻 ᴛɪᴛʟᴇ - <a href={url}>{title}</a>
🎭 ɢᴇɴʀᴇs - {genres}
🎖 ʀᴀᴛɪɴɢ - <a href={url}/ratings>{rating}</a> / 10 (ʙᴀsᴇᴅ ᴏɴ {votes} ᴜsᴇʀ ʀᴀᴛɪɴɢ.)
📆 ʏᴇᴀʀ - {release_date}
❗️ ʟᴀɴɢᴜᴀɢᴇ - {languages}</b>
"""

    FILE_CAPTION = """<b><a href=https://t.me/Aksbackup>{file_name} </a></b>

<i>ᴘʟᴇᴀsᴇ ꜰᴏʀᴡᴀʀᴅ ᴛʜɪs ꜰɪʟᴇs ᴛᴏ ᴛʜᴇ sᴀᴠᴇᴅ ᴍᴇssᴀɢᴇ ᴀɴᴅ ᴄʟᴏsᴇ ᴛʜɪs ᴍᴇssᴀɢᴇ</i>"""

    RESTART_TXT = """<b>
📅 Dᴀᴛᴇ : <code>{}</code>
⏰ Tɪᴍᴇ : <code>{}</code>
🌐 Tɪᴍᴇᴢᴏɴᴇ : <code>Asia/Kolkata</code></b>"""

    ALRT_TXT = """❌ 𝗧𝗵𝗮𝘁 𝗶𝘀 𝗻𝗼𝘁 𝗳𝗼𝗿 𝘆𝗼𝘂 𝘀𝗶𝗿 ⛔️"""

    OLD_ALRT_TXT = """𝐘𝐨𝐮 𝐚𝐫𝐞 𝐮𝐬𝐢𝐧𝐠 𝐨𝐧𝐞 𝐨𝐟 𝐦𝐲 𝐨𝐥𝐝 𝐦𝐞𝐬𝐬𝐚𝐠𝐞𝐬, 𝐩𝐥𝐞𝐚𝐬𝐞 𝐬𝐞𝐧𝐝 𝐭𝐡𝐞 𝐫𝐞𝐪𝐮𝐞𝐬𝐭 𝐚𝐠𝐚𝐢𝐧"""

    NO_RESULT_TXT = """🗳 𝗧𝗵𝗶𝘀 𝗠𝗼𝘃𝗶𝗲 𝗶𝘀 𝗻𝗼𝘁 𝘆𝗲𝘁 𝗿𝗲𝗹𝗲𝗮𝘀𝗲𝗱 𝗼𝗿 𝗮𝗱𝗱𝗲𝗱 𝘁𝗼 𝗱𝗮𝘁𝗮𝗯𝗮𝘀𝗲 🗳"""
    
    I_CUDNT = """🤧 𝗛𝗲𝗹𝗹𝗼 {}

𝗜 𝗰𝗼𝘂𝗹𝗱𝗻'𝘁 𝗳𝗶𝗻𝗱 𝗮𝗻𝘆 𝗺𝗼𝘃𝗶𝗲 𝗼𝗿 𝘀𝗲𝗿𝗶𝗲𝘀 𝗶𝗻 𝘁𝗵𝗮𝘁 𝗻𝗮𝗺𝗲.. 😐"""

    I_CUD_NT = """😑 𝗛𝗲𝗹𝗹𝗼 {}

𝗜 𝗰𝗼𝘂𝗹𝗱𝗻'𝘁 𝗳𝗶𝗻𝗱 𝗮𝗻𝘆𝘁𝗵𝗶𝗻𝗴 𝗿𝗲𝗹𝗮𝘁𝗲𝗱 𝘁𝗼 𝘁𝗵𝗮𝘁 😞... 𝗰𝗵𝗲𝗰𝗸 𝘆𝗼𝘂𝗿 𝘀𝗽𝗲𝗹𝗹𝗶𝗻𝗴."""
    
    CUDNT_FND = """🤧 𝗛𝗲𝗹𝗹𝗼 {}

𝗜 𝗰𝗼𝘂𝗹𝗱𝗻'𝘁 𝗳𝗶𝗻𝗱 𝗮𝗻𝘆𝘁𝗵𝗶𝗻𝗴 𝗿𝗲𝗹𝗮𝘁𝗲𝗱 𝘁𝗼 𝘁𝗵𝗮𝘁 𝗱𝗶𝗱 𝘆𝗼𝘂 𝗺𝗲𝗮𝗻 𝗮𝗻𝘆 𝗼𝗻𝗲 𝗼𝗳 𝘁𝗵𝗲𝘀𝗲 ?? 👇"""
    
    FONT_TXT= """<b>ʏᴏᴜ ᴄᴀɴ ᴜsᴇ ᴛʜɪs ᴍᴏᴅᴇ ᴛᴏ ᴄʜᴀɴɢᴇ ʏᴏᴜʀ ꜰᴏɴᴛs sᴛʏʟᴇ, ᴊᴜsᴛ sᴇɴᴅ ᴍᴇ ʟɪᴋᴇ ᴛʜɪs ꜰᴏʀᴍᴀᴛ

<code>/font hi how are you</code></b>"""

    PREMIUM_TEXT = """<b><u>- ᴀᴠᴀɪʟᴀʙʟᴇ ᴘʟᴀɴs - </u>

- 30ʀs - 1 ᴡᴇᴇᴋ
- 50ʀs - 1 ᴍᴏɴᴛʜs
- 120ʀs - 3 ᴍᴏɴᴛʜs
- 220ʀs - 6 ᴍᴏɴᴛʜs

<u>🎁 ᴘʀᴇᴍɪᴜᴍ ғᴇᴀᴛᴜʀᴇs 🎁</u>

○ ɴᴏ ɴᴇᴇᴅ ᴛᴏ ᴠᴇʀɪғʏ
○ ᴅɪʀᴇᴄᴛ ғɪʟᴇs   
○ ᴀᴅ-ғʀᴇᴇ ᴇxᴘᴇʀɪᴇɴᴄᴇ 
○ ʜɪɢʜ-sᴘᴇᴇᴅ ᴅᴏᴡɴʟᴏᴀᴅ ʟɪɴᴋ                         
○ ᴍᴜʟᴛɪ-ᴘʟᴀʏᴇʀ sᴛʀᴇᴀᴍɪɴɢ ʟɪɴᴋs                           
○ ᴜɴʟɪᴍɪᴛᴇᴅ ᴍᴏᴠɪᴇs & sᴇʀɪᴇs                                                                         
○ ꜰᴜʟʟ ᴀᴅᴍɪɴ sᴜᴘᴘᴏʀᴛ                              
○ ʀᴇǫᴜᴇsᴛ ᴡɪʟʟ ʙᴇ ᴄᴏᴍᴘʟᴇᴛᴇᴅ ɪɴ 1ʜ ɪꜰ ᴀᴠᴀɪʟᴀʙʟᴇ   

✨ ᴜᴘɪ ɪᴅ - <code>aaaayush1230@oksbi</code>

ᴄʟɪᴄᴋ ᴛᴏ ᴄʜᴇᴄᴋ ʏᴏᴜʀ ᴀᴄᴛɪᴠᴇ ᴘʟᴀɴ /myplan

💢 ᴍᴜsᴛ sᴇɴᴅ sᴄʀᴇᴇɴsʜᴏᴛ ᴀғᴛᴇʀ ᴘᴀʏᴍᴇɴᴛ

‼️ ᴀғᴛᴇʀ sᴇɴᴅɪɴɢ ᴀ sᴄʀᴇᴇɴsʜᴏᴛ ᴘʟᴇᴀsᴇ ɢɪᴠᴇ ᴜs sᴏᴍᴇ ᴛɪᴍᴇ ᴛᴏ ᴀᴅᴅ ʏᴏᴜ ɪɴ ᴛʜᴇ ᴘʀᴇᴍɪᴜᴍ ʟɪsᴛ</b>"""

    EARN_TEXT = """<b>🤑 ʜᴏᴡ ᴛᴏ ᴇᴀʀɴ ᴍᴏɴᴇʏ ʙʏ ᴛʜɪs ʙᴏᴛ -

1:- ʏᴏᴜ ʜᴀᴠᴇ ᴀᴛʟᴇᴀsᴛ ᴏɴᴇ ᴍᴏᴠɪᴇ ɢʀᴏᴜᴘ.

2:- ᴍᴀᴋᴇ ᴛʜɪs <a href=https://t.me/{}</a> ᴀᴅᴍɪɴ ɪɴ ʏᴏᴜʀ ɢʀᴏᴜᴘ.

3:- ᴄʀᴇᴀᴛᴇ ᴀᴄᴄᴏᴜɴᴛ ᴏɴ ᴀɴʏ sʜᴏʀᴛɴᴇʀ ʟɪᴋᴇ ʏᴏᴜ ᴄᴀɴ ᴀʟsᴏ ᴜsᴇ ᴛʜɪs ʙᴇsᴛ sʜᴏʀᴛɴᴇʀ <a href=https://tnshort.net>ᴛɴʟɪɴᴋ</a>.

4:- ᴛʜᴇɴ sᴇᴛ ʏᴏᴜʀ sʜᴏʀᴛɴᴇʀ ᴅᴇᴛᴀɪʟs ʙʏ ᴛʜɪs ꜰᴏʀᴍᴀᴛ 👇

<code>/set_shortner tnshort.net 06b24eb6bbb025713cd522fb3f696b6d5de11354</code>

<code>/set_shortner_2 mdiskshortner.link e7beb3c8f756dfa15d0bec495abc65f58c0dfa95</code>

<code>/set_tutorial https://t.me/Aksbackup</code>

5:- ᴀᴅᴅ ʟᴏɢ ᴄʜᴀɴɴᴇʟ ʙʏ ᴛʜɪs ꜰᴏʀᴍᴀᴛ & ᴍᴀᴋᴇ sᴜʀᴇ ʙᴏᴛ ɪs ᴀᴅᴍɪɴ ɪɴ ʏᴏᴜʀ ʟᴏɢ ᴄʜᴀɴɴᴇʟ 👇

<code>/set_log_channel -100*******</code>

ʏᴏᴜ ᴄᴀɴ ᴄʜᴇᴄᴋ ʏᴏᴜʀ ᴀʟʟ ᴅᴇᴛᴀɪʟs ʙʏ /details ᴄᴏᴍᴍᴀɴᴅ

💯 ɴᴏᴛᴇ - <i>ᴛʜɪs ʙᴏᴛ ɪs ꜰʀᴇᴇ ᴛᴏ ᴀʟʟ, ʏᴏᴜ ᴄᴀɴ ᴜsᴇ ᴛʜɪs ʙᴏᴛ ɪɴ ʏᴏᴜʀ ɢʀᴏᴜᴘs ᴀɴᴅ ᴇᴀʀɴ ᴜɴʟɪᴍɪᴛᴇᴅ ᴍᴏɴᴇʏ.</i></b>"""

    VERIFICATION_TEXT = """<b>ʜᴇʏ {} {},

<u>ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴠᴇʀɪғɪᴇᴅ ᴛᴏᴅᴀʏ, ᴘʟᴇᴀꜱᴇ ᴄʟɪᴄᴋ ᴏɴ ᴠᴇʀɪғʏ & ɢᴇᴛ ᴜɴʟɪᴍɪᴛᴇᴅ ᴀᴄᴄᴇꜱꜱ ғᴏʀ ᴛɪʟʟ ɴᴇxᴛ ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ</u>

#ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ:- 1/2

ɪғ ʏᴏᴜ ᴡᴀɴᴛ ᴅɪʀᴇᴄᴛ ғɪʟᴇꜱ ᴡɪᴛʜᴏᴜᴛ ᴀɴʏ ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴꜱ ᴛʜᴇɴ ʙᴜʏ ʙᴏᴛ ꜱᴜʙꜱᴄʀɪᴘᴛɪᴏɴ ☺️

💶 ꜱᴇɴᴅ /plan ᴛᴏ ʙᴜʏ ꜱᴜʙꜱᴄʀɪᴘᴛɪᴏɴ</b>"""

    VERIFY_COMPLETE_TEXT = """<b>ʜᴇʏ {},

ʏᴏᴜ ʜᴀᴠᴇ ᴄᴏᴍᴘʟᴇᴛᴇᴅ ᴛʜᴇ 1st ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ...

ɴᴏᴡ ʏᴏᴜ ʜᴀᴠᴇ ᴜɴʟɪᴍɪᴛᴇᴅ ᴀᴄᴄᴇss ɴᴇxᴛ <code>{}</code> ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ...

ɪғ ʏᴏᴜ ᴡᴀɴᴛ ᴅɪʀᴇᴄᴛ ғɪʟᴇꜱ ᴡɪᴛʜᴏᴜᴛ ᴀɴʏ ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴꜱ ᴛʜᴇɴ ʙᴜʏ ʙᴏᴛ ꜱᴜʙꜱᴄʀɪᴘᴛɪᴏɴ ☺️

💶 ꜱᴇɴᴅ /plan ᴛᴏ ʙᴜʏ ꜱᴜʙꜱᴄʀɪᴘᴛɪᴏɴ</b>"""

    SECOND_VERIFICATION_TEXT = """<b>ʜᴇʏ {} {},

<u>ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴠᴇʀɪꜰɪᴇᴅ ‼️
ᴛᴀᴘ ᴏɴ ᴛʜᴇ ᴠᴇʀɪꜰʏ ʟɪɴᴋ ᴀɴᴅ ɢᴇᴛ ᴜɴʟɪᴍɪᴛᴇᴅ ᴀᴄᴄᴇss ꜰᴏʀ ᴛᴏᴅᴀʏ. 🔋</u>

#ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ:- 2/2

ɪғ ʏᴏᴜ ᴡᴀɴᴛ ᴅɪʀᴇᴄᴛ ғɪʟᴇꜱ ᴡɪᴛʜᴏᴜᴛ ᴀɴʏ ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴꜱ ᴛʜᴇɴ ʙᴜʏ ʙᴏᴛ ꜱᴜʙꜱᴄʀɪᴘᴛɪᴏɴ ☺️

💶 ꜱᴇɴᴅ /plan ᴛᴏ ʙᴜʏ ꜱᴜʙꜱᴄʀɪᴘᴛɪᴏɴ</b>"""

    SECOND_VERIFY_COMPLETE_TEXT = """<b>ʜᴇʏ {},

🤩 ʏᴏᴜ ʜᴀᴠᴇ ᴄᴏᴍᴘʟᴇᴛᴇᴅ ᴛʜᴇ ᴀʟʟ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ...

ɴᴏᴡ ʏᴏᴜ ʜᴀᴠᴇ ᴜɴʟɪᴍɪᴛᴇᴅ ᴀᴄᴄᴇss ꜰᴏʀ ᴏɴᴇ ᴅᴀʏꜱ...

ɪғ ʏᴏᴜ ᴡᴀɴᴛ ᴅɪʀᴇᴄᴛ ғɪʟᴇꜱ ᴡɪᴛʜᴏᴜᴛ ᴀɴʏ ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴꜱ ᴛʜᴇɴ ʙᴜʏ ʙᴏᴛ ꜱᴜʙꜱᴄʀɪᴘᴛɪᴏɴ ☺️

💶 ꜱᴇɴᴅ /plan ᴛᴏ ʙᴜʏ ꜱᴜʙꜱᴄʀɪᴘᴛɪᴏɴ</b>"""

    VERIFIED_LOG_TEXT = """<b><u>☄ ᴜsᴇʀ ᴠᴇʀɪꜰɪᴇᴅ sᴜᴄᴄᴇssꜰᴜʟʟʏ ☄</u>

⚡️ ɴᴀᴍᴇ:- {} [ <code>{}</code> ] 
📆 ᴅᴀᴛᴇ:- <code>{} </code></b>

#verified_{}_completed"""
