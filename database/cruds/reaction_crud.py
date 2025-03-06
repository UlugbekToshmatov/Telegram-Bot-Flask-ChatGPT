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


async def view_conversations(session: AsyncSession):
    sql_query = text("""
        SELECT u.name as user_name, u.surname as user_surname, role.name as role_name, 'Suhbatlar:' as conversation, parent_msg.sender as prompt_sender, parent_msg.text as prompt, child_msg.sender as bot, child_msg.text as bot_response, parent_msg.sender as feedback_sender, rctn.feedback as feedback, rctn.created_at as feedback_time
            FROM reaction rctn
            JOIN message child_msg ON rctn.message_id = child_msg.id
            JOIN message parent_msg ON child_msg.reply_to_message_id=parent_msg.id
            JOIN chat c ON child_msg.chat_id = c.id
            JOIN users u ON c.user_id = u.id
            JOIN role ON u.role_id = role.id
            WHERE u.deleted_at IS NULL AND role.deleted_at IS NULL
    """)

    result = await session.execute(sql_query)
    rows = result.fetchall()

    # Create column headers
    headers = [
        "Foydalanuvchining ismi",
        "Foydalanuvchining sharifi",
        "Foydalanuvchining roli",
        " ",
        "Foydalanuvchi",
        "Murojaat",
        "Assistent",
        "Assistent javobi",
        "Foydalanuvchi",
        "Foydalanuvchining fikri",
        "Fikr bildirilgan vaqt"
    ]

    # Calculate the max length for each column to align the text properly
    max_lengths = [len(header) for header in headers]
    for row in rows:
        for i, value in enumerate(row):
            max_lengths[i] = max(max_lengths[i], len(str(value)))

    # Create a formatted string for the headers
    formatted_results = []
    header_row = " | ".join(f"{header:{max_lengths[i]}}" for i, header in enumerate(headers))
    formatted_results.append(header_row)

    # Create a formatted string for each row
    for row in rows:
        formatted_string = " | ".join(f"{str(value):{max_lengths[i]}}" for i, value in enumerate(row))
        formatted_results.append(formatted_string)

    # Return the formatted output as a string
    return "\n".join(formatted_results)