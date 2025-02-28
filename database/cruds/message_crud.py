import logging

from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Message
from dtos.chat_dto import get_message_from_query_result


async def save_message(session: AsyncSession, message: Message):
    try:
        sql_query = text("""
            INSERT INTO message (text, sender, bot_message_id, reply_to_message_id, chat_id, created_at, updated_at, deleted_at)
            VALUES (:text, :sender, :bot_message_id, :reply_to_message_id, :chat_id, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, NULL)
            RETURNING id, text, sender, bot_message_id, reply_to_message_id, chat_id
        """)
        result = await session.execute(
            sql_query,
            {
                'text': message.text,
                'sender': message.sender,
                'bot_message_id': message.bot_message_id,
                'reply_to_message_id': message.reply_to_message_id,
                'chat_id': message.chat_id
            }
        )
        new_chat = result.fetchone()
        await session.commit()

        if new_chat is None:
            logging.error('Insert query did not return any result!')
            return None

        return get_message_from_query_result(new_chat)
    except Exception as e:
        logging.error(f'Error while saving new message to database. Cause: {e}')
        return None


async def get_message_by_id(session: AsyncSession, message_id: int) -> Message | None:
    query = select(Message).where(Message.id == message_id and Message.deleted_at.is_null())
    message = await session.execute(query)
    return message.scalars().first()