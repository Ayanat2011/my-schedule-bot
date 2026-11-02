from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def get_main_reply_keyboard() -> ReplyKeyboardMarkup:
    """Главная Reply-клавиатура бота со всеми ключевыми разделами."""
    keyboard = [
        [
            KeyboardButton(text="📅 Моё расписание"),
            KeyboardButton(text="➕ Добавить занятие"),
        ],
        [
            KeyboardButton(text="👧 Мои дети"),
            KeyboardButton(text="📝 Редактировать занятия"),
        ],
        [
            KeyboardButton(text="🔔 Настройки напоминаний"),
            KeyboardButton(text="📍 Места занятий"),
        ],
        [
            KeyboardButton(text="⚙️ Настройки"),
            KeyboardButton(text="❓ Помощь"),
        ],
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        persistent=True,
        input_field_placeholder="Выберите нужный раздел...",
    )


def get_cancel_reply_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура с кнопкой отмены."""
    keyboard = [
        [KeyboardButton(text="❌ Отмена")],
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def get_skip_or_cancel_reply_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура с кнопками пропуска и отмены."""
    keyboard = [
        [KeyboardButton(text="⏭️ Пропустить")],
        [KeyboardButton(text="❌ Отмена")],
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=True,
    )
