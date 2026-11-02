from typing import Dict, Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from bot.database.models import User, Child, Activity, Schedule, NotificationLog


async def get_system_statistics(session: AsyncSession) -> Dict[str, Any]:
    """Собирает ключевые метрики системы для панели администратора."""
    # Количество пользователей
    users_count = await session.scalar(select(func.count(User.id))) or 0

    # Количество детей
    children_count = await session.scalar(select(func.count(Child.id))) or 0

    # Количество занятий (всего и активных)
    total_activities = await session.scalar(select(func.count(Activity.id))) or 0
    active_activities = await session.scalar(
        select(func.count(Activity.id)).where(Activity.is_active == True)
    ) or 0

    # Количество слотов в расписании
    total_schedules = await session.scalar(select(func.count(Schedule.id))) or 0

    # Количество отправленных напоминаний
    total_notifications = await session.scalar(
        select(func.count(NotificationLog.id)).where(NotificationLog.status == "sent")
    ) or 0

    # По типам
    notifications_by_type = {}
    stmt_types = (
        select(NotificationLog.notification_type, func.count(NotificationLog.id))
        .where(NotificationLog.status == "sent")
        .group_by(NotificationLog.notification_type)
    )
    result_types = await session.execute(stmt_types)
    for row in result_types.all():
        notifications_by_type[row[0]] = row[1]

    # Количество ошибок отправки
    failed_notifications = await session.scalar(
        select(func.count(NotificationLog.id)).where(NotificationLog.status == "failed")
    ) or 0

    return {
        "users_count": users_count,
        "children_count": children_count,
        "total_activities": total_activities,
        "active_activities": active_activities,
        "total_schedules": total_schedules,
        "total_notifications": total_notifications,
        "notifications_by_type": notifications_by_type,
        "failed_notifications": failed_notifications,
    }
