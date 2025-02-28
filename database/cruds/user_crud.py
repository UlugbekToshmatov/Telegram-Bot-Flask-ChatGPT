from datetime import datetime
from typing import Any
import logging

from sqlalchemy import select, update, text
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User
from database.cruds.role_crud import get_role
from dtos.user_dto import UserWithRole, get_user_from_query_result
from enums.telegram_eunms import RoleType


async def add_user(session: AsyncSession, user: User) -> User | None:
    print('Inside add_user function')
    try:
        sql_query = text("""
            INSERT INTO users (tg_id, username, name, surname, password, role_id, created_at, updated_at, deleted_at)
            VALUES (:tg_id, :username, :name, :surname, :password, :role_id, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, NULL)
            RETURNING id, tg_id, username, name, surname, role_id
        """)
        result = await session.execute(
            sql_query,
            {
                'tg_id': user.tg_id,
                'username': user.username,
                'name': user.name,
                'surname': user.surname,
                'password': user.password,
                'role_id': user.role_id
            }
        )
        new_user = result.fetchone()
        # session.add(user)
        await session.commit()

        if new_user is None:
            logging.error('Insert query did not return any result!')
            return None

        return get_user_from_query_result(new_user)
    except Exception as e:
        logging.error(f'Error while adding user to database. Cause: {e}')
        return None


async def get_user(session: AsyncSession, user_id: int) -> User:
    query = select(User).where(User.id == user_id and User.deleted_at.is_null())
    user = await session.execute(query)
    return user.scalars().first()


async def get_user_by_tg_id(session: AsyncSession, tg_id: int) -> User | None:
    query = select(User).where(User.tg_id==tg_id and User.deleted_at.is_null())
    user = await session.execute(query)
    return user.scalars().first()


async def get_user_by_username(session: AsyncSession, username: str) -> User | None:
    query = select(User).where(User.username==username and User.deleted_at.is_null())
    user = await session.execute(query)
    return user.scalars().first()


async def get_all_admins(session: AsyncSession) -> list[UserWithRole]:
    sql_query = text("""
        SELECT u.id, u.tg_id, u.username, u.name, u.surname, r.name as r_name, r.privileges 
        FROM users u JOIN role r ON u.role_id = r.id 
        WHERE r.name!=:role_name AND r.deleted_at IS NULL AND u.tg_id!=341330802
    """)
    result = await session.execute(sql_query, {'role_name': RoleType.USER.name})
    admins: list[UserWithRole] = []

    for admin in result.fetchall():
        admins.append(
            UserWithRole(
                user_id=admin[0],
                user_tg_id=admin[1],
                user_tg_username=admin[2],
                user_name=admin[3],
                user_surname=admin[4],
                role_name=admin[5],
                privileges=str(admin[6]).split(';'),
            )
        )

    return admins


async def get_super_admins(session: AsyncSession) -> list[UserWithRole]:
    sql_query = text("""
        SELECT u.id, u.tg_id, u.username, u.name, u.surname, r.name as role_name, r.privileges 
        FROM users u JOIN role r ON u.role_id = r.id 
        WHERE r.name='SUPER_ADMIN'
    """)
    result = await session.execute(sql_query)
    super_admins: list[UserWithRole] = []

    for super_admin in result.fetchall():
        try:
            super_admins.append(
                UserWithRole(
                    user_id=super_admin[0],
                    user_tg_id=super_admin[1],
                    user_tg_username=super_admin[2],
                    user_name=super_admin[3],
                    user_surname=super_admin[4],
                    role_name=super_admin[5],
                    privileges=str(super_admin[6]).split(';'),
                )
            )
        except KeyError as e:
            print(f"KeyError: {e}, check the query result or the attribute names in UserWithRole")
            pass

    return super_admins


async def update_user(session: AsyncSession, user_id: int, data: dict[str, Any], check_role: bool) -> None:
    if check_role:
        role = get_role(session, data['role_id'])
        if role is None:
            raise Exception(f'Role with id={data["role_id"]} not found')

    query = update(User).where(User.id == user_id and User.deleted_at.is_null()).values(
        username=data['username'],
        name=data['name'],
        surname=data['surname'],
        role_id=data['role_id']
    )
    await session.execute(query)
    await session.commit()


async def delete_user(session: AsyncSession, user_id: int) -> None:
    query = update(User).where(User.id == user_id and User.deleted_at.is_null()).values(
        deleted_at=datetime.now()
    )
    await session.execute(query)
    await session.commit()