import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from bot.database.session import async_session_maker

logger = logging.getLogger(__name__)


class DbSessionMiddleware(BaseMiddleware):
    """Middleware для предоставления асинхронной сессии SQLAlchemy в каждый хэндлер."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        async with async_session_maker() as session:
            data["session"] = session
            try:
                return await handler(event, data)
            except Exception as e:
                await session.rollback()
                logger.error(f"Исключение во время обработки события хэндлером: {e}", exc_info=True)
                raise
