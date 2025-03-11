from aiogram.types import Message

from database.models import User, Role


def get_user_from_message(message: Message, role: Role):
    return User(
        tg_id=message.from_user.id,
        username=f'@{message.from_user.username}' if message.from_user.username is not None else None,
        name=message.from_user.first_name,
        surname=message.from_user.last_name,
        password='adil456',
        role_id=role.id,
    )


def get_user_from_query_result(user):
    return User(
        id=user[0],
        tg_id=user[1],
        username=user[2],
        name=user[3],
        surname=user[4],
        role_id=user[5],
    )


class UserWithRole:
    def __init__(self, user_id: int, user_tg_id: str, user_tg_username: str, user_name: str, user_surname: str, role_name: str, privileges: list[str]):
        self.user_id = user_id
        self.user_tg_id = user_tg_id
        self.user_tg_username = user_tg_username
        self.user_name = user_name
        self.user_surname = user_surname
        self.role_name = role_name
        self.privileges = privileges


class RoleWithUserId:
    def __init__(self, user_id: int, role_id: int, role_name: str, privileges: str):
        self.user_id = user_id
        self.role_id = role_id
        self.role_name = role_name
        self.privileges = privileges