import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy import event
from bot.config import settings
from bot.database.models import Base

logger = logging.getLogger(__name__)

# Параметры подключения к движку БД
connect_args = {}
if "sqlite" in settings.effective_db_url:
    connect_args["check_same_thread"] = False

engine: AsyncEngine = create_async_engine(
    settings.effective_db_url,
    echo=False,
    future=True,
    connect_args=connect_args,
    pool_pre_ping=True,
)

# Включение внешних ключей для SQLite
if "sqlite" in settings.effective_db_url:
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def init_db() -> None:
    """Инициализация базы данных: создание всех таблиц, если они не существуют."""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Таблицы базы данных успешно проверены/созданы.")
    except Exception as e:
        logger.error(f"Ошибка при инициализации базы данных: {e}", exc_info=True)
        raise


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Асинхронный генератор сессий базы данных."""
    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
