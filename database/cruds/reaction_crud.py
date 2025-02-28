from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Reaction


async def save_dissatisfaction(session: AsyncSession, message_id: int):
    reaction = Reaction(satisfied=False, message_id=message_id)
    session.add(reaction)
    await session.commit()


async def save_dissatisfaction_feedback(session: AsyncSession, message_id: int, feedback: str):
    sql_query = text("""
        UPDATE reaction
        SET feedback = :feedback
        WHERE message_id = :message_id AND deleted_at IS NULL
    """)
    await session.execute(sql_query, {'feedback': feedback, 'message_id': message_id})
    await session.commit()