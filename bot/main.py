import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties

from bot.config import settings
from bot.database.session import init_db, engine
from bot.middlewares.db_middleware import DbSessionMiddleware
from bot.services.scheduler_service import ReminderScheduler

# Импорт хэндлеров
from bot.handlers.common import router as common_router
from bot.handlers.schedule import router as schedule_router
from bot.handlers.add_activity import router as add_activity_router
from bot.handlers.manage_activity import router as manage_activity_router
from bot.handlers.children import router as children_router
from bot.handlers.locations import router as locations_router
from bot.handlers.reminders import router as reminders_router
from bot.handlers.settings import router as settings_router
from bot.handlers.admin import router as admin_router

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger("schedule_bot")


async def main():
    """Точка входа приложения Telegram-бота «Мой распорядок» (Background Worker)."""
    logger.info("Запуск Telegram-бота «Мой распорядок» в режиме Background Worker (polling)...")

    # Проверка наличия токена при запуске
    token = settings.bot_token
    if not token or token == "dummy_token_for_validation_only":
        logger.critical(
            "❌ КРИТИЧЕСКАЯ ОШИБКА: Токен Telegram-бота не найден!\n"
            "Пожалуйста, задайте переменную окружения TELEGRAM_BOT_TOKEN.\n"
            "Пример: TELEGRAM_BOT_TOKEN=1234567890:ABCdefGhIJKlmNoPQRsTUVwxyZ_1234567"
        )
        sys.exit(1)

    logger.info(f"Проверка токена бота: OK [ID: {settings.masked_token}]")

    # 1. Инициализация базы данных
    await init_db()

    # 2. Инициализация бота и диспетчера
    bot = Bot(
        token=token,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )

    try:
        # Проверка подключения к Telegram Bot API
        bot_user = await bot.get_me()
        logger.info(f"✅ Успешное подключение к Telegram Bot API: @{bot_user.username} ({bot_user.full_name})")
    except Exception as e:
        logger.critical(f"❌ Ошибка подключения к Telegram Bot API: {e}", exc_info=True)
        await bot.session.close()
        sys.exit(1)

    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # 3. Регистрация Middleware
    dp.message.middleware(DbSessionMiddleware())
    dp.callback_query.middleware(DbSessionMiddleware())

    # 4. Подключение роутеров
    dp.include_router(common_router)
    dp.include_router(schedule_router)
    dp.include_router(add_activity_router)
    dp.include_router(manage_activity_router)
    dp.include_router(children_router)
    dp.include_router(locations_router)
    dp.include_router(reminders_router)
    dp.include_router(settings_router)
    dp.include_router(admin_router)

    # 5. Запуск фонового планировщика умных напоминаний (APScheduler / background runner)
    scheduler = ReminderScheduler(bot_instance=bot)
    scheduler.start()

    logger.info("Бот и планировщик напоминаний успешно инициализированы. Запуск polling...")

    try:
        # Пропускаем накопившиеся апдейты при старте
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Критическая ошибка работы бота: {e}", exc_info=True)
    finally:
        logger.info("Остановка компонентов Background Worker...")
        await scheduler.stop()
        await bot.session.close()
        await engine.dispose()
        logger.info("Бот полностью остановлен.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Процесс завершён пользователем.")
