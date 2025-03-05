import os
from datetime import datetime

from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, ReplyKeyboardRemove, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from werkzeug.datastructures import FileStorage

from configs.config import UPLOAD_DIR
from database.cruds.file_crud import get_all_files, save_file_details, get_file_by_id, delete_file
from database.cruds.role_crud import get_role_by_user_tg_id
from database.models import File
from enums.telegram_eunms import RoleType
from gpt.ai_assistant import upload_file_to_vector_store, delete_file_from_vector_store, upload_file_to_openai
from telegram.filters.user_types import IsSuperiorAdmin
from telegram.handlers.super_admin_handler import SUPER_ADMIN_KEYBOARD
from telegram.keyboards.inline_keyboards import get_inline_buttons
from telegram.keyboards.reply_keyboards import get_keyboard
from telegram.uitls.handler_utils import is_supported_file_type, secure_filename, secure_date_time

superior_admin_router = Router()
superior_admin_router.message.filter(IsSuperiorAdmin())


SUPERIOR_ADMIN_KEYBOARD = get_keyboard(
    'Fayllarni ko\'rish', 'Fayl yuklash',
    'Savol-javoblarni ko\'rish',
    placeholder='Amaliyot turini tanglang yoki assistent botga savolinggizni yozing:',
    sizes=(2, 1)
)


class FileFSM(StatesGroup):
    file_upload = State()


@superior_admin_router.message(CommandStart())
async def superior_admin_start_handler(message: Message):
    await message.answer(
        text='Amaliyot turini tanglang yoki assistent botga savolinggizni yozing:',
        reply_markup=SUPERIOR_ADMIN_KEYBOARD
    )


@superior_admin_router.message(F.text == 'Fayllarni ko\'rish')
async def superior_admin_view_files_handler(message: Message, session: AsyncSession):
    files = await get_all_files(session=session)

    if len(files) == 0:
        await message.answer('Hozirda hech qanday fayl mavjud emas!')
        return

    await message.answer('***Fayllar ro\'yxati***')

    for file in files:
        await message.answer(
            text=f'Fayl nomi: {file.name}\n'
                 f'Fayl turi: {file.content_type}\n'
                 f'Qachon yuklangan: {file.created_at}',
            reply_markup=get_inline_buttons(
                buttons={
                    'Faylni ochib ko\'rish': f'view_file_{file.id}',
                    'Faylni o\'chirish': f'delete_file_{file.id}'
                },
                sizes=(2, 1))
        )

    await message.answer('***Fayllar ro\'yxati***')


@superior_admin_router.callback_query(F.data.startswith('view_file_'))
async def superior_admin_view_file_handler(callback: CallbackQuery, session: AsyncSession):
    try:
        file_id = int(callback.data.split('_')[-1])
        file = await get_file_by_id(session=session, file_id=file_id)

        if file is None:
            await callback.message.answer('Kechirasiz, bunday fayl topilmadi!')
            return

        await callback.bot.send_document(callback.message.chat.id, file.tg_file_id)

    except Exception as e:
        print(f'Error while opening file. Cause: {e}')
        await callback.message.answer('Faylni ochishda xatolik')


@superior_admin_router.callback_query(F.data.startswith('delete_file_'))
async def superior_admin_delete_file_handler(callback: CallbackQuery, session: AsyncSession):
    try:
        file_id = int(callback.data.split('_')[-1])
        file = await get_file_by_id(session=session, file_id=file_id)

        if file is None:
            await callback.message.answer('Kechirasiz, bunday fayl topilmadi!')
            return

        if os.path.exists(file.path):
            new_file_name = f'deleted_at_{secure_date_time(str(datetime.now()))}_{secure_filename(file.name)}'
            new_path = os.path.join(UPLOAD_DIR, new_file_name)

            # Rename the filename to deleted_at_... in local storage
            os.rename(file.path, new_path)

            # Update the file to be deleted in DB
            await delete_file(session=session, file_id=file_id, new_file_name=new_file_name, new_path=new_path)

            # Delete the file from the OpenAI's vector store
            delete_file_from_vector_store(file_id=file.asst_file_id)

            await callback.bot.delete_message(chat_id=callback.message.chat.id, message_id=callback.message.message_id)
            await callback.message.answer('Fayl muvaffaqqiyatli o\'chirildi')
        else:
            await callback.message.answer('Kechirasiz, fayl topilmadi!')

    except Exception as e:
        print(f'Error while deleting file. Cause: {e}')
        await callback.message.answer('Faylni o\'chirishda xatolik')


@superior_admin_router.message(StateFilter(None), F.text == 'Fayl yuklash')
async def superior_admin_upload_file_handler(message: Message, state: FSMContext):
    # document = await message.document
    # print(document)
    await state.set_state(FileFSM.file_upload)
    await message.answer('Faylni yuklang:', reply_markup=ReplyKeyboardRemove())


@superior_admin_router.message(StateFilter(FileFSM.file_upload), F.content_type == 'document')
async def superior_admin_upload_file_content_handler(message: Message, session: AsyncSession, state: FSMContext, bot: Bot):
    file = message.document
    print(file)
    file_id = file.file_id
    file_name = file.file_name
    extension = file_name.split('.')[-1]
    content_type = file.mime_type
    file_size = file.file_size

    if file_size > 104857600:   # 100 MB
        await message.answer('Fayl hajmi juda katta. Iltimos, kichikroq fayl yuklang')
        return

    if is_supported_file_type(file_name) is False:
        await message.answer('Siz noto\'g\'ri formatdagi faylni yukladinggiz. Iltimos, faylni quyidagi formatlardan birida yuklang: '
                             '\'pdf\', \'txt\', \'doc\', \'docx\', \'json\'')
        return

    current_user_role = await get_role_by_user_tg_id(session=session, user_tg_id=message.from_user.id)

    # Checking if user is not none as user's role is needed below
    # In case user is none in DB, they are required to be registered in 'users' table, and /start registers new users
    if current_user_role is None:
        await message.answer('Faylni yuklashda noma\'lum xatolik. Iltimos, /start buyrug\'ini bering.')

    await bot.send_chat_action(message.from_user.id, 'upload_document')

    try:
        # Ensure the uploads directory exists
        if not os.path.exists(UPLOAD_DIR):
            os.makedirs(UPLOAD_DIR)

        file_upload_dir = os.path.join(UPLOAD_DIR, file_name)
        # filename = secure_filename(filename=file_name)
        if os.path.exists(file_upload_dir):
            await message.answer('Bunday nomli fayl yuklanib bo\'lgan. Iltimos, boshqa faylni yuklang.')
            return

        # await message.bot.download(file=file_id, destination=file_upload_dir)

        file_info = await message.bot.get_file(file_id)

        # Download the file content into memory (as a byte stream)
        file_content = await message.bot.download_file(file_info.file_path)

        # Save the file to the UPLOAD_DIR
        file_storage = FileStorage(stream=file_content, filename=file_name, content_type=extension, content_length=file_size)
        file_storage.save(file_upload_dir)

        # Upload file to OpenAI first
        uploaded_file_id = upload_file_to_openai(file_upload_dir)

        # Now attach the file to OpenAI's Vector Store
        batch_id = upload_file_to_vector_store(file_id=uploaded_file_id)

        # Remove the file just saved above from local storage in case of failure while uploading the file to OpenAI
        if uploaded_file_id is None or batch_id is None:
            if os.path.exists(file_upload_dir):
                os.remove(file_upload_dir)

            await state.clear()

            if current_user_role.name == RoleType.SUPER_ADMIN.name:
                await message.answer('Faylni yuklashda noma\'lum xatolik', reply_markup=SUPER_ADMIN_KEYBOARD)
            else:
                await message.answer('Faylni yuklashda noma\'lum xatolik', reply_markup=SUPERIOR_ADMIN_KEYBOARD)
            return

        # Save the file details to DB
        await save_file_details(
            session=session, file=File(
                asst_file_id=uploaded_file_id,
                tg_file_id=file_id,
                name=file_name,
                extension=extension,
                content_type=content_type,
                size=file_size,
                path=file_upload_dir,
                uploaded_by=message.from_user.id
            ),
            check_file=False
        )
    except Exception as e:
        print(e)
        await state.clear()

        if current_user_role.name == RoleType.SUPER_ADMIN.name:
            await message.answer('Faylni yuklashda noma\'lum xatolik', reply_markup=SUPER_ADMIN_KEYBOARD)
        else:
            await message.answer('Faylni yuklashda noma\'lum xatolik', reply_markup=SUPERIOR_ADMIN_KEYBOARD)
        return

    await state.clear()

    if current_user_role.name == RoleType.SUPER_ADMIN.name:
        await message.answer(text='Fayl muvaffaqqiyatli yuklandi!', reply_markup=SUPER_ADMIN_KEYBOARD)
    else:
        await message.answer(text='Fayl muvaffaqqiyatli yuklandi!', reply_markup=SUPERIOR_ADMIN_KEYBOARD)


@superior_admin_router.message(StateFilter(FileFSM.file_upload))
async def superior_admin_upload_incorrect_file_content_handler(message: Message):
    await message.answer(text='Iltimos, faylni to\'g\'ri yuklang:')