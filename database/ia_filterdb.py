import logging
from struct import pack
import re
import base64
from pyrogram.file_id import FileId
from pymongo.errors import DuplicateKeyError
from umongo import Instance, Document, fields
from motor.motor_asyncio import AsyncIOMotorClient
from marshmallow.exceptions import ValidationError
# Import all dual-DB config variables
from info import DATABASE_URI1, DATABASE_URI2, DATABASE_NAME1, DATABASE_NAME2, COLLECTION_NAME, MAX_BTN

# ----------------- Dynamic Connection Setup -----------------
# Clients
client1 = AsyncIOMotorClient(DATABASE_URI1)
client2 = AsyncIOMotorClient(DATABASE_URI2)

# Database Objects
db_primary = client1[DATABASE_NAME1]
db_secondary = client2[DATABASE_NAME2]

# Umongo Instance Objects
instance_primary = Instance.from_db(db_primary)
instance_secondary = Instance.from_db(db_secondary)

# Dictionary to select the correct instance/model
DB_INSTANCES = {
    'primary': instance_primary,
    'secondary': instance_secondary
}

# ----------------- Dynamic Document Class -----------------
# Base Class for Schema
class MediaBase(Document):
    file_id = fields.StrField(attribute='_id')
    file_ref = fields.StrField(allow_none=True)
    file_name = fields.StrField(required=True)
    file_size = fields.IntField(required=True)
    mime_type = fields.StrField(allow_none=True)
    caption = fields.StrField(allow_none=True)
    file_type = fields.StrField(allow_none=True)

    class Meta:
        indexes = ('$file_name', )
        collection_name = COLLECTION_NAME

# Register Document Class for both instances
MediaPrimary = instance_primary.register(MediaBase)
MediaSecondary = instance_secondary.register(MediaBase)

# Dictionary to select the correct Document Model
MEDIA_MODELS = {
    'primary': MediaPrimary,
    'secondary': MediaSecondary
}

# Default Model for backward compatibility
Media = MediaPrimary 
# -----------------------------------------------------------


async def get_files_db_size(db_name='primary'):
    """Returns the data size of the specified database."""
    target_db = db_primary if db_name == 'primary' else db_secondary
    return (await target_db.command("dbstats"))['dataSize']
    
async def save_file(media, db_name='primary'):
    """Save file in the specified database (primary or secondary)"""
    # Select the correct model based on db_name
    MediaModel = MEDIA_MODELS.get(db_name, MediaPrimary)
    
    file_id, file_ref = unpack_new_file_id(media.file_id)
    file_name = re.sub(r"(_|\-|\.|\+)", " ", str(media.file_name))
    
    try:
        file = MediaModel(
            file_id=file_id,
            file_ref=file_ref,
            file_name=file_name,
            file_size=media.file_size,
            mime_type=media.mime_type,
            caption=media.caption.html if media.caption else None,
            file_type=media.mime_type.split('/')[0]
        )
    except ValidationError:
        logging.error('Error occurred while saving file in database', exc_info=True)
        return 'err'
    else:
        try:
            await file.commit()
        except DuplicateKeyError:      
            logging.warning(f'{getattr(media, "file_name", "NO_FILE")} is already saved in {db_name} database') 
            return 'dup'
        except Exception as e:
            logging.error(f"Error committing file to {db_name}: {e}", exc_info=True)
            return 'err'
        else:
            logging.info(f'{getattr(media, "file_name", "NO_FILE")} is saved to {db_name} database')
            return 'suc'

async def get_search_results(query, max_results=MAX_BTN, offset=0, lang=None):
    """Search files in BOTH databases and combine results."""
    query = query.strip()
    # Search in Primary DB
    files_primary, _, total_primary = await search_db(query, 'primary', max_results, offset, lang)
    # Search in Secondary DB
    files_secondary, _, total_secondary = await search_db(query, 'secondary', max_results, offset, lang)

    # Combine results
    all_files = files_primary + files_secondary
    total_results = total_primary + total_secondary

    # Since we are combining, pagination needs adjustment or simplification
    # For now, we return the combined list up to max_results and the total count
    next_offset = offset + len(all_files)
    if next_offset >= total_results:
        next_offset = ''

    return all_files[:max_results], next_offset, total_results

async def search_db(query, db_name, max_results, offset, lang):
    """Helper function to search a single database."""
    MediaModel = MEDIA_MODELS.get(db_name)
    if not query:
        raw_pattern = '.'
    elif ' ' not in query:
        raw_pattern = r'(\b|[\.\+\-_])' + query + r'(\b|[\.\+\-_])'
    else:
        raw_pattern = query.replace(' ', r'.*[\s\.\+\-_]')
    
    try:
        regex = re.compile(raw_pattern, flags=re.IGNORECASE)
        filter = {'file_name': regex}
        
        cursor = MediaModel.find(filter).sort('$natural', -1)
        
        if lang:
            lang_files = [file async for file in cursor if lang in file.file_name.lower()]
            files = lang_files[offset:][:max_results]
            total_results = len(lang_files)
        else:
            cursor.skip(offset).limit(max_results)
            files = await cursor.to_list(length=max_results)
            total_results = await MediaModel.count_documents(filter)
            
        next_offset = offset + max_results
        if next_offset >= total_results:
            next_offset = ''
            
        return files, next_offset, total_results
    except:
        return [], 0, 0

    
async def get_bad_files(query, file_type=None, offset=0):
    """Get bad files from BOTH databases."""
    files1, total1 = await search_bad_db(query, 'primary', file_type)
    files2, total2 = await search_bad_db(query, 'secondary', file_type)
    return files1 + files2, total1 + total2

async def search_bad_db(query, db_name, file_type):
    """Helper for get_bad_files."""
    MediaModel = MEDIA_MODELS.get(db_name)
    query = query.strip()
    raw_pattern = query.replace(' ', r'.*[\s\.\+\-_]')
    try:
        regex = re.compile(raw_pattern, flags=re.IGNORECASE)
    except:
        return [], 0
    filter = {'file_name': regex}
    if file_type:
        filter['file_type'] = file_type
    total_results = await MediaModel.count_documents(filter)
    cursor = MediaModel.find(filter).sort('$natural', -1)
    files = await cursor.to_list(length=total_results)
    return files, total_results

async def get_file_details(query):
    """Get file details from primary, fallback to secondary."""
    # First, try to find in the primary database
    file_details = await MEDIA_MODELS['primary'].find_one({'file_id': query})
    if file_details:
        return [file_details]
    
    # If not found, try the secondary database
    file_details_secondary = await MEDIA_MODELS['secondary'].find_one({'file_id': query})
    if file_details_secondary:
        return [file_details_secondary]
        
    # If not found in either, return empty list
    return []

# Utility functions remain the same
def encode_file_id(s: bytes) -> str:
    r = b""
    n = 0
    for i in s + bytes([22]) + bytes([4]):
        if i == 0:
            n += 1
        else:
            if n:
                r += b"\x00" + bytes([n])
                n = 0
            r += bytes([i])
    return base64.urlsafe_b64encode(r).decode().rstrip("=")

def encode_file_ref(file_ref: bytes) -> str:
    return base64.urlsafe_b64encode(file_ref).decode().rstrip("=")

def unpack_new_file_id(new_file_id):
    """Return file_id, file_ref"""
    decoded = FileId.decode(new_file_id)
    file_id = encode_file_id(
        pack(
            "<iiqq",
            int(decoded.file_type),
            decoded.dc_id,
            decoded.media_id,
            decoded.access_hash
        )
    )
    file_ref = encode_file_ref(decoded.file_reference)
    return file_id, file_ref
    