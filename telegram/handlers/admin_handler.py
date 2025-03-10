import os.path
from datetime import datetime

from aiogram import Router, F, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message, BufferedInputFile
from sqlalchemy.ext.asyncio import AsyncSession

from configs.config import DOWNLOAD_DIR
from database.cruds.reaction_crud import view_conversations
from telegram.filters.user_types import IsAdmin
from telegram.keyboards.reply_keyboards import get_keyboard
from telegram.uitls.handler_utils import secure_date_time

admin_router = Router()
admin_router.message.filter(IsAdmin())


ADMIN_KEYBOARD = get_keyboard(
    'Savol-javoblarni ko\'rish',
    placeholder='Amaliyot turini tanglang yoki assistent botga savolinggizni yozing:',
    sizes=(1,)
)


@admin_router.message(CommandStart())
async def admin_start_handler(message: Message):
    await message.answer(
        text='Amaliyot turini tanglang yoki assistent botga savolinggizni yozing:',
        reply_markup=ADMIN_KEYBOARD
    )


@admin_router.message(F.text == 'Savol-javoblarni ko\'rish')
async def admin_view_questions_handler(message: Message, session: AsyncSession, bot: Bot):
    await message.answer('***Savol-javoblar ro\'yxati***')

    conversations = await view_conversations(session=session)
    print(conversations)

    # If reports directory does not exist, create it
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)

    report_name = f'report_{secure_date_time(str(datetime.now()))}.txt'

    report_dir = os.path.join(DOWNLOAD_DIR, report_name)

    # Save the conversations to the file
    with open(report_dir, 'w', encoding='utf-8') as file:
        file.write(conversations)

    # Open the file in binary mode and create an InputFile
    with open(report_dir, 'rb') as file:
        file_content = file.read()
        input_file = BufferedInputFile(file=file_content, filename=report_name)  # Pass the file object here

        # Send the document to Telegram
        await bot.send_document(chat_id=message.chat.id, document=input_file)

    # Remove the report file from local storage
    if os.path.exists(report_dir):
        os.remove(report_dir)

    await message.answer('***Savol-javoblar ro\'yxati***')