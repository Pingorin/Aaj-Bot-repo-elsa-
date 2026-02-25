import re
import os
from os import environ
from pyrogram import enums
from Script import script
import asyncio
import json
from collections import defaultdict
from pyrogram import Client

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
USERNAME = environ.get('USERNAME', 'https://t.me/ramSitm')
LOG_CHANNEL = int(environ.get('LOG_CHANNEL', '-1003163434752'))
MOVIE_GROUP_LINK = environ.get('MOVIE_GROUP_LINK', '')
CHANNELS = [int(ch) if id_pattern.search(ch) else ch for ch in environ.get('CHANNELS', '-1002990033841').split()]
DATABASE_URI = environ.get('DATABASE_URI', "mongodb+srv://Mango5:Mango5@aks2-primary.659ojvs.mongodb.net/?retryWrites=true&w=majority")
DATABASE_URI2 = environ.get('DATABASE_URI2', "mongodb+srv://Rose2:Rose2@aks2-secondary.iybhqc8.mongodb.net/")
DATABASE_URI3 = environ.get('DATABASE_URI3', "mongodb+srv://Catz3:Catz3@naina.qvugkka.mongodb.net/") # <-- YEH NAYI LINE ADD KAREIN 
DATABASE_URI4 = environ.get('DATABASE_URI4', "mongodb+srv://Rosaa12:Rosaa12@rosaa.xhqyqcs.mongodb.net/") # <-- YEH NAYI LINE ADD KAREIN
DATABASE_NAME = environ.get('DATABASE_NAME', "mydatabase")
COLLECTION_NAME = environ.get('COLLECTION_NAME', 'TG_files_movie')
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
# Default time ke liye verification valid rahega (24 hours)
DEFAULT_VERIFY_DURATION = 86400 
# languages search
# --- Verification 3 Settings ---
SHORTENER_WEBSITE3 = ""
SHORTENER_API3 = ""
# Default gap time (in seconds) between V2 and V3 (e.g., 5 minutes)
THIRD_VERIFY_GAP = 300 

LANGUAGES = ["hindi", "english", "telugu", "tamil", "kannada", "malayalam"]

# quality search
QUALITIES = ["4K", "2160p", "1080p", "720p", "480p", "360p"]

auth_channel = environ.get('AUTH_CHANNEL', '-1003105162989')
AUTH_CHANNEL = int(auth_channel) if auth_channel and id_pattern.search(auth_channel) else None

auth_channel_2 = environ.get('AUTH_CHANNEL_2', '-1003295790341') # Yahan apne doosre channel ka ID daalein
AUTH_CHANNEL_2 = int(auth_channel_2) if auth_channel_2 and id_pattern.search(auth_channel_2) else None

# --- YEH BADLAAV HAI ---
# Teesra channel (Normal Fsub)
# Yahan ID ya @username daalein (jaise: -100123... ya '@mychannel')
auth_channel_3 = environ.get('AUTH_CHANNEL_3', '-1002954499406') 
# FIX: ID ko integer mein convert karein agar woh number hai, varna string (jaise @username) rehne dein
AUTH_CHANNEL_3 = int(auth_channel_3) if auth_channel_3 and id_pattern.search(auth_channel_3) else auth_channel_3
# AUTH_CHANNEL_3_INVITE_LINK waali line hata di gayi hai.
# --- YAHAN TAK ---

# --- YEH NAYA CHANNEL ADD KAREIN (Post-Verification FSub) ---
# Yeh channel 'Advanced Fsub' (Request wala) hona chahiye
AUTH_CHANNEL_4 = environ.get('AUTH_CHANNEL_4', '-1003210900437') # Naye channel ka ID daalein
AUTH_CHANNEL_4 = int(AUTH_CHANNEL_4) if AUTH_CHANNEL_4 and id_pattern.search(AUTH_CHANNEL_4) else None
AUTH_CHANNEL_4_TEXT = environ.get('AUTH_CHANNEL_4_TEXT', '✅ Touch me') # Button ka text
# --- YAHAN TAK ---

SUPPORT_GROUP = int(environ.get('SUPPORT_GROUP', '-1003115990357'))

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
FILE_CAPTION = environ.get('FILE_CAPTION', f'{script.FILE_CAPTION}')
IMDB_TEMPLATE = environ.get('IMDB_TEMPLATE', f'{script.IMDB_TEMPLATE_TXT}')
LONG_IMDB_DESCRIPTION = is_enabled('LONG_IMDB_DESCRIPTION', False)
PROTECT_CONTENT = is_enabled('PROTECT_CONTENT', False)
SPELL_CHECK = is_enabled('SPELL_CHECK', True)
LINK_MODE = is_enabled('LINK_MODE', True)

# Add these variables anywhere in your info.py file
REFERRAL_TARGET = 2  # Number of referrals needed for premium
PREMIUM_MONTH_DURATION = 30 # Days of premium to grant
