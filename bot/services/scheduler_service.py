import asyncio
import logging
from bot.database.session import async_session_maker
from bot.services.reminder_service import (
    check_and_send_due_reminders,
    check_and_send_morning_digests,
)
from bot.config import settings

logger = logging.getLogger(__name__)


class ReminderScheduler:
    """Фоновый планировщик проверки напоминаний и утренних дайджестов."""

    def __init__(self, bot_instance):
        self.bot = bot_instance
        self._task: asyncio.Task | None = None
        self._is_running = False

    async def _loop(self):
        logger.info("Фоновый планировщик напоминаний успешно запущен.")
        while self._is_running:
            try:
                async with async_session_maker() as session:
                    # 1. Проверяем напоминания перед уроками
                    sent_reminders = await check_and_send_due_reminders(session, self.bot)
                    if sent_reminders > 0:
                        logger.info(f"Отправлено напоминаний о занятиях: {sent_reminders}")

                    # 2. Проверяем утренние дайджесты
                    sent_digests = await check_and_send_morning_digests(session, self.bot)
                    if sent_digests > 0:
                        logger.info(f"Отправлено утренних дайджестов: {sent_digests}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Ошибка в цикле планировщика напоминаний: {e}", exc_info=True)

            try:
                await asyncio.sleep(settings.SCHEDULER_CHECK_INTERVAL)
            except asyncio.CancelledError:
                break

        logger.info("Фоновый планировщик напоминаний остановлен.")

    def start(self):
        """Запуск фоновой задачи."""
        if not self._is_running:
            self._is_running = True
            self._task = asyncio.create_task(self._loop())

    async def stop(self):
        """Корректная остановка фоновой задачи."""
        self._is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
