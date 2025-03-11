from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Reaction
from enums.telegram_eunms import RoleType


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


async def view_conversations(session: AsyncSession, role: str, number_of_days: int):
    if not isinstance(number_of_days, int):
        raise ValueError("number_of_days must be an integer")
    if number_of_days < 0:
        raise ValueError("number_of_days must be a non-negative number")

    if role == RoleType.USER.name:
        sql_query = text("""
            SELECT u.name as user_name, u.surname as user_surname, role.name as role_name, 'Suhbatlar:' as conversation, parent_msg.sender as prompt_sender, parent_msg.text as prompt, child_msg.sender as bot, child_msg.text as bot_response, parent_msg.sender as feedback_sender, rctn.feedback as feedback, rctn.created_at as feedback_time
                FROM reaction rctn
                JOIN message child_msg ON rctn.message_id = child_msg.id
                JOIN message parent_msg ON child_msg.reply_to_message_id=parent_msg.id
                JOIN chat c ON child_msg.chat_id = c.id
                JOIN users u ON c.user_id = u.id
                JOIN role ON u.role_id = role.id
                WHERE role.name = 'USER'
                    AND rctn.created_at >= CURRENT_DATE - INTERVAL '1 day' * (:days - 1) 
                    AND rctn.created_at < CURRENT_DATE + INTERVAL '1 day' 
                    AND u.deleted_at IS NULL
                    AND role.deleted_at IS NULL
        """)
    else:
        sql_query = text("""
            SELECT u.name as user_name, u.surname as user_surname, role.name as role_name, 'Suhbatlar:' as conversation, parent_msg.sender as prompt_sender, parent_msg.text as prompt, child_msg.sender as bot, child_msg.text as bot_response, parent_msg.sender as feedback_sender, rctn.feedback as feedback, rctn.created_at as feedback_time
                FROM reaction rctn
                JOIN message child_msg ON rctn.message_id = child_msg.id
                JOIN message parent_msg ON child_msg.reply_to_message_id=parent_msg.id
                JOIN chat c ON child_msg.chat_id = c.id
                JOIN users u ON c.user_id = u.id
                JOIN role ON u.role_id = role.id
                WHERE role.name <> 'USER'
                    AND rctn.created_at >= CURRENT_DATE - INTERVAL '1 day' * (:days - 1) 
                    AND rctn.created_at < CURRENT_DATE + INTERVAL '1 day' 
                    AND u.deleted_at IS NULL
                    AND role.deleted_at IS NULL
        """)

    result = await session.execute(sql_query, {'days': number_of_days})
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

    # # --- SQL Expression Language (Recommended) ---
    # # from sqlalchemy import column, table
    #
    # rctn = table("reaction", column("message_id"), column("feedback"), column("created_at"))
    # child_msg = table("message", column("id"), column("reply_to_message_id"), column("chat_id"), column("sender"),
    #                   column("text"))
    # parent_msg = table("message", column("id"), column("sender"), column("text"))
    # chat = table("chat", column("id"), column("user_id"))
    # users = table("users", column("id"), column("role_id"), column("name"), column("surname"), column("deleted_at"))
    # role_table = table("role", column("id"), column("name"), column("deleted_at"))
    # # Create the dynamic interval string for period_of_time
    # interval_expr = f"INTERVAL '{number_of_days} days'"
    #
    # query = select(
    #     users.c.name.label("user_name"),
    #     users.c.surname.label("user_surname"),
    #     role_table.c.name.label("role_name"),
    #     literal_column("'Suhbatlar:'").label("conversation"),
    #     parent_msg.c.sender.label("prompt_sender"),
    #     parent_msg.c.text.label("prompt"),
    #     child_msg.c.sender.label("bot"),
    #     child_msg.c.text.label("bot_response"),
    #     parent_msg.c.sender.label("feedback_sender"),
    #     rctn.c.feedback.label("feedback"),
    #     rctn.c.created_at.label("feedback_time")
    # ).select_from(
    #     rctn
    #     .join(child_msg, rctn.c.message_id == child_msg.c.id)
    #     .join(parent_msg, child_msg.c.reply_to_message_id == parent_msg.c.id)
    #     .join(chat, child_msg.c.chat_id == chat.c.id)
    #     .join(users, chat.c.user_id == users.c.id)
    #     .join(role_table, users.c.role_id == role_table.c.id)
    # ).where(role_table.c.name != 'USER' if role != RoleType.USER.name else role_table.c.name == 'USER') \
    #     .where(rctn.c.created_at >= func.current_date() - text(interval_expr)) \
    #     .where(rctn.c.created_at < func.current_date() + func.make_interval(days=1)) \
    #     .where(users.c.deleted_at == None) \
    #     .where(role_table.c.deleted_at == None)
    #
    # result = await session.execute(query)
    # rows = result.fetchall()
    #
    # # Create column headers
    # headers = [
    #     "Foydalanuvchining ismi",
    #     "Foydalanuvchining sharifi",
    #     "Foydalanuvchining roli",
    #     " ",
    #     "Foydalanuvchi",
    #     "Murojaat",
    #     "Assistent",
    #     "Assistent javobi",
    #     "Foydalanuvchi",
    #     "Foydalanuvchining fikri",
    #     "Fikr bildirilgan vaqt"
    # ]
    #
    # # Calculate the max length for each column to align the text properly
    # max_lengths = [len(header) for header in headers]
    # for row in rows:
    #     for i, value in enumerate(row):
    #         max_lengths[i] = max(max_lengths[i], len(str(value)))
    #
    # # Create a formatted string for the headers
    # formatted_results = []
    # header_row = " | ".join(f"{header:{max_lengths[i]}}" for i, header in enumerate(headers))
    # formatted_results.append(header_row)
    #
    # # Create a formatted string for each row
    # for row in rows:
    #     formatted_string = " | ".join(f"{str(value):{max_lengths[i]}}" for i, value in enumerate(row))
    #     formatted_results.append(formatted_string)
    #
    # # Return the formatted output as a string
    # return "\n".join(formatted_results)