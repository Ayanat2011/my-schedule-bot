import logging
from datetime import time
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
try:
    from zoneinfo import ZoneInfo
    def validate_tz(name: str) -> bool:
        try:
            ZoneInfo(name)
            return True
        except Exception:
            return False
except ImportError:
    try:
        import pytz
        def validate_tz(name: str) -> bool:
            try:
                pytz.timezone(name)
                return True
            except Exception:
                return False
    except ImportError:
        def validate_tz(name: str) -> bool:
            return True

from bot.services.user_service import get_user, update_user_settings
from bot.keyboards.inline import get_user_settings_keyboard, get_timezones_keyboard
from bot.keyboards.reply import get_main_reply_keyboard, get_cancel_reply_keyboard
from bot.utils.time_utils import parse_time
from bot.states.fsm import UserSettingsFSM

logger = logging.getLogger(__name__)
router = Router(name="settings_router")


def format_user_settings_view(user):
    """Форматирует текст и клавиатуру настроек пользователя."""
    quiet_start = user.quiet_hours_start.strftime("%H:%M") if user.quiet_hours_start else "22:00"
    quiet_end = user.quiet_hours_end.strftime("%H:%M") if user.quiet_hours_end else "07:00"
    digest_time = user.morning_digest_time.strftime("%H:%M") if user.morning_digest_time else "08:00"

    kb = get_user_settings_keyboard(
        current_tz=user.timezone or "Europe/Moscow",
        notifications_enabled=user.is_notifications_enabled,
        quiet_hours_enabled=user.quiet_hours_enabled,
        quiet_start_str=quiet_start,
        quiet_end_str=quiet_end,
        digest_enabled=user.morning_digest_enabled,
        digest_time_str=digest_time,
    )

    notif_text = "🟢 Включены" if user.is_notifications_enabled else "🔴 Отключены (пауза)"
    quiet_text = f"🟢 Включены ({quiet_start} – {quiet_end})" if user.quiet_hours_enabled else "⚪ Выключены"
    digest_text = f"🟢 В 08:00 ({digest_time})" if user.morning_digest_enabled else "⚪ Выключено"

    text = (
        "⚙️ *Настройки профиля и уведомлений*\n\n"
        f"🌍 *Часовой пояс:* `{user.timezone}`\n"
        f"🔔 *Все напоминания:* {notif_text}\n"
        f"🌙 *Тихие часы:* {quiet_text}\n"
        f"☀️ *Утренний дайджест:* {digest_text}\n\n"
        "Нажмите на нужную кнопку ниже для изменения параметров:"
    )
    return text, kb


@router.message(Command("settings"))
@router.message(F.text == "⚙️ Настройки")
async def show_settings_menu(message: Message, session: AsyncSession):
    """Открывает меню настроек пользователя."""
    user = await get_user(session, message.from_user.id)
    if not user:
        await message.answer("Сначала запустите бота: /start")
        return

    text, kb = format_user_settings_view(user)
    await message.answer(text=text, parse_mode="Markdown", reply_markup=kb)


@router.callback_query(F.data == "settings:toggle_notifications")
async def callback_toggle_notifications(callback: CallbackQuery, session: AsyncSession):
    """Включение/выключение всех уведомлений (мастер-переключатель)."""
    user = await get_user(session, callback.from_user.id)
    new_val = not user.is_notifications_enabled
    await update_user_settings(session, user.id, is_notifications_enabled=new_val)

    user = await get_user(session, callback.from_user.id)
    text, kb = format_user_settings_view(user)
    await callback.message.edit_text(text=text, parse_mode="Markdown", reply_markup=kb)
    status_str = "включены" if new_val else "приостановлены"
    await callback.answer(f"Все напоминания {status_str}!")


@router.callback_query(F.data == "settings:timezone")
async def callback_open_timezone_picker(callback: CallbackQuery):
    """Открывает клавиатуру выбора часового пояса."""
    await callback.message.edit_text(
        "🌍 *Выберите ваш часовой пояс* из списка популярных или введите вручную:",
        parse_mode="Markdown",
        reply_markup=get_timezones_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("set_tz:"))
async def callback_set_timezone(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Установка выбранного часового пояса."""
    tz_val = callback.data.split(":", 1)[1]

    if tz_val == "manual":
        await state.set_state(UserSettingsFSM.input_custom_timezone)
        await callback.message.delete()
        await callback.message.answer(
            "🌍 Введите название часового пояса по стандарту IANA (например: `Asia/Almaty`, `Europe/Samara`, `Europe/Minsk`):",
            parse_mode="Markdown",
            reply_markup=get_cancel_reply_keyboard(),
        )
        await callback.answer()
        return

    await update_user_settings(session, callback.from_user.id, timezone=tz_val)
    user = await get_user(session, callback.from_user.id)
    text, kb = format_user_settings_view(user)
    await callback.message.edit_text(text=text, parse_mode="Markdown", reply_markup=kb)
    await callback.answer(f"Часовой пояс изменён на {tz_val}!")


@router.message(UserSettingsFSM.input_custom_timezone)
async def process_custom_timezone(message: Message, session: AsyncSession, state: FSMContext):
    """Обработка ручного ввода часового пояса."""
    tz_input = message.text.strip()
    if not validate_tz(tz_input):
        await message.answer(
            "⚠️ Неизвестный часовой пояс! Примеры: `Europe/Moscow`, `Asia/Yekaterinburg`, `Asia/Almaty`.\n"
            "Попробуйте ещё раз или нажмите *«❌ Отмена»*:",
            parse_mode="Markdown",
            reply_markup=get_cancel_reply_keyboard(),
        )
        return

    await update_user_settings(session, message.from_user.id, timezone=tz_input)
    await state.clear()
    await message.answer(
        f"✅ Часовой пояс успешно установлен: `{tz_input}`!",
        parse_mode="Markdown",
        reply_markup=get_main_reply_keyboard(),
    )


@router.callback_query(F.data == "settings:quiet_hours")
async def callback_toggle_quiet_hours(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Переключение или настройка тихих часов."""
    user = await get_user(session, callback.from_user.id)
    new_val = not user.quiet_hours_enabled
    await update_user_settings(session, user.id, quiet_hours_enabled=new_val)

    user = await get_user(session, callback.from_user.id)
    text, kb = format_user_settings_view(user)
    await callback.message.edit_text(text=text, parse_mode="Markdown", reply_markup=kb)
    status_str = "включены" if new_val else "выключены"
    await callback.answer(f"Тихие часы {status_str}!")


@router.callback_query(F.data == "settings:morning_digest")
async def callback_toggle_morning_digest(callback: CallbackQuery, session: AsyncSession):
    """Переключение утреннего дайджеста."""
    user = await get_user(session, callback.from_user.id)
    new_val = not user.morning_digest_enabled
    await update_user_settings(session, user.id, morning_digest_enabled=new_val)

    user = await get_user(session, callback.from_user.id)
    text, kb = format_user_settings_view(user)
    await callback.message.edit_text(text=text, parse_mode="Markdown", reply_markup=kb)
    status_str = "включен" if new_val else "выключен"
    await callback.answer(f"Утренний дайджест {status_str}!")


@router.callback_query(F.data == "settings:back")
async def callback_settings_back(callback: CallbackQuery, session: AsyncSession):
    """Возврат в меню настроек."""
    user = await get_user(session, callback.from_user.id)
    text, kb = format_user_settings_view(user)
    await callback.message.edit_text(text=text, parse_mode="Markdown", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data == "settings:close")
async def callback_settings_close(callback: CallbackQuery):
    """Закрытие меню настроек."""
    await callback.message.delete()
    await callback.answer()
