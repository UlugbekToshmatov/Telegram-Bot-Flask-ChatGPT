from datetime import datetime
from typing import Sequence

from sqlalchemy import select, update, text, desc
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Role


async def add_roles(session: AsyncSession, roles: list[Role]) -> None:
    session.add_all(roles)
    await session.commit()


async def add_role(session: AsyncSession, role: Role) -> None:
    session.add(role)
    await session.commit()


async def get_roles(session: AsyncSession) -> Sequence[Role]:
    query = select(Role).where(Role.deleted_at == None).order_by(desc(Role.id))
    result = await session.execute(query)
    return result.scalars().all()


async def get_role(session: AsyncSession, role_id: int) -> Role | None:
    query = select(Role).where(Role.id == role_id and Role.deleted_at == None)
    result = await session.execute(query)
    return result.scalars().first()


async def get_role_by_name(session: AsyncSession, name: str) -> Role | None:
    query = select(Role).where(Role.name == name and Role.deleted_at == None)
    role = await session.execute(query)
    return role.scalars().first()


async def get_role_by_user_id(session: AsyncSession, user_id: int) -> Role | None:
    try:
        sql_query = text("""
            SELECT r.id, r.name, r.privileges 
            FROM Role r JOIN Users u ON r.id = u.role_id 
            WHERE u.id = :user_id and u.deleted_at is NULL
        """)
        result = await session.execute(sql_query, {'user_id': user_id})
        role = result.fetchone()  # This returns a single row (tuple) if found
        return Role(id=role.id, name=role.name, privileges=role.privileges)
        # # or
        # roles = result.fetchall()  # This returns all rows as a list of tuples
    except NoResultFound:
        return None


async def get_role_by_user_tg_id(session: AsyncSession, user_tg_id: int) -> Role | None:
    try:
        sql_query = text("""
            SELECT r.id, r.name, r.privileges 
            FROM Role r JOIN Users u ON r.id = u.role_id 
            WHERE u.tg_id = :tg_id and u.deleted_at is NULL
        """)
        result = await session.execute(sql_query, {'tg_id': user_tg_id})
        role = result.fetchone()

        if role is None:
            return None

        return Role(id=role.id, name=role.name, privileges=role.privileges)
    except NoResultFound:
        return None


async def update_role(session: AsyncSession, role_id: int, data: dict[str, str]) -> None:
    query = update(Role).where(Role.id == role_id and Role.deleted_at == None).values(
        name=data['name'],
        permissions=data['permissions']
    )
    await session.execute(query)
    await session.commit()


async def delete_role(session: AsyncSession, role_id: int) -> None:
    query = update(Role).where(Role.id == role_id and Role.deleted_at == None).values(
        deleted_at=datetime.now()
    )
    await session.execute(query)
    await session.commit()