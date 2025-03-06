from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.cruds.reaction_crud import view_conversations
from telegram.filters.user_types import IsAdmin
from telegram.keyboards.reply_keyboards import get_keyboard

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
async def admin_view_questions_handler(message: Message, session: AsyncSession):
    await message.answer('***Savol-javoblar ro\'yxati***')
    conversations = await view_conversations(session=session)
    print(conversations)
    await message.answer(conversations)
    await message.answer('Ushbu ro\'yxatni yaxshilangan formatda ko\'rish uchun, iltimos, ro\'yxatni .txt formatdagi faylga ko\'chiring')
    await message.answer('***Savol-javoblar ro\'yxati***')