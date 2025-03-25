import re
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