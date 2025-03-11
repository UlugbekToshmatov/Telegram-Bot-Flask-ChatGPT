from typing import Any

from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from sqlalchemy.ext.asyncio import AsyncSession

from database.cruds.role_crud import get_roles, get_role_by_name, get_role_by_user_tg_id
from database.cruds.user_crud import get_all_admins, get_user_by_tg_id, update_user, add_user, get_super_admins, \
    get_user_by_username
from database.models import User
from dtos.user_dto import UserWithRole
from enums.telegram_eunms import RoleType
from telegram.filters.user_types import IsSuperAdmin
from telegram.keyboards.inline_keyboards import get_callback_buttons
from telegram.keyboards.reply_keyboards import get_keyboard

super_admin_router = Router()
super_admin_router.message.filter(IsSuperAdmin())


SUPER_ADMIN_KEYBOARD = get_keyboard(
    'Adminlarni ko\'rish', 'Admin qo\'shish',
    'Fayllarni ko\'rish', 'Fayl yuklash',
    'Savol-javoblarni ko\'rish',
    placeholder='Amaliyot turini tanglang yoki assistent botga savolinggizni yozing:',
    sizes=(2, 2, 1)
)


class AdminFSM(StatesGroup):
    tg_id = State()
    username = State()
    name = State()
    surname = State()
    password = State()
    role_id = State()

    admin_to_be_updated: User = None


@super_admin_router.message(CommandStart())
async def super_admin_start_handler(message: Message) -> None:
    await message.answer(
        text='Amaliyot turini tanglang yoki assistent botga savolinggizni yozing:',
        reply_markup=SUPER_ADMIN_KEYBOARD
    )


@super_admin_router.message(F.text == 'Adminlarni ko\'rish')
async def super_admin_view_admins_handler(message: Message, session: AsyncSession) -> None:
    admins = await get_all_admins(session=session)

    if len(admins) == 0:
        await message.answer('Hozirda hech qanday admin yo\'q!')
        return

    await message.answer(text='***Barcha adminlar ro\'yxati***')

    for admin in admins:
        await message.answer(
            text=f'User telegram id: {admin.user_tg_id},\n'
                 f'User telegram username: {admin.user_tg_username},\n'
                 f'User name: {admin.user_name},\n'
                 f'User surname: {admin.user_surname},\n'
                 f'Role name: {admin.role_name},\n'
                 f'Privileges: {admin.privileges}',
            reply_markup=get_callback_buttons(
                buttons={'Foydalanuvchi ma\'lumotlarini o\'zgartirish': f'update_admin_{admin.user_tg_id}'}
            ),
        )

    await message.answer(text='***Barcha adminlar ro\'yxati***')


# @super_admin_router.callback_query(StateFilter('*'), F.data == 'cancel')
# async def super_admin_cancel_handler(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
#     await bot.edit_message_reply_markup(
#         chat_id=callback.message.chat.id,
#         message_id=callback.message.message_id,
#         reply_markup=None  # This removes the inline keyboard
#     )
#     if AdminFSM.admin_to_be_updated is not None:
#         AdminFSM.admin_to_be_updated = None
#         await callback.message.answer(text='Adminni o\'zgartirish bekor qilindi', reply_markup=SUPER_ADMIN_KEYBOARD)
#     else:
#         await callback.message.answer(text='Yangi adminni qo\'shish bekor qilindi', reply_markup=SUPER_ADMIN_KEYBOARD)
#
#     current_state = await state.get_state()
#     if current_state is not None:
#         await state.clear()


@super_admin_router.message(StateFilter('*'), F.text == 'cancel')
async def super_admin_cancel_operation_handler(message: Message, state: FSMContext) -> None:
    current_state = await state.get_state()

    if current_state is None:
        await message.answer(text='Bekor qilish uchun siz hali biror amaliyotni boshlamadinggiz.')
        return
    elif current_state == 'FileFSM:file_upload':
        await message.answer(text='Fayl yuklash bekor qilindi', reply_markup=SUPER_ADMIN_KEYBOARD)
    elif AdminFSM.admin_to_be_updated is not None:
        AdminFSM.admin_to_be_updated = None
        await message.answer(text='Adminni o\'zgartirish bekor qilindi', reply_markup=SUPER_ADMIN_KEYBOARD)
    else:
        await message.answer(text='Yangi adminni qo\'shish bekor qilindi', reply_markup=SUPER_ADMIN_KEYBOARD)

    await state.clear()


# @super_admin_router.callback_query(StateFilter('*'), F.data == 'next')
# async def super_admin_next_button_handler(callback: CallbackQuery, state: FSMContext, bot: Bot):
#     current_state = await state.get_state()
#     if current_state is None:
#         await callback.message.answer(text='Keyingisi tugmasidan foydalanish uchun siz hali biror amaliyotni boshlamadinggiz.')
#         return
#     elif AdminFSM.admin_to_be_updated is not None:


'''Update admin start'''

@super_admin_router.callback_query(StateFilter(None), F.data.startswith('update_admin_'))
async def super_admin_update_admin_role_handler(callback: CallbackQuery, session: AsyncSession, state: FSMContext, bot: Bot) -> None:
    admin_tg_id = int(callback.data.split('_')[-1])

    if admin_tg_id == callback.from_user.id:
        await callback.message.answer(text='Kechirasiz, siz o\'zinggizning rolinggizni o\'zgartirish huquqiga ega emassiz!')
        return

    admin_user = await get_user_by_tg_id(session=session, tg_id=admin_tg_id)
    if admin_user is None:
        await callback.message.answer(text='Kechirasiz, bunday foydalanuvchi topilmadi!')
        return

    AdminFSM.admin_to_be_updated = admin_user
    await state.set_state(AdminFSM.username)

    temp_message = await callback.message.answer(
        text='Updating admin...',
        reply_markup=ReplyKeyboardRemove()
    )
    await bot.delete_message(chat_id=temp_message.chat.id, message_id=temp_message.message_id)
    await callback.message.answer(
        text='Foydalanuvchining yangi telegram username\'ini kiriting:',
        # reply_markup=get_callback_buttons(    todo: inform super and superior admins about their hidden capabilities
        #     buttons={
        #         # 'Keyingisi': 'next',
        #         'Bekor qilish': 'cancel'
        #     },
        #     sizes=(2, )
        # )
    )


'''Create admin start'''

@super_admin_router.message(StateFilter(None), F.text == 'Admin qo\'shish')
async def super_admin_add_admin_handler(message: Message, state: FSMContext) -> None:
    await message.answer('Foydalanuvchi telegram ID\'sini kiriting:', reply_markup=ReplyKeyboardRemove())
    await state.set_state(AdminFSM.tg_id)


@super_admin_router.message(AdminFSM.tg_id, F.text)
async def super_admin_add_admin_tg_id_handler(message: Message, session: AsyncSession, state: FSMContext) -> None:
    if message.text == '>':
        await message.answer('Kechirasiz, foydalanuvchi telegram ID\'sini kiritish majburiy. '
                             'Iltimos, foydalanuvchi telegram ID\'sini kiriting:')
        return
    elif message.text == '<':
        await message.answer('Siz 1-qadamdasiz, bundan oldin boshqa qadam yo\'q. '
                             'Iltimos, foydalanuvchi telegram ID\'sini kiriting:')
        return

    try:
        tg_id = int(message.text)
    except Exception as e:
        print(e)
        await message.answer('Iltimos, foydalanuvchi telegram ID\'sini to\'g\'ri kiriting:')
        return

    user_role = await get_role_by_user_tg_id(session=session, user_tg_id=tg_id)

    if user_role is not None and user_role.role_name != RoleType.USER.name:
        await message.answer('Kechirasiz, ushbu telegram ID\'li admin allaqachon mavjud. '
                             'Iltimos, boshqa telegram ID kiriting yoki o\'sha admin ma\'lumotlarini o\'zgartiring.')
        return

    await state.update_data({'tg_id': tg_id})
    await state.set_state(AdminFSM.username)
    await message.answer('Foydalanuvchi telegram username\'ini kiriting:')


@super_admin_router.message(AdminFSM.tg_id)
async def super_admin_add_incorrect_admin_tg_id_handler(message: Message):
    await message.answer('Siz noto\'g\'ri ma\'lumot kiritdinggiz.\nIltimos, foydalanuvchi telegram ID\'sini to\'g\'ri kiriting:')


@super_admin_router.message(AdminFSM.username, F.text)
async def super_admin_add_admin_username_handler(message: Message, session: AsyncSession, state: FSMContext) -> None:
    username = message.text

    # Handle next or prev operations
    if username == '>':
        if AdminFSM.admin_to_be_updated is not None:
            await state.update_data({'username': AdminFSM.admin_to_be_updated.username})
            await message.answer('Siz keyingi qadamdasiz. Foydalanuvchining yangi ismini kiriting:')
        else:
            await state.update_data({'username': None})
            await message.answer('Siz keyingi qadamdasiz. Foydalanuvchining ismini kiriting:')

        await state.set_state(AdminFSM.name)
        return
    elif username == '<':
        if AdminFSM.admin_to_be_updated is not None:
            await message.answer('Siz 1-qadamdasiz, bundan oldin boshqa qadam yo\'q. '
                                 'Iltimos, foydalanuvchining yangi telegram username\'ini kiriting:')
        else:
            await state.set_state(AdminFSM.tg_id)
            await message.answer('Siz avvalgi qadamdasiz. Foydalanuvchining telegram ID\'sini kiriting:')
        return

    # Handle incorrect tg username input
    if not username.startswith('@'):
        await message.answer('Iltimos, foydalanuvchi telegram username\'ini kiriting ("@username" kabi):')
        return

    # Check the uniqueness of the provided tg username
    user = await get_user_by_username(session=session, username=username)
    if user is not None:
        await message.answer('Kechirasiz, bu telegram username band! Iltimos, boshqa telegram username kiriting:')
        return

    # Update state, and proceed to the next step
    await state.update_data({'username': username})
    await state.set_state(AdminFSM.name)

    if AdminFSM.admin_to_be_updated is not None:
        await message.answer('Foydalanuvchining yangi ismini kiriting:')
    else:
        await message.answer('Foydalanuvchi ismini kiriting:')


@super_admin_router.message(AdminFSM.username)
async def super_admin_add_incorrect_admin_username_handler(message: Message):
    await message.answer('Siz noto\'g\'ri ma\'lumot kiritdinggiz.\nIltimos, foydalanuvchi telegram username\'ini to\'g\'ri kiriting:')


@super_admin_router.message(AdminFSM.name, F.text)
async def super_admin_add_admin_name_handler(message: Message, state: FSMContext) -> None:
    name = message.text

    if name == '>':
        if AdminFSM.admin_to_be_updated is not None:
            await state.update_data({'name': AdminFSM.admin_to_be_updated.name})
            await state.set_state(AdminFSM.surname)
            await message.answer('Siz keyingi qadamdasiz. Foydalanuvchining yangi sharifini kiriting:')
            return
        else:
            await message.answer('Kechirasiz, foydalanuvchining ismini kiritish majburiy. '
                                 'Iltimos, foydalanuvchining ismini kiriting:')
            return
    elif name == '<':
        if AdminFSM.admin_to_be_updated is not None:
            await message.answer('Siz avvalgi qadamdasiz. Foydalanuvchining yangi telegram username\'ini kiriting: ')
        else:
            await message.answer('Siz avvalgi qadamdasiz. Foydalanuvchining telegram username\'ini kiriting:')

        await state.set_state(AdminFSM.username)
        return

    await state.update_data({'name': name})
    await state.set_state(AdminFSM.surname)

    if AdminFSM.admin_to_be_updated is not None:
        await message.answer('Foydalanuvchining yangi sharifini kiriting:')
    else:
        await message.answer('Foydalanuvchi sharifini kiriting:')


@super_admin_router.message(AdminFSM.name)
async def super_admin_add_incorrect_admin_name_handler(message: Message):
    await message.answer('Siz noto\'g\'ri ma\'lumot kiritdinggiz.\nIltimos, foydalanuvchi ismini to\'g\'ri kiriting:')


@super_admin_router.message(AdminFSM.surname, F.text)
async def super_admin_add_admin_surname_handler(message: Message, session: AsyncSession, state: FSMContext) -> None:
    surname = message.text

    if surname == '>':
        if AdminFSM.admin_to_be_updated is not None:
            await state.update_data({'surname': AdminFSM.admin_to_be_updated.surname})
            await message.answer('Siz keyingi qadamdasiz')
        else:
            await state.update_data({'surname': None})
            await message.answer('Siz keyingi qadamdasiz')
    elif surname == '<':
        if AdminFSM.admin_to_be_updated is not None:
            await message.answer('Siz avvalgi qadamdasiz. Foydalanuvchining yangi ismini kiriting:')
        else:
            await message.answer('Siz avvalgi qadamdasiz. Foydalanuvchining ismini kiriting:')

        await state.set_state(AdminFSM.name)
        return
    else:
        await state.update_data({'surname': surname})

    await state.set_state(AdminFSM.role_id)
    await message.answer('Foydalanuvchi uchun quyidagi rollardan birini tanlang:')
    roles = await get_roles(session=session)
    for role in roles:
        if AdminFSM.admin_to_be_updated is not None:
            await message.answer(
                text=f'Rol: {role.name.upper().replace(" ", "_")},\n'
                     f'Huquqlar: {role.privileges.split(";")}',
                reply_markup=get_callback_buttons(
                    buttons={'Tanlash': f'choose_role_{role.name}'}
                )
            )
        else:
            if role.name != RoleType.USER.name:
                await message.answer(
                    text=f'Rol: {role.name.upper().replace(" ", "_")},\n'
                         f'Huquqlar: {role.privileges.split(";")}',
                    reply_markup=get_callback_buttons(
                        buttons={'Tanlash': f'choose_role_{role.name}'}
                    )
                )


@super_admin_router.message(AdminFSM.surname)
async def super_admin_add_incorrect_admin_surname_handler(message: Message):
    await message.answer('Siz noto\'g\'ri ma\'lumot kiritdinggiz.\nIltimos, foydalanuvchi sharifini to\'g\'ri kiriting:')


@super_admin_router.callback_query(AdminFSM.role_id, F.data.startswith('choose_role_'))
async def super_admin_add_admin_role_handler(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    print(f'Callback received {callback.data}')
    role_name = callback.data.replace('choose_role_', '')
    role = await get_role_by_name(session=session, name=role_name)
    if role is None:
        await callback.message.answer('Kechirasiz, bunday rol topilmadi!')
        await state.clear()
        return

    # check if number of super admins does not exceed 2
    if role.name == RoleType.SUPER_ADMIN.name:
        super_admins: list[UserWithRole] = await get_super_admins(session=session)
        if super_admins.__len__() > 1:
            await callback.message.answer(text='Kechirasiz, siz ushbu rolni boshqalarga bera olmaysiz. Iltimos, boshqa rolni tanlang!')
            return

    await state.update_data({'role_id': role.id})
    new_admin: dict[str, Any] = await state.get_data()
    print(new_admin)

    # get user by tg id, and first check if the user already exists
    # user: User = None
    if AdminFSM.admin_to_be_updated is not None:
        user = await get_user_by_tg_id(session=session, tg_id=AdminFSM.admin_to_be_updated.tg_id)
    else:
        user = await get_user_by_tg_id(session=session, tg_id=new_admin['tg_id'])

    if user is None:
        await add_user(session=session, user=User(
            tg_id=new_admin['tg_id'],
            username=new_admin['username'],
            name=new_admin['name'],
            surname=new_admin['surname'],
            role_id=new_admin['role_id'],
        ))
    else:
        await update_user(session=session, user_id=user.id, data=new_admin, check_role=False)

    if AdminFSM.admin_to_be_updated is not None:
        await callback.message.answer(text='Foydalanuvchi ma\'lumotlari muvaffaqqiyatli o\'zgartirildi', reply_markup=SUPER_ADMIN_KEYBOARD)
    else:
        await callback.message.answer(text='Yangi admin muvaffaqqiyatli qo\'shildi', reply_markup=SUPER_ADMIN_KEYBOARD)

    await state.clear()
    AdminFSM.admin_to_be_updated = None


# Handle next or prev operation when user is in the role_id state
@super_admin_router.message(AdminFSM.role_id, F.text)
async def super_admin_next_or_prev_of_admin_role_handler(message: Message, state: FSMContext) -> None:
    command = message.text

    if command == '>':
        if AdminFSM.admin_to_be_updated is not None:
            await state.update_data({'role_id': AdminFSM.admin_to_be_updated.role_id})
            AdminFSM.admin_to_be_updated = None
            await state.clear()
            await message.answer(text='Foydalanuvchi ma\'lumotlari muvaffaqqiyatli o\'zgartirildi', reply_markup=SUPER_ADMIN_KEYBOARD)
            return
        else:
            await message.answer(text='Kechirasiz, foydalanuvchining rolini kiritish majburiy. '
                                     'Iltimos, foydalanuvchi uchun yuqoridagi rollardan birini tanlang.')
            return
    elif command == '<':
        if AdminFSM.admin_to_be_updated is not None:
            await message.answer(text='Siz avvalgi qadamdasiz. Foydalanuvchining yangi sharifini kiriting:')
        else:
            await message.answer(text='Siz avvalgi qadamdasiz. Foydalanuvchi sharifini kiriting:')

        await state.set_state(AdminFSM.surname)
    else:
        await message.answer('Siz noto\'g\'ri ma\'lumot kiritdinggiz.\nIltimos, foydalanuvchi uchun yuqoridagi rollardan birini tanlang.')


@super_admin_router.message(AdminFSM.role_id)
async def super_admin_add_incorrect_admin_role_handler(message: Message):
    await message.answer('Siz noto\'g\'ri ma\'lumot kiritdinggiz.\nIltimos, foydalanuvchi uchun yuqoridagi rollardan birini tanlang.')

'''Create/update admin end'''


# @super_admin_router.message(F.text)
# async def super_admin_view_questions_handler(message: Message, bot: Bot) -> None:
#     text = message.text
#     tg_id = text.split('...')[0]
#     message_text = text.split('...')[1]
#     await bot.send_message(chat_id=int(tg_id), text=message_text)