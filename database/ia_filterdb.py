import logging
from struct import pack
import re
import base64
from pyrogram.file_id import FileId
from pymongo.errors import DuplicateKeyError
from umongo import Instance, Document, fields
from motor.motor_asyncio import AsyncIOMotorClient
from marshmallow.exceptions import ValidationError
from info import DATABASE_URI2, DATABASE_NAME, COLLECTION_NAME, MAX_BTN

client = AsyncIOMotorClient(DATABASE_URI2)
mydb = client[DATABASE_NAME]
instance = Instance.from_db(mydb)

@instance.register
class Media(Document):
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

async def get_files_db_size():
    return (await mydb.command("dbstats"))['dataSize']
    
async def save_file(media):
    """Save file in database"""

    # TODO: Find better way to get same file_id for same media to avoid duplicates
    file_id, file_ref = unpack_new_file_id(media.file_id)
    file_name = re.sub(r"(_|\-|\.|\+)", " ", str(media.file_name))
    try:
        file = Media(
            file_id=file_id,
            file_ref=file_ref,
            file_name=file_name,
            file_size=media.file_size,
            mime_type=media.mime_type,
            caption=media.caption.html if media.caption else None,
            file_type=media.mime_type.split('/')[0]
        )
    except ValidationError:
        print('Error occurred while saving file in database')
        return 'err'
    else:
        try:
            await file.commit()
        except DuplicateKeyError:      
            print(f'{getattr(media, "file_name", "NO_FILE")} is already saved in database') 
            return 'dup'
        else:
            print(f'{getattr(media, "file_name", "NO_FILE")} is saved to database')
            return 'suc'

async def get_search_results(query, max_results=MAX_BTN, offset=0, lang=None, quality=None, year=None, extract_years=False, year_extract_limit=100):
    query = query.strip()
    # Basic query regex
    if not query:
        raw_pattern = '.'
    elif ' ' not in query:
        # Match word boundaries more reliably for single words
        raw_pattern = r'(?:^|\W|\b)' + re.escape(query) + r'(?:$|\W|\b)'
    else:
        # Allow spaces or dots/hyphens/underscores between words
        raw_pattern = r'\b' + query.replace(' ', r'.*[\s.\-_\+].*') + r'\b'

    try:
        regex = re.compile(raw_pattern, flags=re.IGNORECASE)
    except Exception as e:
        logging.error(f"Regex compilation failed for '{raw_pattern}': {e}")
        # Fallback to simple contains check if regex fails (less accurate)
        filter_query = {'file_name': {'$regex': re.escape(query), '$options': 'i'}}
        regex = None # Indicate regex failed
    else:
        filter_query = {'file_name': regex}

    # --- Initial Fetch for Year Extraction (if requested) ---
    unique_years = []
    if extract_years:
        cursor_for_years = Media.find(filter_query).limit(year_extract_limit)
        found_years = set()
        year_pattern = re.compile(r'\b(19[89]\d|20[0-3]\d)\b') # Find years 1980-2039
        async for file in cursor_for_years:
            matches = year_pattern.findall(file.file_name)
            if matches:
                found_years.update(matches) # Add all found years to the set
        if found_years:
            # Sort years numerically, descending
            unique_years = sorted(list(found_years), key=int, reverse=True)

    # --- Main Query & Filtering ---
    cursor = Media.find(filter_query)
    cursor.sort('$natural', -1) # Sort newest first generally

    # Apply filters iteratively in Python (more flexible than complex DB queries)
    filtered_files = []
    async for file in cursor:
        file_name_lower = file.file_name.lower()
        
        # Year Filter
        if year and not re.search(r'\b' + re.escape(str(year)) + r'\b', file.file_name):
            continue # Skip if year doesn't match
            
        # Quality Filter
        if quality and not re.search(r'\b' + re.escape(quality.strip()) + r'\b', file_name_lower):
            continue # Skip if quality doesn't match
            
        # Language Filter
        if lang and not re.search(r'\b' + re.escape(lang.strip()) + r'\b', file_name_lower):
             continue # Skip if language doesn't match

        filtered_files.append(file)

    # --- Pagination ---
    total_results = len(filtered_files)
    files_on_page = filtered_files[offset : offset + max_results]
    
    next_offset = offset + max_results
    if next_offset >= total_results:
        next_offset = '' # No more pages

    # Return extracted years only if requested initially
    return files_on_page, next_offset, total_results, (unique_years if extract_years else None)

async def get_bad_files(query, file_type=None, offset=0, filter=False):
    query = query.strip()
    if not query:
        raw_pattern = '.'
    elif ' ' not in query:
        raw_pattern = r'(\b|[\.\+\-_])' + query + r'(\b|[\.\+\-_])'
    else:
        raw_pattern = query.replace(' ', r'.*[\s\.\+\-_]')
    try:
        regex = re.compile(raw_pattern, flags=re.IGNORECASE)
    except:
        return []
    filter = {'file_name': regex}
    if file_type:
        filter['file_type'] = file_type
    total_results = await Media.count_documents(filter)
    cursor = Media.find(filter)
    cursor.sort('$natural', -1)
    files = await cursor.to_list(length=total_results)
    return files, total_results
    
async def get_file_details(query):
    filter = {'file_id': query}
    cursor = Media.find(filter)
    filedetails = await cursor.to_list(length=1)
    return filedetails

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
    
