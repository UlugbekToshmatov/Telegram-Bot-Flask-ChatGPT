import asyncio

from aiogram import Router, types, F, Bot
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import ReplyKeyboardRemove
from sqlalchemy.ext.asyncio import AsyncSession

from database.cruds.chat_crud import update_chat
from database.cruds.message_crud import save_message, save_tg_message_id, get_message_by_id
from database.cruds.reaction_crud import save_dissatisfaction, save_dissatisfaction_feedback
from database.cruds.role_crud import get_role_by_user_id, get_role_by_user_tg_id
from database.models import Message, Chat, User
from database.utils.user_utils import save_user_and_create_chat
from enums.telegram_eunms import SenderType, RoleType
from gpt.ai_assistant import create_thread, send_message
from telegram.handlers.admin_handler import ADMIN_KEYBOARD
from telegram.handlers.super_admin_handler import SUPER_ADMIN_KEYBOARD
from telegram.handlers.superior_admin_handler import SUPERIOR_ADMIN_KEYBOARD
from telegram.keyboards.inline_keyboards import get_callback_buttons
from telegram.uitls.handler_utils import clean_response, greetings, leave_takings, commands

user_router = Router()


class UserDissatisfactionFSM(StatesGroup):
    provide_feedback = State()
    message_id: int = None


@user_router.message(CommandStart())
async def user_start_handler(message: types.Message, session: AsyncSession, state: FSMContext, bot: Bot):
    await bot.send_chat_action(message.chat.id, 'typing')
    print(f'User in user handler start: {message.from_user}')

    try:
        await save_user_and_create_chat(session=session, message=message)
    except Exception as e:
        print(e)
        await message.answer(text=e.args[0])
        return

    state_data = await state.get_data()
    if state_data is not None:
        await state.clear()

    await message.answer(
        text='Asslamu alaykum. Men Adliya Vazirligining yordamchi botiman. Sizga qanday yordam bera olishim mumkin?',
        reply_markup=ReplyKeyboardRemove()
    )


@user_router.callback_query(F.data == 'satisfied')
async def user_satisfaction_handler(callback: types.CallbackQuery, session: AsyncSession, bot: Bot):
    await bot.edit_message_reply_markup(
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id,
        reply_markup=None  # This removes the inline keyboard
    )

    current_user_role = await get_role_by_user_tg_id(session=session, user_tg_id=callback.from_user.id)

    if current_user_role.role_name == RoleType.SUPER_ADMIN.name:
        await callback.message.answer(
            text='Ushbu javobim sizni qanoatlantirganidan xursandman.\n'
                 'Agar sizda qo‘shimcha savollar bo‘lsa, marhamat, so‘rashingiz mumkin.',
            reply_to_message_id=callback.message.message_id,
            reply_markup=SUPER_ADMIN_KEYBOARD
        )
    elif current_user_role.role_name == RoleType.SUPERIOR_ADMIN.name:
        await callback.message.answer(
            text='Ushbu javobim sizni qanoatlantirganidan xursandman.\n'
                 'Agar sizda qo‘shimcha savollar bo‘lsa, marhamat, so‘rashingiz mumkin.',
            reply_to_message_id=callback.message.message_id,
            reply_markup=SUPERIOR_ADMIN_KEYBOARD
        )
    elif current_user_role.role_name == RoleType.ADMIN.name:
        await callback.message.answer(
            text='Ushbu javobim sizni qanoatlantirganidan xursandman.\n'
                 'Agar sizda qo‘shimcha savollar bo‘lsa, marhamat, so‘rashingiz mumkin.',
            reply_to_message_id=callback.message.message_id,
            reply_markup=ADMIN_KEYBOARD
        )
    else:
        await callback.message.answer(
            text='Ushbu javobim sizni qanoatlantirganidan xursandman.\n'
                 'Agar sizda qo‘shimcha savollar bo‘lsa, marhamat, so‘rashingiz mumkin.',
            reply_to_message_id=callback.message.message_id
        )


@user_router.callback_query(F.data.startswith('dissatisfied_'))
async def user_dissatisfaction_handler(callback: types.CallbackQuery, bot: Bot, session:AsyncSession):
    message_id = int(callback.data.split('_')[-1])
    # save dissatisfaction reaction for assistant response
    await save_dissatisfaction(session=session, message_id=message_id)

    await bot.edit_message_reply_markup(
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id,
        reply_markup=None  # This removes the inline keyboard
    )
    await callback.message.answer(
        text='Ushbu javobim sizni qanoatlantirmaganidan afsusdaman.\n'
             'Agar bu borada sizda biror fikr bor bo‘lsa, iltimos fikringgizni bildiring.',
        reply_to_message_id=callback.message.message_id,
        reply_markup=get_callback_buttons(buttons={
            'Fikr bildirish': f'feedback_{message_id}',
            'Davom etish': 'continue',
        },
        sizes=(2,))
    )


@user_router.callback_query(F.data == 'continue')
async def user_continue_handler(callback: types.CallbackQuery, bot: Bot):
    await bot.edit_message_reply_markup(
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id,
        reply_markup=None  # This removes the inline keyboard
    )
    await callback.message.answer('Agar sizda qo‘shimcha savollar bo‘lsa, marhamat, so‘rashingiz mumkin.')


@user_router.callback_query(StateFilter(None), F.data.startswith('feedback_'))
async def user_feedback_option_handler(callback: types.CallbackQuery, session: AsyncSession, bot: Bot, state: FSMContext):
    message_id = int(callback.data.split('_')[-1])

    await state.set_state(UserDissatisfactionFSM.provide_feedback)
    UserDissatisfactionFSM.message_id = message_id

    assistant_response = await get_message_by_id(session=session, message_id=message_id)
    user_prompt = await get_message_by_id(session=session, message_id=assistant_response.reply_to_message_id)

    await bot.edit_message_reply_markup(
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id,
        reply_markup=None  # This removes the inline keyboard
    )
    await callback.message.answer(
        text='Iltimos, bu so\'rovinggiz bo\'yicha fikringgizni bildiring:',
        reply_to_message_id=user_prompt.tg_message_id,
        reply_markup=ReplyKeyboardRemove()
    )


@user_router.message(StateFilter(UserDissatisfactionFSM.provide_feedback), F.text)
async def user_feedback_handler(message: types.Message, session: AsyncSession, state: FSMContext, bot: Bot):
    await bot.send_chat_action(message.chat.id, 'typing')
    assistant_message_id = UserDissatisfactionFSM.message_id
    feedback = message.text
    # save feedback for the reaction
    await save_dissatisfaction_feedback(session=session, message_id=assistant_message_id, feedback=feedback)

    current_user_role = await get_role_by_user_tg_id(session=session, user_tg_id=message.from_user.id)

    if current_user_role.role_name == RoleType.SUPER_ADMIN.name:
        await message.answer(
            text='Fikringgiz uchun rahmat. Agar sizda qo‘shimcha savollar bo‘lsa, yana so‘rashinggiz mumkin.',
            reply_markup=SUPER_ADMIN_KEYBOARD
        )
    elif current_user_role.role_name == RoleType.SUPERIOR_ADMIN.name:
        await message.answer(
            text='Fikringgiz uchun rahmat. Agar sizda qo‘shimcha savollar bo‘lsa, yana so‘rashinggiz mumkin.',
            reply_markup=SUPERIOR_ADMIN_KEYBOARD
        )
    elif current_user_role.role_name == RoleType.ADMIN.name:
        await message.answer(
            text='Fikringgiz uchun rahmat. Agar sizda qo‘shimcha savollar bo‘lsa, yana so‘rashinggiz mumkin.',
            reply_markup=ADMIN_KEYBOARD
        )
    else:
        await message.answer('Fikringgiz uchun rahmat. Agar sizda qo‘shimcha savollar bo‘lsa, yana so‘rashinggiz mumkin.')

    await state.clear()
    UserDissatisfactionFSM.message_id = None


@user_router.message(UserDissatisfactionFSM.provide_feedback)
async def incorrect_user_feedback_handler(message: types.Message):
    await message.answer('Iltimos, fikringgizni yozma ko‘rinishda bildiring:')


user_role = None
temp_message = None

@user_router.message(F.text)
async def user_prompt_handler(message: types.Message, session: AsyncSession, bot: Bot):
    global user_role
    print(f'user: {message.from_user}')
    chat_id = message.chat.id
    text = message.text

    await bot.send_chat_action(chat_id, 'typing')
    try:
        result = await save_user_and_create_chat(session=session, message=message)
        chat: Chat = result['chat']
        user: User = result['user']
        user_role = await get_role_by_user_id(session=session, user_id=user.id)
        user_message = await save_message(session=session, message=Message(text=text, sender=SenderType.USER.name, tg_message_id=message.message_id, chat_id=chat.id))
    except Exception as e:
        print(e)
        if user_role is not None:
            if user_role.name != RoleType.USER.name:
                await message.answer(text=e.args[0])
            else:
                await message.answer(text=e.args[0], reply_markup=ReplyKeyboardRemove())
            return
        else:
            print(f'User role by user id not found!')
            await message.answer(text='Kechirasiz, tizimda xatolik yuz berdi!')
            return

    await bot.send_chat_action(chat_id, 'typing')

    for command in greetings:
        if command.__contains__(text.lower()):
            bot_response = 'Asslamu alaykum. Men Adliya Vazirligining yordamchi botiman. Sizga qanday yordam bera olishim mumkin?'
            await save_message(
                session=session,
                message=Message(text=bot_response, sender=SenderType.BOT.name, reply_to_message_id=user_message.id, chat_id=chat.id)
            )
            if user_role.name != RoleType.USER.name:
                await message.answer(bot_response)
            else:
                await message.answer(bot_response, reply_markup=ReplyKeyboardRemove())
            return

    for leave_taking in leave_takings:
        if leave_taking.__contains__(text.lower()):
            bot_response = 'Xizmatimizdan foydalanganinggiz uchun rahmat. Xayr, salomat bo\'ling.'
            await save_message(
                session=session,
                message=Message(text=bot_response, sender=SenderType.BOT.name, reply_to_message_id=user_message.id, chat_id=chat.id)
            )
            if user_role.name != RoleType.USER.name:
                await message.answer(bot_response)
            else:
                await message.answer(bot_response, reply_markup=ReplyKeyboardRemove())
            return

    for command in commands:
        if text.lower().__contains__(command):
            bot_response = 'Kechirasiz, siz ushbu buyruqdan foydalana olmaysiz!'
            await save_message(
                session=session,
                message=Message(text=bot_response, sender=SenderType.BOT.name, reply_to_message_id=user_message.id, chat_id=chat.id)
            )
            if user_role.name != RoleType.USER.name:
                await message.answer(bot_response)
            else:
                await message.answer(bot_response, reply_markup=ReplyKeyboardRemove())
            return

    if len(text) < 5:
        bot_response = 'Iltimos, savolinggizni to\'liqroq yozing!'
        await save_message(
            session=session,
            message=Message(text=bot_response, sender=SenderType.BOT.name, reply_to_message_id=user_message.id, chat_id=chat.id)
        )
        if user_role.name != RoleType.USER.name:
            await message.answer(bot_response)
        else:
            await message.answer(bot_response, reply_markup=ReplyKeyboardRemove())
        return

    if chat.asst_thread_id is None:
        asst_thread_id = await create_thread()
        chat.asst_thread_id = asst_thread_id
        await update_chat(session=session, chat_id=chat.id, data={'asst_thread_id': asst_thread_id})

    response = await send_message(text=text, thread_id=chat.asst_thread_id)
    assistant_response = response['assistant_response']
    assistant_message_id = response['assistant_message_id']
    assistant_response = clean_response(assistant_response)
    assistant_message = await save_message(
        session=session,
        message=Message(
            text=assistant_response,
            sender=SenderType.ASSISTANT.name,
            bot_message_id=assistant_message_id,
            reply_to_message_id=user_message.id,
            chat_id=chat.id
        )
    )

    global temp_message
    if user_role.name != RoleType.USER.name:
        temp_message = await message.answer(text='Iltimos, kutib turing...')
    else:
        temp_message = await message.answer(text='Iltimos, kutib turing...', reply_markup=ReplyKeyboardRemove())

    await asyncio.sleep(1)
    await bot.delete_message(chat_id=chat_id, message_id=temp_message.message_id)
    tg_bot_response = await message.answer(
        text=assistant_response,
        reply_to_message_id=message.message_id,
        reply_markup=get_callback_buttons(buttons={
            'Qoniqarli': f'satisfied',
            'Qoniqarsiz': f'dissatisfied_{assistant_message.id}',
        },
            sizes=(2,))
    )

    await save_tg_message_id(session=session, message_id=assistant_message.id, tg_message_id=tg_bot_response.message_id)

    # await bot.edit_message_text(text='Iltimos, kutib turing..', chat_id=chat_id, message_id=temp_message.message_id)
    # await asyncio.sleep(1)
    # await bot.edit_message_text(text='Iltimos, kutib turing...', chat_id=chat_id, message_id=temp_message.message_id)
    # await asyncio.sleep(1)
    # # await bot.delete_message(chat_id=chat_id, message_id=temp_message.message_id)
    #
    # await bot.edit_message_text(
    #     text=assistant_response, chat_id=chat_id, message_id=temp_message.message_id,
    #     reply_markup=get_callback_buttons(buttons={
    #         'Qoniqarli': f'satisfied',
    #         'Qoniqarsiz': f'dissatisfied_{assistant_message.id}',
    #     },
    #         sizes=(2,))
    # )

    # await message.answer(
    #     assistant_response,
    #     reply_markup=get_callback_buttons(buttons={
    #         'Qoniqarli': f'satisfied',
    #         'Qoniqarsiz': f'dissatisfied_{assistant_message.id}',
    #     },
    #     sizes=(2,))
    # )