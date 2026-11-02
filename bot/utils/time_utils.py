from datetime import datetime, date, time, timedelta, timezone
from typing import Tuple, Optional, List

try:
    from zoneinfo import ZoneInfo
except ImportError:
    try:
        from pytz import timezone as ZoneInfo
    except ImportError:
        ZoneInfo = None

DAYS_OF_WEEK = [
    {"index": 0, "short": "Пн", "full": "Понедельник"},
    {"index": 1, "short": "Вт", "full": "Вторник"},
    {"index": 2, "short": "Ср", "full": "Среда"},
    {"index": 3, "short": "Чт", "full": "Четверг"},
    {"index": 4, "short": "Пт", "full": "Пятница"},
    {"index": 5, "short": "Сб", "full": "Суббота"},
    {"index": 6, "short": "Вс", "full": "Воскресенье"},
]

POPULAR_TIMEZONES = [
    ("Europe/Kaliningrad", "Калининград (UTC+2)"),
    ("Europe/Moscow", "Москва (UTC+3)"),
    ("Europe/Samara", "Самара (UTC+4)"),
    ("Asia/Yekaterinburg", "Екатеринбург (UTC+5)"),
    ("Asia/Almaty", "Алматы / Астана (UTC+5)"),
    ("Asia/Omsk", "Омск (UTC+6)"),
    ("Asia/Krasnoyarsk", "Красноярск (UTC+7)"),
    ("Asia/Irkutsk", "Иркутск (UTC+8)"),
    ("Asia/Yakutsk", "Якутск (UTC+9)"),
    ("Asia/Vladivostok", "Владивосток (UTC+10)"),
    ("Asia/Magadan", "Магадан (UTC+11)"),
    ("Asia/Kamchatka", "Камчатка (UTC+12)"),
]


def get_day_name(day_index: int, short: bool = False) -> str:
    """Возвращает название дня недели по его индексу (0-6)."""
    if 0 <= day_index < 7:
        return DAYS_OF_WEEK[day_index]["short"] if short else DAYS_OF_WEEK[day_index]["full"]
    return "Неизвестный день"


def parse_time(time_str: str) -> Optional[time]:
    """Парсит строку времени в объект time (поддерживает форматы HH:MM, HH.MM, H:MM)."""
    cleaned = time_str.strip().replace(".", ":").replace("-", ":")
    parts = cleaned.split(":")
    if len(parts) == 2:
        try:
            h, m = int(parts[0]), int(parts[1])
            if 0 <= h <= 23 and 0 <= m <= 59:
                return time(hour=h, minute=m)
        except ValueError:
            return None
    return None


def format_time_range(start_t: time, end_t: time) -> str:
    """Форматирует диапазон времени: 14:00 - 15:30."""
    return f"{start_t.strftime('%H:%M')} – {end_t.strftime('%H:%M')}"


def get_user_now(tz_name: str = "Europe/Moscow") -> datetime:
    """Возвращает текущее время в часовом поясе пользователя."""
    if ZoneInfo:
        try:
            tz = ZoneInfo(tz_name)
            return datetime.now(tz)
        except Exception:
            pass
    # Fallback на системное время или UTC
    return datetime.now()


def is_in_quiet_hours(current_time: time, start_q: Optional[time], end_q: Optional[time]) -> bool:
    """
    Проверяет, попадает ли current_time в интервал тихих часов.
    Корректно обрабатывает интервалы с переходом через полночь (например, 22:00 -> 07:00).
    """
    if not start_q or not end_q:
        return False

    if start_q == end_q:
        return False

    if start_q < end_q:
        # Простой интервал внутри одних суток (например, 13:00 - 15:00)
        return start_q <= current_time < end_q
    else:
        # Интервал с переходом через полночь (например, 22:00 - 07:00)
        return current_time >= start_q or current_time < end_q


def get_date_for_day_of_week(base_date: date, target_day_of_week: int) -> date:
    """
    Возвращает ближайшую дату с заданным днем недели в текущей неделе
    или ближайшую будущую дату.
    """
    days_ahead = target_day_of_week - base_date.weekday()
    return base_date + timedelta(days=days_ahead)


def get_week_date_range(base_date: date) -> Tuple[date, date]:
    """Возвращает понедельник и воскресенье для недели, содержащей base_date."""
    monday = base_date - timedelta(days=base_date.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday


def format_russian_date(d: date) -> str:
    """Форматирует дату по-русски: например, '15 ноября (Среда)'."""
    months = [
        "января", "февраля", "марта", "апреля", "мая", "июня",
        "июля", "августа", "сентября", "октября", "ноября", "декабря"
    ]
    month_name = months[d.month - 1]
    day_name = get_day_name(d.weekday(), short=False)
    return f"{d.day} {month_name} ({day_name})"
