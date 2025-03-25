import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path.cwd().joinpath(".env"))

DEVELOPERS_TELEGRAM_ID = os.getenv('DEVELOPERS_TELEGRAM_ID')
DEVELOPERS_TELEGRAM_USERNAME = os.getenv('DEVELOPERS_TELEGRAM_USERNAME')
TELEGRAM_TOKEN   = os.getenv('TELEGRAM_TOKEN')
OPEN_AI_API_KEY  = os.getenv('OPEN_AI_API_KEY')
ASSISTANT_ID     = os.getenv('ASSISTANT_ID')
VECTOR_STORE_ID  = os.getenv('VECTOR_STORE_ID')
DB_LITE          = os.getenv('DB_LITE')
DB_URL           = os.getenv('DB_URL')

# split upload path in case upload directory is like 'uploads/deleted', or 'uploads/admins', etc.
upload_path = os.getenv('DOC_UPLOAD').split('/')
static           = Path("static")

UPLOAD_DIR       = static
DOC_UPLOAD_DIR   = Path.cwd().joinpath(static)
DOC_DOWNLOAD_DIR = Path.cwd().joinpath(static).joinpath(os.getenv('DOC_DOWNLOAD'))
DOC_EXT          = os.getenv('DOC_EXT').split(",")
DOC_MAX_SIZE     = int(os.getenv('DOC_MAX_SIZE'))

for path in upload_path:
    UPLOAD_DIR = UPLOAD_DIR.joinpath(path)
    DOC_UPLOAD_DIR = DOC_UPLOAD_DIR.joinpath(path)
