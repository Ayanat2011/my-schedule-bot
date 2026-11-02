from typing import Optional, List
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from bot.database.models import User, Child


async def get_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    username: Optional[str] = None,
    full_name: str = "",
) -> User:
    """Получает пользователя по telegram_id или регистрирует нового родителя."""
    stmt = select(User).where(User.id == telegram_id).options(selectinload(User.children))
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            id=telegram_id,
            username=username,
            full_name=full_name or "",
            role="parent",
            timezone="Europe/Moscow",
            is_notifications_enabled=True,
            morning_digest_enabled=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
    else:
        # Обновим имя и юзернейм, если они изменились
        changed = False
        if username and user.username != username:
            user.username = username
            changed = True
        if full_name and user.full_name != full_name:
            user.full_name = full_name
            changed = True
        if changed:
            await session.commit()

    return user


async def get_user(session: AsyncSession, telegram_id: int) -> Optional[User]:
    """Получает пользователя со всеми связанными детьми."""
    stmt = (
        select(User)
        .where(User.id == telegram_id)
        .options(selectinload(User.children))
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def update_user_settings(session: AsyncSession, telegram_id: int, **kwargs) -> Optional[User]:
    """Обновляет настройки пользователя (часовой пояс, тихие часы и т.д.)."""
    stmt = update(User).where(User.id == telegram_id).values(**kwargs)
    await session.execute(stmt)
    await session.commit()
    return await get_user(session, telegram_id)


async def get_children(session: AsyncSession, parent_id: int) -> List[Child]:
    """Возвращает список всех детей пользователя."""
    stmt = (
        select(Child)
        .where(Child.parent_id == parent_id)
        .options(selectinload(Child.activities))
        .order_by(Child.id)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def create_child(
    session: AsyncSession,
    parent_id: int,
    name: str,
    age: Optional[int] = None,
    color_emoji: str = "👧",
    telegram_id: Optional[int] = None,
) -> Child:
    """Создаёт профиль нового ребёнка."""
    child = Child(
        parent_id=parent_id,
        name=name.strip(),
        age=age,
        color_emoji=color_emoji,
        telegram_id=telegram_id,
    )
    session.add(child)
    await session.commit()
    await session.refresh(child)
    return child


async def get_child(session: AsyncSession, child_id: int) -> Optional[Child]:
    """Получает профиль ребёнка по ID."""
    stmt = (
        select(Child)
        .where(Child.id == child_id)
        .options(selectinload(Child.activities), selectinload(Child.parent))
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def update_child(session: AsyncSession, child_id: int, **kwargs) -> Optional[Child]:
    """Обновляет профиль ребёнка."""
    stmt = update(Child).where(Child.id == child_id).values(**kwargs)
    await session.execute(stmt)
    await session.commit()
    return await get_child(session, child_id)


async def delete_child(session: AsyncSession, child_id: int) -> bool:
    """Удаляет профиль ребёнка и все его занятия."""
    stmt = delete(Child).where(Child.id == child_id)
    result = await session.execute(stmt)
    await session.commit()
    return result.rowcount > 0


async def find_child_by_telegram_id(session: AsyncSession, telegram_id: int) -> Optional[Child]:
    """Ищет профиль ребёнка по его личному Telegram ID."""
    stmt = (
        select(Child)
        .where(Child.telegram_id == telegram_id)
        .options(selectinload(Child.activities), selectinload(Child.parent))
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
