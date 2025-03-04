import re

greetings = ['assalomu alaykum', 'assalomu aleykum', 'assalomu alekum', 'assalom alekum', 'salam alekum',
             'salom alekum', 'salom', 'qale', 'qaley', 'qalay', 'qanday', 'qalesan', 'qalesiz', 'qaleysan',
             'qalaysan', 'qalaysiz', 'qandaysan', 'qandeysan', 'qandaysiz', 'qandeysiz',]

leave_takings = ['xayr', 'xayir', 'hayr', 'hayir', 'sog\' bo\'l', 'sog bo\'l', 'sog\' bul', 'sog bul']

ALLOWED_EXTENSIONS = {'pdf', 'txt', 'doc', 'docx', 'json'}

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
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS