import re
import os
from os import environ
# FIX: Removed unused imports (enums, asyncio, json, etc.)
from Script import script

# This is the corrected line
id_pattern = re.compile(r'^-?\d+$')
def is_enabled(value, default):
    if value.lower() in ["true", "yes", "1", "enable", "y"]:
        return True
    elif value.lower() in ["false", "no", "0", "disable", "n"]:
        return False
    else:
        return default

#main variables
API_ID = int(environ.get('API_ID', '20638104'))
API_HASH = environ.get('API_HASH', '6c884690ca85d39a4c5ad7c15b194e42')
BOT_TOKEN = environ.get('BOT_TOKEN', '8348689181:AAFj6VO4s6rk5D8HU-tC6oAAgSbRrCD1Se4')
ADMINS = [int(admin) if id_pattern.search(admin) else admin for admin in environ.get('ADMINS', '7245547751').split()]
USERNAME = environ.get('USERNAME', 'https://t.me/ramSitaam')
LOG_CHANNEL = int(environ.get('LOG_CHANNEL', '-1003163434752'))
MOVIE_GROUP_LINK = environ.get('MOVIE_GROUP_LINK', 'https://t.me/+7vxlanrMnWw4N2Fl')
CHANNELS = [int(ch) if id_pattern.search(ch) else ch for ch in environ.get('CHANNELS', '-1002990033841').split()]
DATABASE_URI = environ.get('DATABASE_URI', "")
DATABASE_URI2 = environ.get('DATABASE_URI2', "")
DATABASE_NAME = environ.get('DATABASE_NAME', "")
COLLECTION_NAME = environ.get('COLLECTION_NAME', '')
LOG_API_CHANNEL = int(environ.get('LOG_API_CHANNEL', '-1003173384552'))
QR_CODE = environ.get('QR_CODE', 'https://i.ibb.co/ycnxb1CB/x.jpg')

#this vars is for when heroku or koyeb acc get banned, then change this vars as your file to link bot name
BIN_CHANNEL = int(environ.get('BIN_CHANNEL', '-1003173929836'))
URL = environ.get('URL', '')

# verify system vars
IS_VERIFY = is_enabled('IS_VERIFY', True)
LOG_VR_CHANNEL = int(environ.get('LOG_VR_CHANNEL', '-1003179051423'))
TUTORIAL = environ.get("TUTORIAL", "https://t.me/how_to_dwnload_mov")
VERIFY_IMG = environ.get("VERIFY_IMG", "https://graph.org/file/1669ab9af68eaa62c3ca4.jpg")
SHORTENER_API = environ.get("SHORTENER_API", "")
SHORTENER_WEBSITE = environ.get("SHORTENER_WEBSITE", "")
SHORTENER_API2 = environ.get("SHORTENER_API2", "")
SHORTENER_WEBSITE2 = environ.get("SHORTENER_WEBSITE2", "")
TWO_VERIFY_GAP = int(environ.get('TWO_VERIFY_GAP', "0"))

# languages search
LANGUAGES = ["hindi", "english", "telugu", "tamil", "kannada", "malayalam"]

# quality search
QUALITIES = ["4K", "2160p", "1080p", "720p", "480p", "360p"]

# auth_channel = environ.get('AUTH_CHANNEL', '-1003105162989') # --- OLD F-SUB (COMMENTED OUT)
# AUTH_CHANNEL = int(auth_channel) if auth_channel and id_pattern.search(auth_channel) else None # --- OLD F-SUB (COMMENTED OUT)
SUPPORT_GROUP = int(environ.get('SUPPORT_GROUP', '-1003115990357'))

# --- ADVANCED F-SUB (REQUEST TO JOIN) VARIABLES ---
AUTH_CHANNEL_1 = int(environ.get('AUTH_CHANNEL_1', '-1003295790341')) # Channel 1 ka ID
AUTH_CHANNEL_2 = int(environ.get('AUTH_CHANNEL_2', '-1003105162989')) # Channel 2 ka ID
CHANNEL_1_NAME = environ.get('CHANNEL_1_NAME', 'Channel 1 ka Naam')
CHANNEL_2_NAME = environ.get('CHANNEL_2_NAME', 'Channel 2 ka Naam')
CHANNEL_1_LINK = environ.get('CHANNEL_1_LINK', 'https://t.me/username_ya_link1')
CHANNEL_2_LINK = environ.get('CHANNEL_2_LINK', 'https://t.me/username_ya_link2')
# --- END F-SUB ---

# hastags request features
request_channel = environ.get('REQUEST_CHANNEL', '-1003140956750')
REQUEST_CHANNEL = int(request_channel) if request_channel and id_pattern.search(request_channel) else None

# bot settings
IS_PM_SEARCH = is_enabled('IS_PM_SEARCH', False)
AUTO_FILTER = is_enabled('AUTO_FILTER', True)
PORT = os.environ.get('PORT', '8080')
MAX_BTN = int(environ.get('MAX_BTN', '8'))
AUTO_DELETE = is_enabled('AUTO_DELETE', True)
DELETE_TIME = int(environ.get('DELETE_TIME', 1200))
IMDB = is_enabled('IMDB', False)
FILE_CAPTION = environ.get('FILE_CAPTION', script.FILE_CAPTION) # <-- FIX: Removed unnecessary f-string
IMDB_TEMPLATE = environ.get('IMDB_TEMPLATE', script.IMDB_TEMPLATE_TXT) # <-- FIX: Removed unnecessary f-string
LONG_IMDB_DESCRIPTION = is_enabled('LONG_IMDB_DESCRIPTION', False)
PROTECT_CONTENT = is_enabled('PROTECT_CONTENT', False)
SPELL_CHECK = is_enabled('SPELL_CHECK', True)
LINK_MODE = is_enabled('LINK_MODE', True)

# Add these variables anywhere in your info.py file
REFERRAL_TARGET = 2  # Number of referrals needed for premium
PREMIUM_MONTH_DURATION = 30 # Days of premium to grant
