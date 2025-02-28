from aiogram.filters import Filter
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User, Role
from database.cruds.role_crud import get_role_by_name, get_role_by_user_tg_id
from database.cruds.user_crud import add_user
from enums.telegram_eunms import UserPrivileges, RoleType


class IsSuperAdmin(Filter):
    def __init__(self) -> None:
        pass

    async def __call__(self, message: Message, session: AsyncSession) -> bool:
        # get session explicitly here as requests come to filters before handlers
        # async with session_maker() as session:
        # get role by user tg id
        role = await get_role_by_user_tg_id(session=session, user_tg_id=message.from_user.id)

        if role is None:
            # if any role is not found by the user tg id, then user with that tg id does not exist yet
            # thus, add the new user with default role 'user'
            await add_new_user(message=message, session=session)
            return False

        else:
            # if role is found, then check if the requesting user has super admin privileges
            return check_privileges(role=role, user_privileges=[UserPrivileges.VIEW_ADMINS])

    # async def __call__(self, message: Message) -> bool:
    #     session = await get_session()
    #     user = await get_user_by_tg_id(session=session, user_tg_id=message.from_user.id)
    #     if user is None:
    #         role = await get_role_by_name(session=session, name='user')
    #         if role is None:
    #             raise Exception('Role by name="user" not found')
    #
    #         await add_user(
    #             session=session, user=User(
    #                 tg_id=message.from_user.id,
    #                 name=message.from_user.first_name,
    #                 role_id=role.id
    #             )
    #         )
    #         return False
    #     else:
    #         privileges = user.role.privileges.split(';')
    #
    #         for privilege in privileges:
    #             if privilege == UserPrivileges.VIEW_ADMINS.name:
    #                 return True
    #
    #         return False


class IsSuperiorAdmin(Filter):
    def __init__(self) -> None:
        pass

    async def __call__(self, message: Message, session: AsyncSession) -> bool:
        # get role by user tg id
        role = await get_role_by_user_tg_id(session=session, user_tg_id=message.from_user.id)

        if role is None:
            # if any role is not found by the user tg id, then user with that tg id does not exist yet
            # thus, add the new user with default role 'user'
            await add_new_user(message=message, session=session)
            return False
        else:
            # if role is found, then check if the requesting user has superior admin privileges
            return check_privileges(role=role, user_privileges=[UserPrivileges.VIEW_FILES, UserPrivileges.VIEW_ADMINS])


async def add_new_user(message: Message, session: AsyncSession) -> None:
    user_role = await get_role_by_name(session=session, name=RoleType.USER.name)
    if user_role is None:
        raise Exception('Role by name="user" not found')

    await add_user(
        session=session,
        user=User(
            tg_id=message.from_user.id,
            name=message.from_user.first_name,
            surname=message.from_user.last_name,
            role_id=user_role.id
        )
    )


def check_privileges(role: Role, user_privileges: list[UserPrivileges]) -> bool:
    privileges = role.privileges.split(';')

    for user_privilege in user_privileges:
        for privilege in privileges:
            if privilege == user_privilege.name:
                return True

    return False