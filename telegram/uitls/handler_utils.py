import re
from UzTransliterator import UzTransliterator

from configs.config import DOC_EXT

greetings = ["assalomu alaykum", "assalomu aleykum", "assalomu alekum", "assalom alekum", "salam alekum",
             "salom alekum", "salom", "qale", "qaley", "qalay", "qanday", "qalesan", "qalesiz", "qaleysan",
             "qalaysan", "qalaysiz", "qandaysan", "qandeysan", "qandaysiz", "qandeysiz", "kimsan", "sen kimsan",
             "san kimsan", "alo", "aloo", "hello"]

leave_takings = ["xayr", "xayir", "hayr", "hayir", "sog' bo'l", "sog bo'l", "sog' bol", "sog' bul", "sog bul"]

commands = [">", "<", "cancel", "adminlarni ko'rish", "admin qo'shish", "fayllarni ko'rish", "fayl yuklash",
            "savol-javoblarni ko'rish", "update_admin_", "choose_role_", "view_file_", "delete_file_",
            "admin_messages", "user_messages", "view_messages_back", "view_messages_for_", "satisfied", "dissatisfied_",
            "feedback_", "continue", "close_message_view"]

PATTERNS = {
    'PASSPORT': r'[A-Za-z]{2}\s?\d{7}',
    'PHONE': r'(?:\+?998[-\s]?|998[-\s]?)\d{2}[-\s]?\d{3}[-\s]?\d{2}[-\s]?\d{2}',
    'CARD_NUMBER': r'\d{4}(?:\s?\d{4}){3}',
}


translator = UzTransliterator.UzTransliterator()

def mask_and_extract_entities(text: str) -> tuple[str, dict]:
    # Mask sensitive information and extract real values
    masked_text = text
    extracted_values = {entity: [] for entity in PATTERNS}

    for entity, pattern in PATTERNS.items():
        matches = re.findall(pattern, masked_text)
        extracted_values[entity].extend(matches)
        masked_text = re.sub(pattern, f'MASK_{entity.upper()}', masked_text)

    return masked_text, extracted_values


def clean_response(assistant_response: str) -> str:
    """Clean AI response from special characters"""
    assistant_response = assistant_response.replace("*", "")
    pattern = r'【[^【】]*?】'
    return re.sub(pattern, '', assistant_response)


def secure_filename(filename: str) -> str:
    return filename.replace(' ', '_')


def secure_date_time(date_time: str) -> str:
    return date_time.replace(' ', '_').replace(':', '-').replace('.', '_')


def is_supported_file_type(filename: str):
    ext = filename.rsplit('.', 1)[1] if "." in filename else ""
    return ext.upper() in DOC_EXT


def contains_cyrillic(text: str) -> bool:
    # Regular expression to match any Cyrillic character (uppercase and lowercase)
    cyrillic_pattern = re.compile('[\u0400-\u04FF]')

    # Search for at least one Cyrillic character in the text
    return bool(cyrillic_pattern.search(text))


def contains_latin(text: str) -> bool:
    # Regular expression to match any Latin character (uppercase and lowercase)
    latin_pattern = re.compile('[\u0041-\u007A]')

    # Search for at least one Latin character in the text
    return bool(latin_pattern.search(text))


def to_latin(text: str) -> str:
    return translator.transliterate(text)


def to_cyrillic(text: str) -> str:
    return translator.transliterate(text=text, from_="lat", to="cyr")