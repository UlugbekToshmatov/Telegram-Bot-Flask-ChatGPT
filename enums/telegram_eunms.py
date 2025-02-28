from enum import Enum


class UserPrivileges(Enum):
    ASK_QUESTIONS = 'ASK_QUESTIONS'
    VIEW_MESSAGES = 'VIEW_MESSAGES'
    VIEW_FILES = 'VIEW_FILES'
    VIEW_ADMINS = 'VIEW_ADMINS'
    VIEW_ROLES = 'VIEW_ROLES'


class RoleType(Enum):
    USER = 'USER'
    ADMIN = 'ADMIN'
    SUPERIOR_ADMIN = 'SUPERIOR_ADMIN'
    SUPER_ADMIN = 'SUPER_ADMIN'


class SenderType(Enum):
    USER = 'USER'
    BOT = 'BOT'
    ASSISTANT = 'ASSISTANT'


class ChatType(Enum):
    TELEGRAM_API = 'TELEGRAM_API'
    WEB_API = 'WEB_API'