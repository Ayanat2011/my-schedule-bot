import os
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Конфигурация приложения бота «Мой распорядок»."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    BOT_TOKEN: str = Field(
        default="",
        description="Токен Telegram бота от @BotFather (из TELEGRAM_BOT_TOKEN или BOT_TOKEN)"
    )
    TELEGRAM_BOT_TOKEN: str = Field(
        default="",
        description="Токен Telegram бота (из TELEGRAM_BOT_TOKEN)"
    )

    # Database: по умолчанию локальный SQLite файл
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./schedule_bot.db",
        description="URL подключения к базе данных (PostgreSQL или SQLite)"
    )

    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "schedule_user"
    DB_PASSWORD: str = "schedule_password"
    DB_NAME: str = "schedule_bot_db"

    # Administrators
    ADMIN_IDS_STR: str = Field(default="", alias="ADMIN_IDS")

    # Timezone & defaults
    DEFAULT_TIMEZONE: str = Field(
        default="Europe/Moscow",
        description="Часовой пояс по умолчанию"
    )

    # Logging
    LOG_LEVEL: str = Field(default="INFO", description="Уровень логирования")

    # Scheduler settings
    SCHEDULER_CHECK_INTERVAL: int = Field(
        default=30,
        description="Интервал проверки напоминаний (в секундах)"
    )

    @property
    def bot_token(self) -> str:
        """Возвращает токен бота исключительно из переменной окружения TELEGRAM_BOT_TOKEN (или BOT_TOKEN)."""
        token = (
            os.getenv("TELEGRAM_BOT_TOKEN")
            or self.TELEGRAM_BOT_TOKEN
            or os.getenv("BOT_TOKEN")
            or self.BOT_TOKEN
        )
        return token.strip() if token else ""

    @property
    def masked_token(self) -> str:
        """Безопасное представление токена для логов (без раскрытия секрета)."""
        tok = self.bot_token
        if not tok:
            return "<НЕ УКАЗАН>"
        if ":" in tok:
            bot_id, secret = tok.split(":", 1)
            masked_secret = secret[:4] + "..." + secret[-4:] if len(secret) > 8 else "***"
            return f"{bot_id}:{masked_secret}"
        return tok[:4] + "..." if len(tok) > 4 else "***"

    @property
    def admin_ids(self) -> List[int]:
        """Парсинг списка ID администраторов из строки."""
        if not self.ADMIN_IDS_STR:
            return []
        ids = []
        for x in self.ADMIN_IDS_STR.split(","):
            cleaned = x.strip()
            if cleaned.isdigit():
                ids.append(int(cleaned))
        return ids

    @property
    def effective_db_url(self) -> str:
        """Возвращает скорректированный URL для async SQLAlchemy."""
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://") and not url.startswith("postgresql+asyncpg://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif url.startswith("sqlite://") and not url.startswith("sqlite+aiosqlite://"):
            url = url.replace("sqlite://", "sqlite+aiosqlite://", 1)
        return url


settings = Settings()
