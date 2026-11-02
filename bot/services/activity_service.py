from datetime import date, time
from typing import Optional, List, Dict, Any
from sqlalchemy import select, update, delete, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from bot.database.models import Activity, Schedule, ReminderSetting, Location, Child, User


# ===================== Locations CRUD =====================

async def create_location(
    session: AsyncSession,
    user_id: int,
    name: str,
    address: str = "",
    note: Optional[str] = None,
) -> Location:
    """Создаёт новое место проведения занятий."""
    loc = Location(
        user_id=user_id,
        name=name.strip(),
        address=address.strip(),
        note=note.strip() if note else None,
    )
    session.add(loc)
    await session.commit()
    await session.refresh(loc)
    return loc


async def get_locations(session: AsyncSession, user_id: int) -> List[Location]:
    """Возвращает список всех мест занятий пользователя."""
    stmt = (
        select(Location)
        .where(Location.user_id == user_id)
        .order_by(Location.name)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_location(session: AsyncSession, location_id: int) -> Optional[Location]:
    """Возвращает место проведения по ID."""
    stmt = select(Location).where(Location.id == location_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def delete_location(session: AsyncSession, location_id: int, user_id: int) -> bool:
    """Удаляет место проведения занятий."""
    stmt = delete(Location).where(and_(Location.id == location_id, Location.user_id == user_id))
    result = await session.execute(stmt)
    await session.commit()
    return result.rowcount > 0


# ===================== Activities & Schedules CRUD =====================

async def create_activity(
    session: AsyncSession,
    child_id: int,
    title: str,
    category: str,
    icon: str,
    start_time: time,
    end_time: time,
    days_of_week: Optional[List[int]] = None,  # [0, 2, 4] для Пн, Ср, Пт
    specific_date: Optional[date] = None,      # Для разового занятия
    location_id: Optional[int] = None,
    teacher_name: Optional[str] = None,
    teacher_phone: Optional[str] = None,
    items_to_bring: Optional[str] = None,
    notes: Optional[str] = None,
    reminder_options: Optional[Dict[str, bool]] = None,
) -> Activity:
    """Создаёт занятие с расписанием и настройками напоминаний."""
    activity = Activity(
        child_id=child_id,
        location_id=location_id,
        title=title.strip(),
        category=category,
        icon=icon,
        teacher_name=teacher_name.strip() if teacher_name else None,
        teacher_phone=teacher_phone.strip() if teacher_phone else None,
        items_to_bring=items_to_bring.strip() if items_to_bring else None,
        notes=notes.strip() if notes else None,
        is_active=True,
    )
    session.add(activity)
    await session.flush()

    # Добавляем расписание
    if specific_date:
        # Разовое мероприятие
        sch = Schedule(
            activity_id=activity.id,
            is_recurring=False,
            specific_date=specific_date,
            day_of_week=specific_date.weekday(),
            start_time=start_time,
            end_time=end_time,
        )
        session.add(sch)
    elif days_of_week:
        # Регулярные дни недели
        for day in days_of_week:
            sch = Schedule(
                activity_id=activity.id,
                is_recurring=True,
                day_of_week=day,
                start_time=start_time,
                end_time=end_time,
            )
            session.add(sch)
    else:
        # По умолчанию понедельник
        sch = Schedule(
            activity_id=activity.id,
            is_recurring=True,
            day_of_week=0,
            start_time=start_time,
            end_time=end_time,
        )
        session.add(sch)

    # Настройки напоминаний
    rem_opts = reminder_options or {}
    rem = ReminderSetting(
        activity_id=activity.id,
        remind_1_day=rem_opts.get("remind_1_day", True),
        remind_2_hours=rem_opts.get("remind_2_hours", True),
        remind_30_min=rem_opts.get("remind_30_min", True),
        remind_10_min=rem_opts.get("remind_10_min", True),
        notify_parent=rem_opts.get("notify_parent", True),
        notify_child=rem_opts.get("notify_child", True),
    )
    session.add(rem)

    await session.commit()
    await session.refresh(activity)
    return await get_activity(session, activity.id)  # type: ignore


async def get_activity(session: AsyncSession, activity_id: int) -> Optional[Activity]:
    """Возвращает занятие со всеми связями."""
    stmt = (
        select(Activity)
        .where(Activity.id == activity_id)
        .options(
            selectinload(Activity.child).selectinload(Child.parent),
            selectinload(Activity.location),
            selectinload(Activity.schedules),
            selectinload(Activity.reminder_setting),
        )
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_child_activities(session: AsyncSession, child_id: int, active_only: bool = False) -> List[Activity]:
    """Возвращает список всех занятий ребёнка."""
    stmt = (
        select(Activity)
        .where(Activity.child_id == child_id)
        .options(
            selectinload(Activity.schedules),
            selectinload(Activity.location),
            selectinload(Activity.reminder_setting),
        )
        .order_by(Activity.title)
    )
    if active_only:
        stmt = stmt.where(Activity.is_active == True)

    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_all_parent_activities(session: AsyncSession, parent_id: int) -> List[Activity]:
    """Возвращает все занятия всех детей родителя."""
    stmt = (
        select(Activity)
        .join(Activity.child)
        .where(Child.parent_id == parent_id)
        .options(
            selectinload(Activity.child),
            selectinload(Activity.schedules),
            selectinload(Activity.location),
        )
        .order_by(Activity.title)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def update_activity(session: AsyncSession, activity_id: int, **kwargs) -> Optional[Activity]:
    """Обновляет поля занятия."""
    stmt = update(Activity).where(Activity.id == activity_id).values(**kwargs)
    await session.execute(stmt)
    await session.commit()
    return await get_activity(session, activity_id)


async def delete_activity(session: AsyncSession, activity_id: int) -> bool:
    """Удаляет занятие со всеми связанными расписаниями и напоминаниями."""
    stmt = delete(Activity).where(Activity.id == activity_id)
    result = await session.execute(stmt)
    await session.commit()
    return result.rowcount > 0


async def toggle_activity_active(session: AsyncSession, activity_id: int) -> Optional[bool]:
    """Переключает статус активности занятия."""
    act = await get_activity(session, activity_id)
    if not act:
        return None
    act.is_active = not act.is_active
    await session.commit()
    return act.is_active


async def update_reminder_settings(
    session: AsyncSession,
    activity_id: int,
    **kwargs,
) -> Optional[ReminderSetting]:
    """Обновляет настройки напоминаний занятия."""
    stmt = (
        update(ReminderSetting)
        .where(ReminderSetting.activity_id == activity_id)
        .values(**kwargs)
    )
    await session.execute(stmt)
    await session.commit()
    act = await get_activity(session, activity_id)
    return act.reminder_setting if act else None


# ===================== Schedule Occurrence Queries =====================

async def get_schedule_item(session: AsyncSession, schedule_id: int) -> Optional[Schedule]:
    """Возвращает элемент расписания с подгрузкой Activity и Child."""
    stmt = (
        select(Schedule)
        .where(Schedule.id == schedule_id)
        .options(
            selectinload(Schedule.activity).selectinload(Activity.child),
            selectinload(Schedule.activity).selectinload(Activity.location),
        )
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def toggle_schedule_cancellation(session: AsyncSession, schedule_id: int) -> Optional[bool]:
    """Переключает статус отмены занятия на сегодня."""
    sch = await get_schedule_item(session, schedule_id)
    if not sch:
        return None
    sch.is_cancelled = not sch.is_cancelled
    await session.commit()
    return sch.is_cancelled


async def mark_schedule_completed(
    session: AsyncSession,
    schedule_id: int,
    is_completed: bool = True,
) -> Optional[bool]:
    """Отмечает занятие как выполненное."""
    sch = await get_schedule_item(session, schedule_id)
    if not sch:
        return None
    sch.is_completed = is_completed
    await session.commit()
    return sch.is_completed


async def get_user_schedule_for_date(
    session: AsyncSession,
    user_id: int,
    target_date: date,
    child_id: Optional[int] = None,
) -> List[Schedule]:
    """
    Получает все слоты расписания на указанную дату (сегодня, завтра или любой день).
    Учитывает:
    - активные занятия (is_active == True)
    - регулярные по дню недели (day_of_week == target_date.weekday() and is_recurring == True)
    - разовые на конкретную дату (specific_date == target_date and is_recurring == False)
    - фильтрацию по ребёнку (опционально)
    - сортировку по start_time
    """
    target_weekday = target_date.weekday()

    stmt = (
        select(Schedule)
        .join(Schedule.activity)
        .join(Activity.child)
        .where(
            and_(
                Child.parent_id == user_id,
                Activity.is_active == True,
                or_(
                    and_(
                        Schedule.is_recurring == True,
                        Schedule.day_of_week == target_weekday,
                    ),
                    and_(
                        Schedule.is_recurring == False,
                        Schedule.specific_date == target_date,
                    ),
                ),
            )
        )
        .options(
            selectinload(Schedule.activity).selectinload(Activity.child),
            selectinload(Schedule.activity).selectinload(Activity.location),
        )
        .order_by(Schedule.start_time)
    )

    if child_id:
        stmt = stmt.where(Activity.child_id == child_id)

    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_child_schedule_for_date(
    session: AsyncSession,
    child_id: int,
    target_date: date,
) -> List[Schedule]:
    """Получает расписание конкретного ребёнка на выбранную дату."""
    target_weekday = target_date.weekday()

    stmt = (
        select(Schedule)
        .join(Schedule.activity)
        .where(
            and_(
                Activity.child_id == child_id,
                Activity.is_active == True,
                or_(
                    and_(
                        Schedule.is_recurring == True,
                        Schedule.day_of_week == target_weekday,
                    ),
                    and_(
                        Schedule.is_recurring == False,
                        Schedule.specific_date == target_date,
                    ),
                ),
            )
        )
        .options(
            selectinload(Schedule.activity).selectinload(Activity.location),
            selectinload(Schedule.activity).selectinload(Activity.child),
        )
        .order_by(Schedule.start_time)
    )

    result = await session.execute(stmt)
    return list(result.scalars().all())
