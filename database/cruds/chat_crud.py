import logging

from sqlalchemy import text, update
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Chat
from dtos.chat_dto import get_chat_from_query_result
from enums.telegram_eunms import ChatType


async def create_chat(session: AsyncSession, chat: Chat):
    try:
        sql_query = text("""
            INSERT INTO chat (asst_thread_id, chat_type, user_id, created_at, updated_at, deleted_at)
            VALUES (:asst_thread_id, :chat_type, :user_id, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, NULL)
            RETURNING id, asst_thread_id, chat_type, user_id
        """)
        result = await session.execute(
            sql_query,
            {
                'asst_thread_id': chat.asst_thread_id,
                'chat_type': chat.chat_type,
                'user_id': chat.user_id
            }
        )
        new_chat = result.fetchone()
        await session.commit()

        if new_chat is None:
            logging.error('Insert query did not return any result!')
            return None

        return get_chat_from_query_result(new_chat)
    except Exception as e:
        logging.error(f'Error while creating new chat to database. Cause: {e}')
        return None


# This function is for working with users through telegram bot as chats are created once per day in telegram APIs.
# Use another function to work with web APIs.
async def get_chat_by_user_tg_id(session: AsyncSession, user_tg_id: int) -> Chat | None:
    try:
        sql_query = text("""
            SELECT c.id, c.asst_thread_id, c.chat_type, c.user_id
            FROM chat c
            JOIN users u ON c.user_id = u.id
            WHERE u.tg_id = :user_tg_id
              AND u.deleted_at IS NULL
              AND c.deleted_at IS NULL
              AND c.chat_type = :chat_type
              AND c.created_at >= CURRENT_DATE
              AND c.created_at < CURRENT_DATE + INTERVAL '1 day'
        """)
        result = await session.execute(sql_query, {'user_tg_id': user_tg_id, 'chat_type': ChatType.TELEGRAM_API.name})
        chat = result.fetchone()
        if chat is None:
            return None

        return get_chat_from_query_result(chat)
    except NoResultFound:
        return None


async def update_chat(session: AsyncSession, chat_id: int, data: dict[str, str]) -> None:
    query = update(Chat).where(Chat.id == chat_id and Chat.deleted_at.is_null()).values(
        asst_thread_id=data['asst_thread_id']
    )
    await session.execute(query)
    await session.commit()