import logging
from datetime import datetime, date, timedelta, time
from typing import List, Dict, Any, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

try:
    from zoneinfo import ZoneInfo
    def get_tz(name: str):
        try:
            return ZoneInfo(name)
        except Exception:
            return ZoneInfo("Europe/Moscow")
except ImportError:
    try:
        import pytz
        def get_tz(name: str):
            try:
                return pytz.timezone(name)
            except Exception:
                return pytz.timezone("Europe/Moscow")
    except ImportError:
        def get_tz(name: str):
            return None

def localize_datetime(naive_dt: datetime, tz) -> datetime:
    if tz is None:
        return naive_dt
    if hasattr(tz, "localize"):
        return tz.localize(naive_dt)
    return naive_dt.replace(tzinfo=tz)

from bot.database.models import (
    User,
    Child,
    Activity,
    Schedule,
    ReminderSetting,
    NotificationLog,
)
from bot.utils.time_utils import get_user_now, is_in_quiet_hours
from bot.utils.text_helpers import (
    format_child_reminder_message,
    format_parent_reminder_message,
    format_morning_digest_message,
)

logger = logging.getLogger(__name__)


async def is_notification_already_sent(
    session: AsyncSession,
    user_id: int,
    schedule_id: Optional[int],
    notification_type: str,
    target_datetime: datetime,
) -> bool:
    """Проверяет, было ли уже отправлено такое уведомление, чтобы исключить дубли."""
    # Округляем target_datetime до минут для надёжного сопоставления
    clean_target = target_datetime.replace(second=0, microsecond=0)
    stmt = (
        select(NotificationLog)
        .where(
            and_(
                NotificationLog.user_id == user_id,
                NotificationLog.notification_type == notification_type,
                NotificationLog.target_datetime == clean_target,
            )
        )
    )
    if schedule_id is not None:
        stmt = stmt.where(NotificationLog.schedule_id == schedule_id)

    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None


async def record_notification_log(
    session: AsyncSession,
    user_id: int,
    notification_type: str,
    target_datetime: datetime,
    activity_id: Optional[int] = None,
    schedule_id: Optional[int] = None,
    status: str = "sent",
) -> NotificationLog:
    """Записывает факт отправки или подавления уведомления в базу данных."""
    clean_target = target_datetime.replace(second=0, microsecond=0)
    log = NotificationLog(
        user_id=user_id,
        activity_id=activity_id,
        schedule_id=schedule_id,
        notification_type=notification_type,
        target_datetime=clean_target,
        status=status,
    )
    session.add(log)
    await session.commit()
    return log


def get_schedule_target_datetime(
    schedule: Schedule,
    target_date: date,
    user_tz: Any,
) -> datetime:
    """Возвращает datetime начала занятия с привязкой к часовому поясу."""
    naive_dt = datetime.combine(target_date, schedule.start_time)
    return localize_datetime(naive_dt, user_tz)


async def check_and_send_due_reminders(session: AsyncSession, bot_instance) -> int:
    """
    Основная логика сканирования предстоящих занятий и рассылки уведомлений.
    Возвращает количество успешно отправленных уведомлений.
    """
    sent_count = 0

    # Загружаем всех пользователей с активными уведомлениями
    stmt = (
        select(User)
        .where(User.is_notifications_enabled == True)
        .options(
            selectinload(User.children)
            .selectinload(Child.activities)
            .selectinload(Activity.schedules),
            selectinload(User.children)
            .selectinload(Child.activities)
            .selectinload(Activity.reminder_setting),
            selectinload(User.children)
            .selectinload(Child.activities)
            .selectinload(Activity.location),
        )
    )
    result = await session.execute(stmt)
    users = result.scalars().all()

    for user in users:
        tz = get_tz(user.timezone or "Europe/Moscow")
        user_now = datetime.now(tz) if tz else datetime.now()
        today_date = user_now.date()
        tomorrow_date = today_date + timedelta(days=1)

        # Проверка тихих часов
        in_quiet = False
        if user.quiet_hours_enabled:
            in_quiet = is_in_quiet_hours(
                user_now.time(),
                user.quiet_hours_start,
                user.quiet_hours_end,
            )

        for child in user.children:
            for activity in child.activities:
                if not activity.is_active:
                    continue

                rem_set = activity.reminder_setting
                if not rem_set:
                    continue

                for sch in activity.schedules:
                    if sch.is_cancelled:
                        continue

                    # Определяем, на какие даты выпадает данное расписание (сегодня или завтра)
                    candidate_dates = []
                    if sch.is_recurring:
                        if sch.day_of_week == today_date.weekday():
                            candidate_dates.append(today_date)
                        if sch.day_of_week == tomorrow_date.weekday():
                            candidate_dates.append(tomorrow_date)
                    else:
                        if sch.specific_date in (today_date, tomorrow_date):
                            candidate_dates.append(sch.specific_date)

                    for occ_date in candidate_dates:
                        occ_dt = get_schedule_target_datetime(sch, occ_date, tz)
                        diff_seconds = (occ_dt - user_now).total_seconds()

                        # Напоминание за 1 день (от 23 до 25 часов)
                        if rem_set.remind_1_day and (23 * 3600 <= diff_seconds <= 25 * 3600):
                            sent_count += await _process_reminder_dispatch(
                                session=session,
                                bot=bot_instance,
                                user=user,
                                child=child,
                                activity=activity,
                                schedule=sch,
                                occ_dt=occ_dt,
                                notif_type="1_day",
                                in_quiet=in_quiet,
                                rem_set=rem_set,
                            )

                        # Напоминание за 2 часа (от 110 до 130 минут = 6600 до 7800 сек)
                        if rem_set.remind_2_hours and (6600 <= diff_seconds <= 7800):
                            sent_count += await _process_reminder_dispatch(
                                session=session,
                                bot=bot_instance,
                                user=user,
                                child=child,
                                activity=activity,
                                schedule=sch,
                                occ_dt=occ_dt,
                                notif_type="2_hours",
                                in_quiet=in_quiet,
                                rem_set=rem_set,
                            )

                        # Напоминание за 30 минут (от 25 до 35 минут = 1500 до 2100 сек)
                        if rem_set.remind_30_min and (1500 <= diff_seconds <= 2100):
                            sent_count += await _process_reminder_dispatch(
                                session=session,
                                bot=bot_instance,
                                user=user,
                                child=child,
                                activity=activity,
                                schedule=sch,
                                occ_dt=occ_dt,
                                notif_type="30_min",
                                in_quiet=in_quiet,
                                rem_set=rem_set,
                            )

                        # Напоминание за 10 минут (от 7 до 15 минут = 420 до 900 сек)
                        if rem_set.remind_10_min and (420 <= diff_seconds <= 900):
                            sent_count += await _process_reminder_dispatch(
                                session=session,
                                bot=bot_instance,
                                user=user,
                                child=child,
                                activity=activity,
                                schedule=sch,
                                occ_dt=occ_dt,
                                notif_type="10_min",
                                in_quiet=in_quiet,
                                rem_set=rem_set,
                            )

    return sent_count


async def _process_reminder_dispatch(
    session: AsyncSession,
    bot,
    user: User,
    child: Child,
    activity: Activity,
    schedule: Schedule,
    occ_dt: datetime,
    notif_type: str,
    in_quiet: bool,
    rem_set: ReminderSetting,
) -> int:
    """Отправка уведомления родителю и ребёнку с проверкой дублирования и тихих часов."""
    # Если тихие часы включены — подавляем заблаговременные напоминания (за 1 день и за 2 часа)
    if in_quiet and notif_type in ("1_day", "2_hours"):
        # Логируем как подавленное, чтобы не слать повторно
        await record_notification_log(
            session=session,
            user_id=user.id,
            notification_type=notif_type,
            target_datetime=occ_dt.replace(tzinfo=None),
            activity_id=activity.id,
            schedule_id=schedule.id,
            status="suppressed_quiet_hours",
        )
        return 0

    sent = 0
    start_str = schedule.start_time.strftime("%H:%M")
    end_str = schedule.end_time.strftime("%H:%M")
    loc_name = activity.location.name if activity.location else None
    loc_addr = activity.location.address if activity.location else None

    # 1. Отправка родителю
    if rem_set.notify_parent:
        already_sent = await is_notification_already_sent(
            session=session,
            user_id=user.id,
            schedule_id=schedule.id,
            notification_type=notif_type,
            target_datetime=occ_dt.replace(tzinfo=None),
        )
        if not already_sent:
            parent_msg = format_parent_reminder_message(
                child_name=child.name,
                activity_icon=activity.icon,
                activity_title=activity.title,
                start_time_str=start_str,
                end_time_str=end_str,
                location_name=loc_name,
                location_address=loc_addr,
                teacher_name=activity.teacher_name,
                items_to_bring=activity.items_to_bring,
                notification_type=notif_type,
            )
            try:
                from bot.keyboards.inline import get_reminder_action_keyboard
                kb = get_reminder_action_keyboard(schedule.id)
                await bot.send_message(
                    chat_id=user.id,
                    text=parent_msg,
                    parse_mode="Markdown",
                    reply_markup=kb,
                )
                await record_notification_log(
                    session=session,
                    user_id=user.id,
                    notification_type=notif_type,
                    target_datetime=occ_dt.replace(tzinfo=None),
                    activity_id=activity.id,
                    schedule_id=schedule.id,
                    status="sent",
                )
                sent += 1
            except Exception as e:
                logger.error(f"Не удалось отправить уведомление родителю {user.id}: {e}")
                await record_notification_log(
                    session=session,
                    user_id=user.id,
                    notification_type=notif_type,
                    target_datetime=occ_dt.replace(tzinfo=None),
                    activity_id=activity.id,
                    schedule_id=schedule.id,
                    status="failed",
                )

    # 2. Отправка ребёнку (если указан его личный Telegram ID)
    if rem_set.notify_child and child.telegram_id:
        child_already_sent = await is_notification_already_sent(
            session=session,
            user_id=child.telegram_id,
            schedule_id=schedule.id,
            notification_type=notif_type,
            target_datetime=occ_dt.replace(tzinfo=None),
        )
        if not child_already_sent:
            child_msg = format_child_reminder_message(
                child_name=child.name,
                activity_icon=activity.icon,
                activity_title=activity.title,
                start_time_str=start_str,
                end_time_str=end_str,
                location_name=loc_name,
                location_address=loc_addr,
                teacher_name=activity.teacher_name,
                items_to_bring=activity.items_to_bring,
                notification_type=notif_type,
            )
            try:
                from bot.keyboards.inline import get_child_activity_keyboard
                kb = get_child_activity_keyboard(schedule.id)
                await bot.send_message(
                    chat_id=child.telegram_id,
                    text=child_msg,
                    parse_mode="Markdown",
                    reply_markup=kb,
                )
                await record_notification_log(
                    session=session,
                    user_id=child.telegram_id,
                    notification_type=notif_type,
                    target_datetime=occ_dt.replace(tzinfo=None),
                    activity_id=activity.id,
                    schedule_id=schedule.id,
                    status="sent",
                )
                sent += 1
            except Exception as e:
                logger.error(f"Не удалось отправить уведомление ребёнку {child.telegram_id}: {e}")
                await record_notification_log(
                    session=session,
                    user_id=child.telegram_id,
                    notification_type=notif_type,
                    target_datetime=occ_dt.replace(tzinfo=None),
                    activity_id=activity.id,
                    schedule_id=schedule.id,
                    status="failed",
                )

    return sent


async def check_and_send_morning_digests(session: AsyncSession, bot_instance) -> int:
    """
    Рассылка утреннего расписания (дайджеста) в заданное пользователем время.
    """
    sent_count = 0
    stmt = (
        select(User)
        .where(
            and_(
                User.is_notifications_enabled == True,
                User.morning_digest_enabled == True,
            )
        )
        .options(
            selectinload(User.children)
            .selectinload(Child.activities)
            .selectinload(Activity.schedules),
            selectinload(User.children)
            .selectinload(Child.activities)
            .selectinload(Activity.location),
        )
    )
    result = await session.execute(stmt)
    users = result.scalars().all()

    for user in users:
        tz = get_tz(user.timezone or "Europe/Moscow")
        user_now = datetime.now(tz) if tz else datetime.now()
        today = user_now.date()

        # Проверяем, наступило ли время утреннего дайджеста
        # Например, если текущее время в пределах 30 минут после назначенного morning_digest_time
        digest_time = user.morning_digest_time or time(8, 0)
        user_digest_dt = localize_datetime(datetime.combine(today, digest_time), tz)

        time_since_digest = (user_now - user_digest_dt).total_seconds()
        # Отправляем, если наступило время и прошло не более 45 минут
        if 0 <= time_since_digest <= 45 * 60:
            target_dt = datetime.combine(today, time(0, 0))
            already_sent = await is_notification_already_sent(
                session=session,
                user_id=user.id,
                schedule_id=None,
                notification_type="morning_digest",
                target_datetime=target_dt,
            )

            if not already_sent:
                # Собираем занятия на сегодня по детям
                activities_by_child: Dict[str, List[Dict[str, Any]]] = {}
                for child in user.children:
                    child_acts = []
                    for act in child.activities:
                        if not act.is_active:
                            continue
                        for sch in act.schedules:
                            if sch.is_cancelled:
                                continue
                            if (sch.is_recurring and sch.day_of_week == today.weekday()) or (
                                not sch.is_recurring and sch.specific_date == today
                            ):
                                loc_name = act.location.name if act.location else ""
                                child_acts.append({
                                    "time_str": f"{sch.start_time.strftime('%H:%M')}–{sch.end_time.strftime('%H:%M')}",
                                    "icon": act.icon,
                                    "title": act.title,
                                    "location": loc_name,
                                    "start_time": sch.start_time,
                                })
                    # Сортируем по времени начала
                    child_acts.sort(key=lambda x: x["start_time"])
                    if child_acts:
                        activities_by_child[child.name] = child_acts

                digest_msg = format_morning_digest_message(
                    recipient_name=user.full_name or "родитель",
                    is_parent=True,
                    activities_by_child=activities_by_child,
                )

                try:
                    await bot_instance.send_message(
                        chat_id=user.id,
                        text=digest_msg,
                        parse_mode="Markdown",
                    )
                    await record_notification_log(
                        session=session,
                        user_id=user.id,
                        notification_type="morning_digest",
                        target_datetime=target_dt,
                        status="sent",
                    )
                    sent_count += 1
                except Exception as e:
                    logger.error(f"Ошибка отправки утреннего дайджеста пользователю {user.id}: {e}")

                # Также отправляем личный дайджест детям, у которых есть Telegram
                for child in user.children:
                    if child.telegram_id and child.name in activities_by_child:
                        child_digest_msg = format_morning_digest_message(
                            recipient_name=child.name,
                            is_parent=False,
                            activities_by_child={child.name: activities_by_child[child.name]},
                        )
                        try:
                            await bot_instance.send_message(
                                chat_id=child.telegram_id,
                                text=child_digest_msg,
                                parse_mode="Markdown",
                            )
                        except Exception as e:
                            logger.error(f"Ошибка отправки дайджеста ребёнку {child.telegram_id}: {e}")

    return sent_count
