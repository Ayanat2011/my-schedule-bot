from typing import List, Optional, Set
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.utils.time_utils import DAYS_OF_WEEK, POPULAR_TIMEZONES

# Стандартные категории занятий
ACTIVITY_CATEGORIES = [
    ("Школа", "📚", "Школьные уроки"),
    ("Репетитор", "🧑‍🏫", "Репетитор"),
    ("Английский", "🇬🇧", "Английский язык"),
    ("Музыка", "🎵", "Музыкальная школа"),
    ("Танцы", "💃", "Танцы / Балет"),
    ("Футбол", "⚽", "Футбол"),
    ("Плавание", "🏊", "Плавание"),
    ("Спорт", "🥋", "Спортивная секция"),
    ("Творчество", "🎨", "Творческий кружок"),
    ("Другое", "📌", "Другое занятие"),
]


def get_schedule_view_keyboard(selected_date_str: Optional[str] = None) -> InlineKeyboardMarkup:
    """Клавиатура для переключения режимов просмотра расписания."""
    buttons = [
        [
            InlineKeyboardButton(text="☀️ На сегодня", callback_data="view_schedule:today"),
            InlineKeyboardButton(text="🌅 На завтра", callback_data="view_schedule:tomorrow"),
        ],
        [
            InlineKeyboardButton(text="🗓️ На всю неделю", callback_data="view_schedule:week"),
        ],
        [
            InlineKeyboardButton(text="👧 По детям", callback_data="view_schedule:by_child"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_categories_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора категории занятия."""
    buttons = []
    row = []
    for cat_name, icon, label in ACTIVITY_CATEGORIES:
        btn = InlineKeyboardButton(
            text=f"{icon} {cat_name}",
            callback_data=f"select_cat:{cat_name}:{icon}"
        )
        row.append(btn)
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_days_selector_keyboard(selected_days: Set[int]) -> InlineKeyboardMarkup:
    """Интерактивная клавиатура выбора дней недели (с галочками)."""
    row1 = []
    row2 = []
    for day in DAYS_OF_WEEK:
        idx = day["index"]
        checked = "✅ " if idx in selected_days else ""
        text = f"{checked}{day['short']}"
        btn = InlineKeyboardButton(text=text, callback_data=f"toggle_day:{idx}")
        if idx < 4:
            row1.append(btn)
        else:
            row2.append(btn)

    buttons = [
        row1,
        row2,
        [
            InlineKeyboardButton(text="📅 Разовое занятие (на дату)", callback_data="select_day_type:onetime"),
        ],
        [
            InlineKeyboardButton(text="✅ Готово (продолжить)", callback_data="days_selected_done"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_children_keyboard(children, callback_prefix: str) -> InlineKeyboardMarkup:
    """Клавиатура выбора ребёнка из списка."""
    buttons = []
    for ch in children:
        btn = InlineKeyboardButton(
            text=f"{ch.color_emoji} {ch.name}",
            callback_data=f"{callback_prefix}:{ch.id}"
        )
        buttons.append([btn])
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_locations_keyboard(locations, include_new_btn: bool = True) -> InlineKeyboardMarkup:
    """Клавиатура выбора места проведения занятия."""
    buttons = []
    for loc in locations:
        buttons.append([
            InlineKeyboardButton(
                text=f"📍 {loc.name}",
                callback_data=f"select_loc:{loc.id}"
            )
        ])
    row = [InlineKeyboardButton(text="🚫 Без места", callback_data="select_loc:none")]
    if include_new_btn:
        row.append(InlineKeyboardButton(text="➕ Новое место", callback_data="select_loc:new"))
    buttons.append(row)
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_activity_detail_keyboard(activity_id: int, is_active: bool) -> InlineKeyboardMarkup:
    """Клавиатура управления конкретным занятием."""
    toggle_text = "⏸️ Приостановить" if is_active else "▶️ Активировать"
    buttons = [
        [
            InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"act_edit:{activity_id}"),
            InlineKeyboardButton(text="🔔 Напоминания", callback_data=f"act_reminders:{activity_id}"),
        ],
        [
            InlineKeyboardButton(text=toggle_text, callback_data=f"act_toggle:{activity_id}"),
            InlineKeyboardButton(text="❌ Отменить сегодня", callback_data=f"act_cancel_today:{activity_id}"),
        ],
        [
            InlineKeyboardButton(text="🗑️ Удалить занятие", callback_data=f"act_delete:{activity_id}"),
        ],
        [
            InlineKeyboardButton(text="🔙 Назад к списку", callback_data="act_list:back"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_reminder_settings_keyboard(
    activity_id: int,
    remind_1_day: bool,
    remind_2_hours: bool,
    remind_30_min: bool,
    remind_10_min: bool,
    notify_parent: bool,
    notify_child: bool,
) -> InlineKeyboardMarkup:
    """Клавиатура настройки интервалов напоминаний для занятия."""
    mark = lambda v: "✅" if v else "❌"
    buttons = [
        [
            InlineKeyboardButton(
                text=f"{mark(remind_1_day)} За 1 день (24 ч)",
                callback_data=f"rem_toggle:{activity_id}:1_day"
            ),
        ],
        [
            InlineKeyboardButton(
                text=f"{mark(remind_2_hours)} За 2 часа",
                callback_data=f"rem_toggle:{activity_id}:2_hours"
            ),
        ],
        [
            InlineKeyboardButton(
                text=f"{mark(remind_30_min)} За 30 минут",
                callback_data=f"rem_toggle:{activity_id}:30_min"
            ),
        ],
        [
            InlineKeyboardButton(
                text=f"{mark(remind_10_min)} За 10 минут",
                callback_data=f"rem_toggle:{activity_id}:10_min"
            ),
        ],
        [
            InlineKeyboardButton(
                text=f"{mark(notify_parent)} Уведомлять меня (родителя)",
                callback_data=f"rem_toggle:{activity_id}:parent"
            ),
        ],
        [
            InlineKeyboardButton(
                text=f"{mark(notify_child)} Уведомлять ребёнка в Telegram",
                callback_data=f"rem_toggle:{activity_id}:child"
            ),
        ],
        [
            InlineKeyboardButton(
                text="🔙 Назад к занятию",
                callback_data=f"act_detail:{activity_id}"
            ),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_user_settings_keyboard(
    current_tz: str,
    notifications_enabled: bool,
    quiet_hours_enabled: bool,
    quiet_start_str: str,
    quiet_end_str: str,
    digest_enabled: bool,
    digest_time_str: str,
) -> InlineKeyboardMarkup:
    """Клавиатура основных настроек профиля."""
    notif_mark = "Включены ✅" if notifications_enabled else "Отключены ❌"
    quiet_mark = f"Вкл ({quiet_start_str}-{quiet_end_str}) ✅" if quiet_hours_enabled else "Выключены ❌"
    digest_mark = f"Вкл ({digest_time_str}) ☀️" if digest_enabled else "Выключен ❌"

    buttons = [
        [
            InlineKeyboardButton(
                text=f"🌍 Часовой пояс: {current_tz.split('/')[-1]}",
                callback_data="settings:timezone"
            ),
        ],
        [
            InlineKeyboardButton(
                text=f"🔔 Все напоминания: {notif_mark}",
                callback_data="settings:toggle_notifications"
            ),
        ],
        [
            InlineKeyboardButton(
                text=f"🌙 Тихие часы: {quiet_mark}",
                callback_data="settings:quiet_hours"
            ),
        ],
        [
            InlineKeyboardButton(
                text=f"☀️ Утреннее расписание: {digest_mark}",
                callback_data="settings:morning_digest"
            ),
        ],
        [
            InlineKeyboardButton(text="🔙 Закрыть", callback_data="settings:close"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_timezones_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура популярных часовых поясов."""
    buttons = []
    for tz_code, label in POPULAR_TIMEZONES:
        buttons.append([
            InlineKeyboardButton(text=label, callback_data=f"set_tz:{tz_code}")
        ])
    buttons.append([
        InlineKeyboardButton(text="✍️ Ввести вручную", callback_data="set_tz:manual"),
        InlineKeyboardButton(text="🔙 Назад", callback_data="settings:back"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_reminder_action_keyboard(schedule_id: int) -> InlineKeyboardMarkup:
    """Интерактивные кнопки, прикрепляемые к напоминанию о занятии."""
    buttons = [
        [
            InlineKeyboardButton(text="✅ Занятие посещено", callback_data=f"sch_done:{schedule_id}"),
            InlineKeyboardButton(text="❌ Отменить сегодня", callback_data=f"sch_cancel:{schedule_id}"),
        ],
        [
            InlineKeyboardButton(text="ℹ️ Подробнее", callback_data=f"sch_info:{schedule_id}"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_child_activity_keyboard(schedule_id: int) -> InlineKeyboardMarkup:
    """Кнопки для сообщения ребёнку."""
    buttons = [
        [
            InlineKeyboardButton(text="👍 Всё понятно!", callback_data=f"child_ack:{schedule_id}"),
            InlineKeyboardButton(text="✅ Я на занятии!", callback_data=f"child_done:{schedule_id}"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
