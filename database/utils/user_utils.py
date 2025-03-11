from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from configs.config import DEVELOPERS_TELEGRAM_ID, DEVELOPERS_TELEGRAM_USERNAME
from database.cruds.chat_crud import get_chat_by_user_tg_id, create_chat
from database.models import User, Chat
from database.cruds.role_crud import get_role_by_name
from database.cruds.user_crud import get_super_admins, add_user, get_user_by_tg_id, get_user_by_username, update_user
from dtos.user_dto import get_user_from_message
from enums.telegram_eunms import RoleType, ChatType


async def add_initial_super_admin(session: AsyncSession):
    super_admins = await get_super_admins(session=session)
    if super_admins.__len__() == 0:
        super_admin_role = await get_role_by_name(session=session, name=RoleType.SUPER_ADMIN.name)
        if super_admin_role is None:
            raise Exception('Super admin role not found')

        await add_user(
            session=session,
            user=User(
                tg_id=int(DEVELOPERS_TELEGRAM_ID),
                username=DEVELOPERS_TELEGRAM_USERNAME,
                name='online',
                password='@On1ineNowW123',
                role_id=super_admin_role.id,
            )
        )


async def save_user_and_create_chat(session: AsyncSession, message: Message) -> dict[str, User | Chat]:
    # Get (one) chat by user tg id. User may be requesting via telegram for the first time.
    chat = await get_chat_by_user_tg_id(session=session, user_tg_id=message.from_user.id)
    print(f'Chat: {chat}')

    # Get user by tg id. If not exists, create one.
    user = await get_user_by_tg_id(session=session, tg_id=message.from_user.id)
    print(f'User: {user.__str__()}')
    if user is None:
        role = await get_role_by_name(session=session, name=RoleType.USER.name)
        print(f'Role: {role}')
        if role is None:
            print('Role is empty, and thus, raising exception')
            raise Exception('Kechirasiz, tizimda xatolik yuz berdi!')
            # await message.answer('Kechirasiz, tizimda xatolik yuz berdi!')
            # return

        user = get_user_from_message(message, role)

        if user.username is not None:
            user_with_username = await get_user_by_username(session=session, username=user.username)

            # Check if the newly requesting user's username is not possessed by someone else in DB. If user with that
            # username is not None, then super admin must have provided that username incorrectly while adding new
            # admin. Thus, setting the username to its real owner by removing it from admin is the correct way here.
            if user_with_username is not None:
                print(f'Removing username "{user_with_username.username}" from user with id={user_with_username.id} '
                      f'to avoid unique constraint violation while saving new user, who is the real owner of the username')
                await update_user(
                    session=session,
                    user_id=user_with_username.id,
                    data={
                        'username': None,
                        'name': user_with_username.name,
                        'surname': user_with_username.surname,
                        'role_id': user_with_username.role_id
                    },
                    check_role=False
                )

        user = await add_user(session=session, user=user)
        if user is None:
            print('User is empty after add_user function call, and thus, raising exception')
            raise Exception('Kechirasiz, foydalanuvchini qo\'shishda xatolik yuz berdi!')
            # await message.answer('Kechirasiz, foydalanuvchini qo\'shishda xatolik yuz berdi!')
            # return

        # If user is new here, then obviously they have no any chat. So, create one for them.
        chat = await create_chat(
            session=session,
            chat=Chat(chat_type=ChatType.TELEGRAM_API.name, user_id=user.id)
        )
        print(f'Created new chat after adding new user. Chat: {chat}')

    # In case user already exists, but did not write to bot before, create chat for them
    if chat is None:
        chat = await create_chat(session=session, chat=Chat(chat_type=ChatType.TELEGRAM_API.name, user_id=user.id))
        print(f'User already existed, and creating new chat for them. Chat: {chat}')

    return {'user': user, 'chat': chat}
