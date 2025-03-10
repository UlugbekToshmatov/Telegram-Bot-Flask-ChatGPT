import logging
import os
from dotenv import load_dotenv

load_dotenv('C:/Users/Ulugbek/Desktop/MyWorks/Python/Practice/ChatGPT-Bot/.env')

TELEGRAM_TOKEN: str = os.getenv('TELEGRAM_TOKEN')
OPEN_AI_API_KEY = os.getenv('OPEN_AI_API_KEY')
ASSISTANT_ID = os.getenv('ASSISTANT_ID')
VECTOR_STORE_ID = os.getenv('VECTOR_STORE_ID')
DB_LITE = os.getenv('DB_LITE')
DB_URL = os.getenv('DB_URL')
DEVELOPERS_TELEGRAM_ID = os.getenv('DEVELOPERS_TELEGRAM_ID')
DEVELOPERS_TELEGRAM_USERNAME = os.getenv('DEVELOPERS_TELEGRAM_USERNAME')

UPLOAD_DIR = os.path.join('static', 'uploads')
DOWNLOAD_DIR = os.path.join('static', 'downloads')

# logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)