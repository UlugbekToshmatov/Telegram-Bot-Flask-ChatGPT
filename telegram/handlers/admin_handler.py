import os.path
from datetime import datetime

from aiogram import Router, F, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message, BufferedInputFile, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from configs.config import DOWNLOAD_DIR
from database.cruds.reaction_crud import view_conversations
from enums.telegram_eunms import RoleType
from telegram.filters.user_types import IsAdmin
from telegram.keyboards.inline_keyboards import get_inline_buttons
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
async def admin_view_conversations_handler(message: Message):
    await message.answer(
        text='Kimlarning savol-javoblarini ko\'rmoqchisiz',
        reply_markup=get_inline_buttons(
            buttons={
                'Adminlar uchun': 'ADMIN_MESSAGES',
                'Foydalanuvchilar uchun': 'USER_MESSAGES'
            },
            sizes=(1, 1)
        )
    )


@admin_router.callback_query(F.data == 'ADMIN_MESSAGES')
async def view_admin_messages_callback_handler(callback: CallbackQuery):
    await callback.bot.edit_message_text(
        text='Adminlar uchun necha kunlik yozishmalarni ko\'rmoqchisiz',
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id,
        reply_markup=get_inline_buttons(
            buttons={
                '1 kunlik': 'VIEW_MESSAGES_FOR_ADMIN_1',
                '3 kunlik': 'VIEW_MESSAGES_FOR_ADMIN_3',
                '1 haftalik': 'VIEW_MESSAGES_FOR_ADMIN_7',
                'Orqaga': 'VIEW_MESSAGES_BACK',
            },
            sizes=(2, 1, 1)
        )
    )


@admin_router.callback_query(F.data == 'USER_MESSAGES')
async def view_user_messages_callback_handler(callback: CallbackQuery):
    await callback.bot.edit_message_text(
        text='Oddiy foydalanuvchilar uchun necha kunlik yozishmalarni ko\'rmoqchisiz',
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id,
        reply_markup=get_inline_buttons(
            buttons={
                '1 kunlik': 'VIEW_MESSAGES_FOR_USER_1',
                '3 kunlik': 'VIEW_MESSAGES_FOR_USER_3',
                '1 haftalik': 'VIEW_MESSAGES_FOR_USER_7',
                'Orqaga': 'VIEW_MESSAGES_BACK',
            },
            sizes=(2, 1, 1)
        )
    )


@admin_router.callback_query(F.data == 'VIEW_MESSAGES_BACK')
async def view_messages_back_callback_handler(callback: CallbackQuery):
    await callback.bot.edit_message_text(
        text='Kimlarning savol-javoblarini ko\'rmoqchisiz',
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id,
        reply_markup=get_inline_buttons(
            buttons={
                'Adminlar uchun': 'ADMIN_MESSAGES',
                'Foydalanuvchilar uchun': 'USER_MESSAGES'
            },
            sizes=(1, 1)
        )
    )


@admin_router.callback_query(F.data.startswith('VIEW_MESSAGES_FOR_'))
async def admin_view_questions_handler(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    callback_data = callback.data.split('_')
    role = callback_data[-2]
    number_of_days = callback_data[-1]

    try:
        conversations = await view_conversations(session=session, role=role, number_of_days=int(number_of_days))
        print(conversations)

        # If reports directory does not exist, create it
        if not os.path.exists(DOWNLOAD_DIR):
            os.makedirs(DOWNLOAD_DIR)

        if role == RoleType.USER.name:
            report_name = f'users_last_{number_of_days}_days_{secure_date_time(str(datetime.now()))}.txt'
        else:
            report_name = f'admins_last_{number_of_days}_days_{secure_date_time(str(datetime.now()))}.txt'

        report_dir = os.path.join(DOWNLOAD_DIR, report_name)

        # Save the conversations to the file
        with open(report_dir, 'w', encoding='utf-8') as file:
            file.write(conversations)

        # Open the file in binary mode and create an InputFile
        with open(report_dir, 'rb') as file:
            file_content = file.read()
            input_file = BufferedInputFile(file=file_content, filename=report_name)  # Pass the file object here

            # Send the document to Telegram
            await bot.send_document(chat_id=callback.message.chat.id, document=input_file)

        # Remove the report file from local storage
        if os.path.exists(report_dir):
            os.remove(report_dir)
    except Exception as e:
        print(f'Error while getting report: {e}')
        await callback.message.answer('Kechirasiz, savol-javoblarni ko\'rishda tizimda xatolik yuz berdi!')
