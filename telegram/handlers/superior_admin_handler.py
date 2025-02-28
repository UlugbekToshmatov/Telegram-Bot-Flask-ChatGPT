import os
from io import BytesIO

from aiogram import Router, F
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, ReplyKeyboardRemove
from sqlalchemy.ext.asyncio import AsyncSession
from werkzeug.datastructures import FileStorage

from configs.config import UPLOAD_DIR
from database.cruds.file_crud import get_all_files, upload_file
from database.cruds.role_crud import get_role_by_user_tg_id
from database.cruds.user_crud import get_user_by_tg_id
from database.models import File
from enums.telegram_eunms import RoleType
from gpt.ai_assistant import upload_file_to_vector_store
from telegram.filters.user_types import IsSuperiorAdmin
from telegram.handlers.super_admin_handler import SUPER_ADMIN_KEYBOARD
from telegram.keyboards.reply_keyboards import get_keyboard
from telegram.uitls.handler_utils import is_supported_file_type, secure_filename

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
    await message.answer('***Fayllar ro\'yxati***')
    files = await get_all_files(session=session)

    if len(files) == 0:
        await message.answer('Hozircha hech qanday fayl mavjud emas!')
        return

    for file in files:
        await message.answer(f'Fayl nomi: {file.name}\n'
                             f'Fayl turi: {file.content_type}\n'
                             f'Qachon yuklangan: {file.created_at}')

    await message.answer('***Fayllar ro\'yxati***')


@superior_admin_router.message(StateFilter(None), F.text == 'Fayl yuklash')
async def superior_admin_upload_file_handler(message: Message, state: FSMContext):
    # document = await message.document
    # print(document)
    await state.set_state(FileFSM.file_upload)
    await message.answer('Faylni yuklang:', reply_markup=ReplyKeyboardRemove())


@superior_admin_router.message(StateFilter(FileFSM.file_upload), F.content_type == 'document')
async def superior_admin_upload_file_content_handler(message: Message, session: AsyncSession, state: FSMContext):
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

    try:
        # Ensure the uploads directory exists
        if not os.path.exists(UPLOAD_DIR):
            os.makedirs(UPLOAD_DIR)

        # filename = secure_filename(filename=file_name)
        if os.path.exists(os.path.join(UPLOAD_DIR, file_name)):
            await message.answer('Bunday nomli fayl yuklanib bo\'lgan. Iltimos, boshqa faylni yuklang.')
            return

        file_info = await message.bot.get_file(file_id)

        # Download the file content into memory (as a byte stream)
        file_content = await message.bot.download_file(file_info.file_path)

        # Save the file to the UPLOAD_DIR
        file_storage = FileStorage(stream=file_content, filename=file_name, content_type=extension, content_length=file_size)
        file_storage.save(os.path.join(UPLOAD_DIR, file_name))

        # Save the file details to DB
        await upload_file(
            session=session, file=File(
                tg_file_id=file_id,
                name=file_name,
                extension=extension,
                content_type=content_type,
                size=file_size,
                path=os.path.join(UPLOAD_DIR, file_name),
                uploaded_by=message.from_user.id
            ),
            check_file=False
        )

        # Upload the file to OpenAI's Vector Store
        upload_file_to_vector_store(file_storage=file_storage)
    except Exception as e:
        print(e)
        await message.answer('Faylni yuklashda noma\'lum xatolik')
        return

    await state.clear()

    current_user_role = await get_role_by_user_tg_id(session=session, user_tg_id=message.from_user.id)
    if current_user_role.name == RoleType.SUPER_ADMIN.name:
        await message.answer(text='Fayl yuklandi!', reply_markup=SUPER_ADMIN_KEYBOARD)
    else:
        await message.answer(text='Fayl yuklandi!', reply_markup=SUPERIOR_ADMIN_KEYBOARD)


@superior_admin_router.message(StateFilter(FileFSM.file_upload))
async def superior_admin_upload_incorrect_file_content_handler(message: Message):
    await message.answer(text='Iltimos, faylni to\'g\'ri yuklang:')