from datetime import datetime
from pathlib import Path

from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, ReplyKeyboardRemove, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from configs.config import DOC_UPLOAD_DIR, DOC_MAX_SIZE, DOC_EXT, UPLOAD_DIR
from database.cruds.file_crud import get_all_files, save_file_details, get_file_by_id, delete_file
from database.cruds.role_crud import get_role_by_user_tg_id
from database.cruds.user_crud import get_user_by_tg_id
from database.models import File
from enums.telegram_eunms import RoleType
from gpt.open_ai_assistant import upload_file_to_vector_store, delete_file_from_vector_store, upload_file_to_openai, \
    delete_file_from_openai
from telegram.filters.user_types import IsSuperiorAdmin
from telegram.handlers.super_admin_handler import SUPER_ADMIN_KEYBOARD
from telegram.keyboards.inline_keyboards import get_inline_buttons
from telegram.keyboards.reply_keyboards import get_keyboard
from telegram.uitls.handler_utils import is_supported_file_type, secure_filename, secure_date_time

superior_admin_router = Router()
superior_admin_router.message.filter(IsSuperiorAdmin())


SUPERIOR_ADMIN_KEYBOARD = get_keyboard(
    "Fayllarni ko'rish", "Fayl yuklash",
    "Savol-javoblarni ko'rish",
    placeholder="Amaliyot turini tanglang yoki assistent botga savolinggizni yozing:",
    sizes=(2, 1)
)


class FileFSM(StatesGroup):
    file_upload = State()


@superior_admin_router.message(CommandStart())
async def superior_admin_start_handler(message: Message, state: FSMContext):
    state_data = await state.get_data()
    if state_data is not None:
        await state.clear()

    await message.answer(
        text='Amaliyot turini tanglang yoki assistent botga savolinggizni yozing:',
        reply_markup=SUPERIOR_ADMIN_KEYBOARD
    )


@superior_admin_router.message(StateFilter('*'), F.text.lower() == 'cancel')
async def superior_admin_cancel_operation_handler(message: Message, session: AsyncSession, state: FSMContext) -> None:
    current_state = await state.get_state()

    if current_state is None:
        await message.answer(
            text='Bekor qilish uchun siz hali fayl yuklash amaliyotini boshlamadinggiz!',
            reply_markup=SUPERIOR_ADMIN_KEYBOARD
        )
        return
    elif current_state == 'FileFSM:file_upload':
        await message.answer(text='Fayl yuklash bekor qilindi', reply_markup=SUPERIOR_ADMIN_KEYBOARD)
    else:
        await message.answer(text='Amaliyot bekor qilindi', reply_markup=SUPERIOR_ADMIN_KEYBOARD)

    await state.clear()


@superior_admin_router.message(F.text == "Fayllarni ko'rish")
async def superior_admin_view_files_handler(message: Message, session: AsyncSession):
    files = await get_all_files(session=session)

    if len(files) == 0:
        await message.answer('Hozirda hech qanday fayl mavjud emas!')
        return

    await message.answer("***Fayllar ro'yxati***")

    for file in files:
        await message.answer(
            text=f'Fayl nomi: {file.name}\n'
                 f'Fayl turi: {file.content_type}\n'
                 f'Qachon yuklangan: {file.created_at}',
            reply_markup=get_inline_buttons(
                buttons={
                    "Faylni ochib ko'rish": f'view_file_{file.id}',
                    "Faylni o'chirish": f'delete_file_{file.id}'
                },
                sizes=(2, 1))
        )

    await message.answer("***Fayllar ro'yxati***")


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

        if Path(file.path).exists():
            new_file_name = f'deleted_at_{secure_date_time(str(datetime.now()))}_{secure_filename(file.name)}'
            new_path = DOC_UPLOAD_DIR.joinpath(new_file_name)

            # Rename the filename to deleted_at_... in local storage
            Path(file.path).rename(UPLOAD_DIR.joinpath(new_file_name))

            print(f'Callback data: {callback}')

            # Get current user id to indicate who is deleting the file
            current_user = await get_user_by_tg_id(session=session, tg_id=callback.from_user.id)

            print(f'Current user: {current_user}')

            # Update the file to be deleted in DB
            await delete_file(
                session=session,
                params={'user_id': current_user.id, 'file_id': file_id, 'new_file_name': new_file_name, 'new_path': UPLOAD_DIR.joinpath(new_path.name).__str__()}
            )

            # Detach the file from the OpenAI's vector store
            delete_file_from_vector_store(file_id=file.asst_file_id)

            # Delete the file from OpenAI itself
            delete_file_from_openai(file_id=file.asst_file_id)

            await callback.bot.delete_message(chat_id=callback.message.chat.id, message_id=callback.message.message_id)
            await callback.message.answer("Fayl muvaffaqqiyatli o'chirildi")
        else:
            await callback.message.answer('Kechirasiz, fayl topilmadi!')

    except Exception as e:
        print(f'Error while deleting file. Cause: {e}')
        await callback.message.answer("Faylni o'chirishda xatolik")


@superior_admin_router.message(StateFilter(None), F.text == 'Fayl yuklash')
async def superior_admin_upload_file_handler(message: Message, state: FSMContext):
    await message.answer(
        text='Yangi faylni serverga yuklashda\n'
             'amaliyotni bekor qilish uchun "cancel" so\'zini\n'
             'kiritishinggiz mumkin',
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(FileFSM.file_upload)
    await message.answer('Faylni yuklang:')


# @superior_admin_router.message(StateFilter(FileFSM.file_upload), F.content_type == 'document')
# async def superior_admin_upload_file_content_handler(message: Message, session: AsyncSession, state: FSMContext, bot: Bot):
#     file = message.document
#     print(file)
#     file_id = file.file_id
#     file_name = file.file_name
#     extension = file_name.split('.')[-1]
#     content_type = file.mime_type
#     file_size = file.file_size
#
#     if file_size > 104857600:   # 100 MB
#         await message.answer('Fayl hajmi juda katta. Iltimos, kichikroq fayl yuklang')
#         return
#
#     if is_supported_file_type(file_name) is False:
#         await message.answer('Siz noto\'g\'ri formatdagi faylni yukladinggiz. Iltimos, faylni quyidagi formatlardan birida yuklang: '
#                              '\'pdf\', \'txt\', \'doc\', \'docx\', \'json\'')
#         return
#
#     current_user_role = await get_role_by_user_tg_id(session=session, user_tg_id=message.from_user.id)
#
#     # Checking if user is not none as user's role is needed below
#     # In case user is none in DB, they are required to be registered in 'users' table, and /start registers new users
#     if current_user_role is None:
#         await message.answer('Faylni yuklashda noma\'lum xatolik. Iltimos, /start buyrug\'ini bering.')
#
#     await bot.send_chat_action(message.from_user.id, 'upload_document')
#
#     try:
#         # Ensure the uploads directory exists
#         if not os.path.exists(UPLOAD_DIR):
#             os.makedirs(UPLOAD_DIR)
#
#         file_upload_dir = os.path.join(UPLOAD_DIR, file_name)
#         # filename = secure_filename(filename=file_name)
#         if os.path.exists(file_upload_dir):
#             await message.answer('Bunday nomli fayl yuklanib bo\'lgan. Iltimos, boshqa faylni yuklang.')
#             return
#
#         # await message.bot.download(file=file_id, destination=file_upload_dir)
#
#         file_info = await message.bot.get_file(file_id)
#
#         # Download the file content into memory (as a byte stream)
#         file_content = await message.bot.download_file(file_info.file_path)
#
#         # Save the file to the UPLOAD_DIR
#         file_storage = FileStorage(stream=file_content, filename=file_name, content_type=extension, content_length=file_size)
#         file_storage.save(file_upload_dir)
#
#         # Upload file to OpenAI first
#         uploaded_file_id = upload_file_to_openai(file_upload_dir)
#
#         # Now attach the file to OpenAI's Vector Store
#         batch_id = upload_file_to_vector_store(file_id=uploaded_file_id)
#
#         # Remove the file just saved above from local storage in case of failure while uploading the file to OpenAI
#         if uploaded_file_id is None or batch_id is None:
#             if os.path.exists(file_upload_dir):
#                 os.remove(file_upload_dir)
#
#             await state.clear()
#
#             if current_user_role.role_name == RoleType.SUPER_ADMIN.name:
#                 await message.answer('Faylni yuklashda noma\'lum xatolik', reply_markup=SUPER_ADMIN_KEYBOARD)
#             else:
#                 await message.answer('Faylni yuklashda noma\'lum xatolik', reply_markup=SUPERIOR_ADMIN_KEYBOARD)
#             return
#
#         # Save the file details to DB
#         await save_file_details(
#             session=session, file=File(
#                 asst_file_id=uploaded_file_id,
#                 tg_file_id=file_id,
#                 name=file_name,
#                 extension=extension,
#                 content_type=content_type,
#                 size=file_size,
#                 path=file_upload_dir,
#                 uploaded_by=current_user_role.user_id
#             ),
#             check_file=False
#         )
#     except Exception as e:
#         print(e)
#         await state.clear()
#
#         if current_user_role.role_name == RoleType.SUPER_ADMIN.name:
#             await message.answer('Faylni yuklashda noma\'lum xatolik', reply_markup=SUPER_ADMIN_KEYBOARD)
#         else:
#             await message.answer('Faylni yuklashda noma\'lum xatolik', reply_markup=SUPERIOR_ADMIN_KEYBOARD)
#         return
#
#     await state.clear()
#
#     if current_user_role.role_name == RoleType.SUPER_ADMIN.name:
#         await message.answer(text='Fayl muvaffaqqiyatli yuklandi!', reply_markup=SUPER_ADMIN_KEYBOARD)
#     else:
#         await message.answer(text='Fayl muvaffaqqiyatli yuklandi!', reply_markup=SUPERIOR_ADMIN_KEYBOARD)


@superior_admin_router.message(StateFilter(FileFSM.file_upload), F.content_type == 'document')
async def superior_admin_upload_file_content_handler(message: Message, session: AsyncSession, state: FSMContext,
                                                     bot: Bot):
    # Checking if user is not none as user's role is needed below
    # In case user is none in DB, they are required to be registered in 'users' table, and /start registers new users
    current_user_role = await get_role_by_user_tg_id(session=session, user_tg_id=message.from_user.id)
    if current_user_role is None:
        await message.answer("Faylni yuklashda noma'lum xatolik. Iltimos, /start buyrug'ini bering.")
        return
    await bot.send_chat_action(message.from_user.id, 'upload_document')
    try:
        document = message.document
        document_local_path = DOC_UPLOAD_DIR.joinpath(document.file_name)

        if document.file_size > DOC_MAX_SIZE:
            await message.answer(
                f"Fayl hajmi {DOC_MAX_SIZE / 1024 / 1024} MB dan katta. Iltimos, kichikroq fayl yuklang.")
            return

        if is_supported_file_type(document.file_name) is False:
            await message.answer(
                f'Siz noto\'g\'ri formatdagi faylni yukladinggiz. Iltimos, faylni quyidagi formatlardan birida yuklang: {", ".join(str(x) for x in DOC_EXT)}')
            return

        if Path.exists(document_local_path):
            await message.answer("Bunday nomli fayl yuklanib bo'lgan. Iltimos, boshqa faylni yuklang.")
            return

        document_file = await bot.get_file(document.file_id)

        await bot.download_file(document_file.file_path, document_local_path)

        # Upload file to OpenAI first
        openai_file_id = upload_file_to_openai(document_local_path)

        # Now attach the file to OpenAI's Vector Store
        openai_batch_id = upload_file_to_vector_store(file_id=openai_file_id)

        # Remove the file just saved above from local storage in case of failure while uploading the file to OpenAI
        if openai_file_id is None or openai_batch_id is None: raise NameError("Cannot send file to OpenAI")

        # Save the file details to DB
        await save_file_details(
            session=session,
            file=File(
                asst_file_id=openai_file_id,
                tg_file_id=document.file_id,
                name=document.file_name,
                extension=document_local_path.suffix,
                content_type=document.mime_type,
                size=document.file_size,
                path=UPLOAD_DIR.joinpath(document_local_path.name).__str__(),
                uploaded_by=current_user_role.user_id
            ),
            check_file=False
        )

    except Exception as e:
        # logger.error(format(e))
        # raise e
        print(f'Error: {e}')
        Path(document_local_path).unlink(missing_ok=True)
        await state.clear()
        await message.answer("Faylni yuklashda noma'lum xatolik",
                             reply_markup=SUPER_ADMIN_KEYBOARD if current_user_role.role_name == RoleType.SUPER_ADMIN.name else SUPERIOR_ADMIN_KEYBOARD)
        return

    await state.clear()
    await message.answer("Fayl muvaffaqqiyatli yuklandi",
                         reply_markup=SUPER_ADMIN_KEYBOARD if current_user_role.role_name == RoleType.SUPER_ADMIN.name else SUPERIOR_ADMIN_KEYBOARD)


@superior_admin_router.message(StateFilter(FileFSM.file_upload))
async def superior_admin_upload_incorrect_file_content_handler(message: Message):
    await message.answer(text='Siz noto\'g\'ri ma\'lumot kiritdinggiz.\nIltimos, faylni to\'g\'ri yuklang:')