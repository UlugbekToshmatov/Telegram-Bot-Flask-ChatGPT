from datetime import datetime

from sqlalchemy import select, Sequence, update
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import File


async def upload_file(session: AsyncSession, file: File, check_file: bool):
    if check_file:
        db_file = await get_file_by_name(session=session, name=file.name)
        if db_file:
            raise FileExistsError(f'File with name "{file.name}" already exists!')

    session.add(file)
    await session.commit()


async def get_all_files(session: AsyncSession) -> Sequence[File]:
    query = select(File).where(File.deleted_at == None)
    result = await session.execute(query)
    return result.scalars().all()


async def get_file_by_name(session: AsyncSession, name: str) -> File:
    query = select(File).where(File.name == name and File.deleted_at == None)
    result = await session.execute(query)
    return result.scalars().first()


async def get_file_by_id(session: AsyncSession, file_id: int) -> File:
    query = select(File).where(File.id == file_id and File.deleted_at == None)
    result = await session.execute(query)
    return result.scalars().first()


async def delete_file(session: AsyncSession, file_id: int, new_file_name, new_path: str) -> None:
    query = update(File).where(File.id == file_id and File.deleted_at == None).values(
        name=new_file_name,
        path=new_path,
        deleted_at=datetime.now()
    )
    await session.execute(query)
    await session.commit()