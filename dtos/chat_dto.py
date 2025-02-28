from database.models import Chat, Message


def get_chat_from_query_result(chat):
    return Chat(
        id=chat[0],
        asst_thread_id=chat[1],
        chat_type=chat[2],
        user_id=chat[3]
    )


def get_message_from_query_result(message):
    return Message(
        id=message[0],
        text=message[1],
        sender=message[2],
        reply_to_message_id=message[3],
        chat_id=message[4]
    )