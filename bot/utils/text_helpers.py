import random
from typing import Optional, List

CHILD_MOTIVATIONS = [
    "У тебя всё отлично получится! 🌟",
    "Удачной и продуктивной тренировки! 🏆",
    "Новые знания — это суперсила! 🚀",
    "Желаем ярких впечатлений и отличного настроения! ✨",
    "Ты большой молодец! Вперёд к новым победам! 🥇",
    "Пусть занятие пройдёт легко и интересно! 💫",
    "Верь в себя, у тебя всё выйдет! 🎈",
]

CHILD_MORNING_WISHES = [
    "Сегодня тебя ждёт потрясающий и интересный день! ☀️",
    "Пусть день будет наполнен улыбками и успехами! 🌈",
    "Вперёд к новым открытиям и достижениям! 🚀",
    "Желаем отличного настроения и лёгких уроков! ❤️",
    "Пусть всё задуманное сегодня обязательно сбудется! 🌟",
]


def get_random_child_motivation() -> str:
    """Возвращает случайное мотивирующее пожелание для ребёнка."""
    return random.choice(CHILD_MOTIVATIONS)


def get_random_morning_wish() -> str:
    """Возвращает случайное утреннее пожелание."""
    return random.choice(CHILD_MORNING_WISHES)


def format_reminder_countdown_text(notification_type: str) -> str:
    """Текстовое описание времени до начала занятия."""
    mapping = {
        "1_day": "Завтра у тебя занятие!",
        "2_hours": "До занятия осталось 2 часа!",
        "30_min": "До занятия осталось 30 минут!",
        "10_min": "Занятие начнётся всего через 10 минут!",
    }
    return mapping.get(notification_type, "Скоро начнётся занятие!")


def format_child_reminder_message(
    child_name: str,
    activity_icon: str,
    activity_title: str,
    start_time_str: str,
    end_time_str: str,
    location_name: Optional[str],
    location_address: Optional[str],
    teacher_name: Optional[str],
    items_to_bring: Optional[str],
    notification_type: str,
) -> str:
    """Формирует дружелюбное сообщение-напоминание для ребёнка в Telegram."""
    countdown = format_reminder_countdown_text(notification_type)
    motivation = get_random_child_motivation()

    lines = [
        f"👋 Привет, {child_name}!\n",
        f"Сегодня у тебя: {activity_icon} *{activity_title}*",
        f"🕓 Начало: *{start_time_str}* (до {end_time_str})",
    ]

    if location_name or location_address:
        loc_str = location_name or ""
        if location_address:
            loc_str = f"{loc_str} ({location_address})" if loc_str else location_address
        lines.append(f"📍 Место: {loc_str}")

    if teacher_name:
        lines.append(f"👤 Преподаватель: {teacher_name}")

    lines.append(f"\n⏰ *{countdown}*")

    if items_to_bring and items_to_bring.strip():
        lines.append(f"\n🎒 *Не забудь взять:*\n{items_to_bring.strip()} 💧")

    lines.append(f"\n{motivation}")

    return "\n".join(lines)


def format_parent_reminder_message(
    child_name: str,
    activity_icon: str,
    activity_title: str,
    start_time_str: str,
    end_time_str: str,
    location_name: Optional[str],
    location_address: Optional[str],
    teacher_name: Optional[str],
    items_to_bring: Optional[str],
    notification_type: str,
) -> str:
    """Формирует структурированное уведомление для родителя."""
    countdown = format_reminder_countdown_text(notification_type)

    lines = [
        f"🔔 *Напоминание для родителя*",
        f"👧 Ребёнок: *{child_name}*",
        f"📌 Занятие: {activity_icon} *{activity_title}*",
        f"🕓 Время: *{start_time_str} – {end_time_str}*",
    ]

    if location_name or location_address:
        loc_str = location_name or ""
        if location_address:
            loc_str = f"{loc_str} ({location_address})" if loc_str else location_address
        lines.append(f"📍 Место: {loc_str}")

    if teacher_name:
        lines.append(f"👤 Преподаватель: {teacher_name}")

    lines.append(f"⏳ Статус: *{countdown}*")

    if items_to_bring and items_to_bring.strip():
        lines.append(f"🎒 Необходимые вещи: {items_to_bring.strip()}")

    return "\n".join(lines)


def format_morning_digest_message(
    recipient_name: str,
    is_parent: bool,
    activities_by_child: dict,  # {child_name: [activity_dict]}
) -> str:
    """Формирует утренний дайджест со всеми занятиями на день."""
    greeting = f"☀️ *Доброе утро, {recipient_name}!*"
    wish = get_random_morning_wish()

    total_activities = sum(len(acts) for acts in activities_by_child.values())

    if total_activities == 0:
        return (
            f"{greeting}\n\n"
            f"🎉 На сегодня занятий не запланировано!\n"
            f"Можно отлично отдохнуть, погулять или заняться любимым хобби.\n\n"
            f"{wish}"
        )

    lines = [greeting, "\n📋 *Твой план на сегодня:*"]

    for child_name, activities in activities_by_child.items():
        if len(activities_by_child) > 1 or is_parent:
            lines.append(f"\n👧 *{child_name}:*")
        for act in activities:
            time_str = act.get("time_str", "")
            icon = act.get("icon", "📌")
            title = act.get("title", "")
            loc = act.get("location", "")
            loc_suffix = f" _({loc})_" if loc else ""
            lines.append(f"• {icon} *{time_str}* — {title}{loc_suffix}")

    lines.append("\nСегодня насыщенный день! Желаем отличного настроения ❤️")
    return "\n".join(lines)
