from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import async_sessionmaker


class DataBaseSession(BaseMiddleware):
    def __init__(self, session_pool: async_sessionmaker):
        print("DataBaseSession middleware is initialized")
        self.session_pool = session_pool


    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # "async with self.session_pool() as session:
        #     print("Session from session_pool is called")
        #     data['session'] = session
        #     return await handler(event, data)"
        async with self.session_pool() as session:
            print("Session from session_pool is called")
            data['session'] = session

            # Execute the handler
            result = await handler(event, data)

            # If needed, commit the transaction before the session closes
            await session.commit()  # If your handler does DB changes

            # The session will be closed automatically after the handler finishes
            return result