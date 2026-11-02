import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession

from bot.services.activity_service import (
    get_all_parent_activities,
    get_activity,
    update_reminder_settings,
)
from bot.keyboards.inline import get_reminder_settings_keyboard
from bot.keyboards.reply import get_main_reply_keyboard

logger = logging.getLogger(__name__)
router = Router(name="reminders_router")


@router.message(F.text == "🔔 Настройки напоминаний")
async def show_reminders_overview(message: Message, session: AsyncSession):
    """Показывает список занятий для настройки умных напоминаний."""
    activities = await get_all_parent_activities(session, message.from_user.id)

    if not activities:
        await message.answer(
            "🔔 *Умные напоминания*\n\n"
            "У вас пока нет созданных занятий. Добавьте занятия через кнопку *«➕ Добавить занятие»*, "
            "и система автоматически настроит для них напоминания!",
            parse_mode="Markdown",
            reply_markup=get_main_reply_keyboard(),
        )
        return

    text = (
        "🔔 *Настройка напоминаний по занятиям*\n\n"
        "Выберите занятие, чтобы настроить интервалы уведомлений:\n"
        "_(за 1 день, за 2 часа, за 30 минут или за 10 минут)_ 👇"
    )

    buttons = []
    for act in activities:
        child = act.child
        buttons.append([
            InlineKeyboardButton(
                text=f"{act.icon} {act.title} ({child.name})",
                callback_data=f"act_reminders:{act.id}"
            )
        ])
    buttons.append([InlineKeyboardButton(text="🔙 Закрыть", callback_data="cancel_action")])

    await message.answer(
        text=text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )


@router.callback_query(F.data.startswith("act_reminders:"))
async def callback_show_reminder_settings(callback: CallbackQuery, session: AsyncSession):
    """Отображение клавиатуры переключения напоминаний для конкретного занятия."""
    act_id = int(callback.data.split(":")[1])
    act = await get_activity(session, act_id)
    if not act or not act.reminder_setting:
        await callback.answer("Настройки напоминаний не найдены.", show_alert=True)
        return

    rem = act.reminder_setting
    kb = get_reminder_settings_keyboard(
        activity_id=act.id,
        remind_1_day=rem.remind_1_day,
        remind_2_hours=rem.remind_2_hours,
        remind_30_min=rem.remind_30_min,
        remind_10_min=rem.remind_10_min,
        notify_parent=rem.notify_parent,
        notify_child=rem.notify_child,
    )

    text = (
        f"🔔 *Настройки напоминаний для:* {act.icon} *{act.title}*\n"
        f"👧 Ребёнок: *{act.child.name}*\n\n"
        f"Нажмите на нужный пункт, чтобы включить или выключить:"
    )

    await callback.message.edit_text(text=text, parse_mode="Markdown", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("rem_toggle:"))
async def callback_toggle_reminder_option(callback: CallbackQuery, session: AsyncSession):
    """Интерактивное переключение одного из параметров напоминания."""
    parts = callback.data.split(":")
    act_id = int(parts[1])
    option = parts[2]

    act = await get_activity(session, act_id)
    if not act or not act.reminder_setting:
        await callback.answer("Ошибка обновления.", show_alert=True)
        return

    rem = act.reminder_setting
    updates = {}

    if option == "1_day":
        updates["remind_1_day"] = not rem.remind_1_day
    elif option == "2_hours":
        updates["remind_2_hours"] = not rem.remind_2_hours
    elif option == "30_min":
        updates["remind_30_min"] = not rem.remind_30_min
    elif option == "10_min":
        updates["remind_10_min"] = not rem.remind_10_min
    elif option == "parent":
        updates["notify_parent"] = not rem.notify_parent
    elif option == "child":
        updates["notify_child"] = not rem.notify_child

    updated_rem = await update_reminder_settings(session, act_id, **updates)

    kb = get_reminder_settings_keyboard(
        activity_id=act.id,
        remind_1_day=updated_rem.remind_1_day,
        remind_2_hours=updated_rem.remind_2_hours,
        remind_30_min=updated_rem.remind_30_min,
        remind_10_min=updated_rem.remind_10_min,
        notify_parent=updated_rem.notify_parent,
        notify_child=updated_rem.notify_child,
    )

    text = (
        f"🔔 *Настройки напоминаний для:* {act.icon} *{act.title}*\n"
        f"👧 Ребёнок: *{act.child.name}*\n\n"
        f"Настройки сохранены! Нажмите на пункт, чтобы изменить:"
    )

    await callback.message.edit_text(text=text, parse_mode="Markdown", reply_markup=kb)
    await callback.answer("Настройка обновлена!")
