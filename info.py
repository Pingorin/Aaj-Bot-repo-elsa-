import re
import os
from os import environ
from Script import script # Assuming Script.py is accessible

id_pattern = re.compile(r'^.\d+$')
def is_enabled(value, default):
    if not isinstance(value, str): # Ensure value is a string
        return default
    if value.lower() in ["true", "yes", "1", "enable", "y"]:
        return True
    elif value.lower() in ["false", "no", "0", "disable", "n"]:
        return False
    else:
        return default

# --- Main Variables ---
API_ID = int(environ.get('API_ID', '20638104')) # Default values are examples
API_HASH = environ.get('API_HASH', '6c884690ca85d39a4c5ad7c15b194e42')
BOT_TOKEN = environ.get('BOT_TOKEN', '8348689181:AAFj6VO4s6rk5D8HU-tC6oAAgSbRrCD1Se4') # Replace with your actual token
ADMINS = [int(admin) if id_pattern.search(admin) else admin for admin in environ.get('ADMINS', '7245547751').split()] # Replace with your Admin ID(s)
USERNAME = environ.get('USERNAME', 'https://t.me/ramSitaam') # Link to your support
LOG_CHANNEL = int(environ.get('LOG_CHANNEL', '-1003163434752')) # Your main log channel
MOVIE_GROUP_LINK = environ.get('MOVIE_GROUP_LINK', 'https://t.me/+7vxlanrMnWw4N2Fl') # Link to your movie group (optional)
CHANNELS = [int(ch) if id_pattern.search(ch) else ch for ch in environ.get('CHANNELS', '-1002990033841').split()] # Channel(s) to index files from

# --- Database ---
DATABASE_URI = environ.get('DATABASE_URI', "") # Main DB for users, groups etc.
DATABASE_URI2 = environ.get('DATABASE_URI2', "") # DB for files
DATABASE_NAME = environ.get('DATABASE_NAME', "")
COLLECTION_NAME = environ.get('COLLECTION_NAME', '')
LOG_API_CHANNEL = int(environ.get('LOG_API_CHANNEL', '-1001925490938')) # Channel for API/Shortener logs
QR_CODE = environ.get('QR_CODE', 'https://i.ibb.co/ycnxb1CB/x.jpg') # Link to your payment QR code

# --- File-to-Link (Optional, if used) ---
BIN_CHANNEL = int(environ.get('BIN_CHANNEL', '-1003173929836')) # Channel where files are temporarily stored for streaming/download links
URL = environ.get('URL', '') # Your web app URL (Heroku, Render, etc.)

# --- Verification System ---
IS_VERIFY = is_enabled(environ.get('IS_VERIFY', 'True'), True) # Enable/disable verification
LOG_VR_CHANNEL = int(environ.get('LOG_VR_CHANNEL', '-1003179051423')) # Channel to log user verifications
TUTORIAL = environ.get("TUTORIAL", "https://t.me/how_to_dwnload_mov") # Link to verification/download tutorial
VERIFY_IMG = environ.get("VERIFY_IMG", "https://graph.org/file/1669ab9af68eaa62c3ca4.jpg") # Image shown during verification
SHORTENER_API = environ.get("SHORTENER_API", "")
SHORTENER_WEBSITE = environ.get("SHORTENER_WEBSITE", "")
SHORTENER_API2 = environ.get("SHORTENER_API2", "")
SHORTENER_WEBSITE2 = environ.get("SHORTENER_WEBSITE2", "")
TWO_VERIFY_GAP = int(environ.get('TWO_VERIFY_GAP', "600")) # Time gap in seconds (e.g., 1800 = 30 mins) before 2nd verification

# --- Languages & Filters ---
LANGUAGES = ["hindi", "english", "telugu", "tamil", "kannada", "malayalam"] # Add more as needed
QUALITIES = ["480p", "720p", "1080p", "2160p"] # Add/remove qualities as needed

# --- Force Subscribe (Join Request) ---
auth_channel = environ.get('AUTH_CHANNEL', '-1003244733972') # Your primary FSub channel ID
AUTH_CHANNEL = int(auth_channel) if auth_channel and id_pattern.search(auth_channel) else None
SUPPORT_GROUP = int(environ.get('SUPPORT_GROUP', '-1003115990357')) # Your support group ID
JOIN_REQUEST_FSUB = is_enabled(environ.get('JOIN_REQUEST_FSUB', 'True'), True) # Enable first FSub?

# Second Force Subscribe Channel
auth_channel_2 = environ.get('AUTH_CHANNEL_2', '-1003295790341') # Your second FSub channel ID (Optional)
AUTH_CHANNEL_2 = int(auth_channel_2) if auth_channel_2 and id_pattern.search(auth_channel_2) else None
JOIN_REQUEST_FSUB_2 = is_enabled(environ.get('JOIN_REQUEST_FSUB_2', 'True'), True) # Enable second FSub? (Default: False)

# --- Request Feature ---
request_channel = environ.get('REQUEST_CHANNEL', '-1002916715370') # Channel ID for #request feature
REQUEST_CHANNEL = int(request_channel) if request_channel and id_pattern.search(request_channel) else None

# --- Bot Settings ---
IS_PM_SEARCH = is_enabled(environ.get('IS_PM_SEARCH', 'False'), False) # Allow searching in PM?
AUTO_FILTER = is_enabled(environ.get('AUTO_FILTER', 'True'), True) # Enable auto-filter in groups?
PORT = int(environ.get('PORT', '8080')) # Web server port (Render usually sets this automatically)
MAX_BTN = int(environ.get('MAX_BTN', '8')) # Max buttons per page in results
AUTO_DELETE = is_enabled(environ.get('AUTO_DELETE', 'True'), True) # Auto-delete result messages?
DELETE_TIME = int(environ.get('DELETE_TIME', 1200)) # Auto-delete time in seconds (e.g., 1200 = 20 mins)
IMDB = is_enabled(environ.get('IMDB', 'True'), True) # Fetch IMDB info?
FILE_CAPTION = environ.get('FILE_CAPTION', script.FILE_CAPTION) # Default file caption
IMDB_TEMPLATE = environ.get('IMDB_TEMPLATE', script.IMDB_TEMPLATE_TXT) # Default IMDB template
LONG_IMDB_DESCRIPTION = is_enabled(environ.get('LONG_IMDB_DESCRIPTION', 'False'), False) # Use plot outline?
PROTECT_CONTENT = is_enabled(environ.get('PROTECT_CONTENT', 'False'), False) # Use Telegram's forward protection?
SPELL_CHECK = is_enabled(environ.get('SPELL_CHECK', 'True'), True) # Enable spell check suggestions?
LINK_MODE = is_enabled(environ.get('LINK_MODE', 'False'), False) # Show results as links instead of buttons?

# --- Referral System ---
REFERRAL_TARGET = int(environ.get('REFERRAL_TARGET', '10')) # Number of referrals needed
REFERRAL_GROUP_ID = int(environ.get('REFERRAL_GROUP_ID', '-1003196580448')) # Group ID for referral invite links (e.g., Support Group ID)
