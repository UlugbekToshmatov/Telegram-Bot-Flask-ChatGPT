import asyncio

from aiogram import Bot, Dispatcher

from configs.config import TELEGRAM_TOKEN
from database.engine import on_startup, on_shutdown, session_maker
from database.middleware import DataBaseSession
from telegram.handlers.super_admin_handler import super_admin_router
from telegram.handlers.superior_admin_handler import superior_admin_router
from telegram.handlers.user_handler import user_router


bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
dp.include_router(super_admin_router)
dp.include_router(superior_admin_router)
dp.include_router(user_router)


async def main():
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    dp.update.middleware(DataBaseSession(session_pool=session_maker))
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == '__main__':
    asyncio.run(main())