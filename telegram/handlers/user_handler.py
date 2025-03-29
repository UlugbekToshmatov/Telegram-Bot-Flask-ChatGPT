import time

from aiogram import Router, types, F, Bot
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import ReplyKeyboardRemove
from sqlalchemy.ext.asyncio import AsyncSession

from database.cruds.chat_crud import update_chat, update_chat_run_id
from database.cruds.message_crud import save_message, save_tg_message_id, get_message_by_id
from database.cruds.reaction_crud import save_dissatisfaction, save_dissatisfaction_feedback
from database.cruds.role_crud import get_role_by_user_id, get_role_by_user_tg_id
from database.models import Message, Chat, User
from database.utils.user_utils import save_user_and_create_chat
from enums.telegram_eunms import SenderType, RoleType
from gpt.open_ai_assistant import create_thread, send_message_to_open_ai
from telegram.handlers.admin_handler import ADMIN_KEYBOARD
from telegram.handlers.super_admin_handler import SUPER_ADMIN_KEYBOARD
from telegram.handlers.superior_admin_handler import SUPERIOR_ADMIN_KEYBOARD
from telegram.keyboards.inline_keyboards import get_callback_buttons
from telegram.uitls.handler_utils import clean_response, greetings, leave_takings, commands, mask_and_extract_entities, \
    contains_cyrillic, contains_latin, to_latin, to_cyrillic

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
        text="Iltimos, bu so'rovinggiz bo'yicha fikringgizni bildiring:",
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
        await message.answer(
            'Fikringgiz uchun rahmat. Agar sizda qo‘shimcha savollar bo‘lsa, yana so‘rashinggiz mumkin.',
            reply_markup=ReplyKeyboardRemove()
        )

    await state.clear()
    UserDissatisfactionFSM.message_id = None


@user_router.message(UserDissatisfactionFSM.provide_feedback)
async def incorrect_user_feedback_handler(message: types.Message):
    await message.answer('Iltimos, fikringgizni yozma ko‘rinishda bildiring:')


user_role = None
temp_message = None
response = None

class QuestionFSM(StatesGroup):
    in_progress = State()


@user_router.message(F.text)
async def user_prompt_handler(message: types.Message, session: AsyncSession, bot: Bot, state: FSMContext):
    question_state = await state.get_state()
    if question_state == QuestionFSM.in_progress:
        await message.answer(
            text="Iltimos, bu so'rovinggizni endi yozing",
            reply_to_message_id=message.message_id
        )
        return

    start = time.time()
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

    is_cyrillic_text = contains_cyrillic(text)
    is_latin_text = contains_latin(text)

    if not is_cyrillic_text and not is_latin_text:
        bot_response = 'Iltimos, savolinggizni tushunarliroq yozing'
        await save_message(
            session=session,
            message=Message(text=bot_response, sender=SenderType.BOT.name, reply_to_message_id=user_message.id,
                            chat_id=chat.id)
        )
        if user_role.name != RoleType.USER.name:
            await message.answer(bot_response)
        else:
            await message.answer(bot_response, reply_markup=ReplyKeyboardRemove())
        return
    elif is_cyrillic_text:
        text = to_latin(text)

    for greeting in greetings:
        if greeting.__contains__(text.replace('?', "").replace('!', "").replace('.', "").lower()):
            bot_response = 'Assalomu alaykum. Men Adliya Vazirligining yordamchi botiman. Sizga qanday yordam bera olishim mumkin?'
            if is_cyrillic_text:
                bot_response = to_cyrillic(bot_response)
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
            bot_response = "Xizmatimizdan foydalanganinggiz uchun rahmat. Xayr, salomat bo'ling."
            if is_cyrillic_text:
                bot_response = to_cyrillic(bot_response)
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
        if text == command:
            bot_response = 'Kechirasiz, siz ushbu buyruqdan foydalana olmaysiz!'
            if is_cyrillic_text:
                bot_response = to_cyrillic(bot_response)
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
        bot_response = "Iltimos, savolinggizni to'liqroq yozing!"
        if is_cyrillic_text:
            bot_response = to_cyrillic(bot_response)
        await save_message(
            session=session,
            message=Message(text=bot_response, sender=SenderType.BOT.name, reply_to_message_id=user_message.id, chat_id=chat.id)
        )
        if user_role.name != RoleType.USER.name:
            await message.answer(bot_response)
        else:
            await message.answer(bot_response, reply_markup=ReplyKeyboardRemove())
        return

    global temp_message
    if user_role.name != RoleType.USER.name:
        temp_message = await message.answer(text='Iltimos, kutib turing...')
    else:
        temp_message = await message.answer(text='Iltimos, kutib turing...', reply_markup=ReplyKeyboardRemove())

    await bot.send_chat_action(chat_id, 'typing')
    await state.set_state(QuestionFSM.in_progress)

    if chat.asst_thread_id is None:
        asst_thread_id = await create_thread()
        chat.asst_thread_id = asst_thread_id
        await update_chat(session=session, chat_id=chat.id, data={'asst_thread_id': asst_thread_id})

    masked_question, real_values = mask_and_extract_entities(text)
    print(f"Masked question: {masked_question}")
    print(f"Real values: {real_values}")
    global response
    if chat.asst_run_id is None:
        response = await send_message_to_open_ai(text=masked_question, thread_id=chat.asst_thread_id)
    else:
        response = await send_message_to_open_ai(text=masked_question, thread_id=chat.asst_thread_id, run_id=chat.asst_run_id)
    assistant_response = response['assistant_response']
    assistant_message_id = response['assistant_message_id']
    assistant_run_id = response['assistant_run_id']

    # Save last run id to retrieve and cancel a potential 'in_progress' run if no error occurred in OpenAI
    if assistant_run_id is not None:
        await update_chat_run_id(session=session, chat_id=chat.id, data={'asst_run_id': assistant_run_id})

    assistant_response = clean_response(assistant_response)

    # Replace masked values with real ones
    for entity, values in real_values.items():
        if values:
            assistant_response = assistant_response.replace(f"MASK_{entity}", values[0])

    print(f"Assistant response after cleaning and replacing masked values: {assistant_response}")

    if is_cyrillic_text:
        assistant_response = to_cyrillic(assistant_response)

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
    end = time.time()
    await save_tg_message_id(session=session, message_id=assistant_message.id, tg_message_id=tg_bot_response.message_id)
    question_state = await state.get_state()
    if question_state == QuestionFSM.in_progress:
        await state.clear()
    print(f"Time spent in total: {(end - start)} seconds")

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