import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from bot.services.activity_service import (
    get_all_parent_activities,
    get_activity,
    delete_activity,
    toggle_activity_active,
    toggle_schedule_cancellation,
    mark_schedule_completed,
    get_schedule_item,
    update_activity,
)
from bot.services.user_service import get_children
from bot.keyboards.inline import (
    get_activity_detail_keyboard,
    get_reminder_settings_keyboard,
)
from bot.keyboards.reply import get_main_reply_keyboard, get_cancel_reply_keyboard
from bot.utils.time_utils import get_day_name
from bot.states.fsm import EditActivityFSM

logger = logging.getLogger(__name__)
router = Router(name="manage_activity_router")


def format_activity_detail_text(act) -> str:
    """Форматирует подробную информацию о занятии."""
    child = act.child
    status_str = "🟢 Активно" if act.is_active else "⏸️ На паузе (напоминания выключены)"

    # Расписание
    sch_lines = []
    for s in act.schedules:
        time_str = f"{s.start_time.strftime('%H:%M')} – {s.end_time.strftime('%H:%M')}"
        if s.is_recurring:
            day_str = get_day_name(s.day_of_week)
            sch_lines.append(f"{day_str}: {time_str}")
        else:
            date_str = s.specific_date.strftime("%d.%m.%Y") if s.specific_date else ""
            sch_lines.append(f"Разово ({date_str}): {time_str}")

    schedule_text = ", ".join(sch_lines) if sch_lines else "Не задано"

    lines = [
        f"📌 *{act.icon} {act.title}*",
        f"👧 Ребёнок: *{child.color_emoji} {child.name}*",
        f"🏷️ Направление: *{act.category}*",
        f"⚡ Статус: *{status_str}*",
        f"🗓️ Расписание: *{schedule_text}*",
    ]

    if act.location:
        loc_str = act.location.name
        if act.location.address:
            loc_str += f" ({act.location.address})"
        lines.append(f"📍 Место: {loc_str}")

    if act.teacher_name:
        lines.append(f"👤 Преподаватель: {act.teacher_name}")

    if act.items_to_bring:
        lines.append(f"🎒 Взять с собой: {act.items_to_bring}")

    if act.notes:
        lines.append(f"📝 Заметки: {act.notes}")

    return "\n".join(lines)


@router.message(F.text == "📝 Редактировать занятия")
async def show_activities_list(message: Message, session: AsyncSession):
    """Показывает список всех занятий родителя с кнопками перехода к управлению."""
    activities = await get_all_parent_activities(session, message.from_user.id)

    if not activities:
        await message.answer(
            "📋 У вас пока нет созданных занятий.\n"
            "Нажмите кнопку *«➕ Добавить занятие»*, чтобы создать первое!",
            parse_mode="Markdown",
            reply_markup=get_main_reply_keyboard(),
        )
        return

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    buttons = []
    for act in activities:
        child = act.child
        active_mark = "" if act.is_active else " ⏸️"
        text = f"{act.icon} {act.title} ({child.name}){active_mark}"
        buttons.append([
            InlineKeyboardButton(text=text, callback_data=f"act_detail:{act.id}")
        ])

    buttons.append([InlineKeyboardButton(text="🔙 Закрыть", callback_data="cancel_action")])

    await message.answer(
        "📝 *Выберите занятие для просмотра, редактирования или настройки:*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )


@router.callback_query(F.data == "act_list:back")
async def callback_back_to_list(callback: CallbackQuery, session: AsyncSession):
    """Возврат к списку занятий."""
    activities = await get_all_parent_activities(session, callback.from_user.id)
    if not activities:
        await callback.message.edit_text("Список занятий пуст.")
        return

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    buttons = []
    for act in activities:
        child = act.child
        active_mark = "" if act.is_active else " ⏸️"
        text = f"{act.icon} {act.title} ({child.name}){active_mark}"
        buttons.append([
            InlineKeyboardButton(text=text, callback_data=f"act_detail:{act.id}")
        ])
    buttons.append([InlineKeyboardButton(text="🔙 Закрыть", callback_data="cancel_action")])

    await callback.message.edit_text(
        "📝 *Выберите занятие для управления:*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("act_detail:"))
async def callback_show_activity_detail(callback: CallbackQuery, session: AsyncSession):
    """Отображение карточки занятия."""
    act_id = int(callback.data.split(":")[1])
    act = await get_activity(session, act_id)
    if not act:
        await callback.answer("Занятие не найдено.", show_alert=True)
        return

    text = format_activity_detail_text(act)
    kb = get_activity_detail_keyboard(act.id, act.is_active)

    await callback.message.edit_text(
        text=text,
        parse_mode="Markdown",
        reply_markup=kb,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("act_toggle:"))
async def callback_toggle_activity(callback: CallbackQuery, session: AsyncSession):
    """Переключение активности занятия (пауза/возобновление)."""
    act_id = int(callback.data.split(":")[1])
    new_status = await toggle_activity_active(session, act_id)
    if new_status is None:
        await callback.answer("Занятие не найдено.", show_alert=True)
        return

    status_word = "возобновлено ▶️" if new_status else "приостановлено ⏸️"
    await callback.answer(f"Занятие {status_word}")

    act = await get_activity(session, act_id)
    text = format_activity_detail_text(act)
    kb = get_activity_detail_keyboard(act.id, act.is_active)
    await callback.message.edit_text(text=text, parse_mode="Markdown", reply_markup=kb)


@router.callback_query(F.data.startswith("act_delete:"))
async def callback_delete_activity(callback: CallbackQuery, session: AsyncSession):
    """Удаление занятия."""
    act_id = int(callback.data.split(":")[1])
    success = await delete_activity(session, act_id)
    if success:
        await callback.answer("🗑️ Занятие успешно удалено!", show_alert=True)
        await callback.message.edit_text("✅ Занятие удалено из расписания.")
    else:
        await callback.answer("Не удалось удалить занятие.", show_alert=True)


@router.callback_query(F.data.startswith("act_cancel_today:"))
async def callback_cancel_today(callback: CallbackQuery, session: AsyncSession):
    """Отмена сегодняшнего урока для занятия."""
    act_id = int(callback.data.split(":")[1])
    act = await get_activity(session, act_id)
    if not act or not act.schedules:
        await callback.answer("Нет расписания для отмены.", show_alert=True)
        return

    # Переключаем отмену для первого найденного расписания
    for sch in act.schedules:
        await toggle_schedule_cancellation(session, sch.id)

    await callback.answer("Статус сегодняшнего занятия изменён!")
    await callback.message.edit_text(
        f"Уведомление: сегодняшнее занятие *{act.title}* было отменено / возвращено.",
        parse_mode="Markdown",
    )


# ===================== Notification Interactive Responses =====================

@router.callback_query(F.data.startswith("sch_done:"))
async def callback_sch_done(callback: CallbackQuery, session: AsyncSession):
    """Родитель нажал кнопку 'Занятие посещено'."""
    sch_id = int(callback.data.split(":")[1])
    await mark_schedule_completed(session, sch_id, is_completed=True)
    await callback.answer("Отлично! Занятие отмечено как выполненное 🎉", show_alert=True)
    await callback.message.edit_reply_markup(reply_markup=None)


@router.callback_query(F.data.startswith("sch_cancel:"))
async def callback_sch_cancel(callback: CallbackQuery, session: AsyncSession):
    """Родитель нажал кнопку 'Отменить сегодня' в напоминании."""
    sch_id = int(callback.data.split(":")[1])
    await toggle_schedule_cancellation(session, sch_id)
    await callback.answer("Занятие на сегодня отменено.", show_alert=True)
    await callback.message.edit_reply_markup(reply_markup=None)


@router.callback_query(F.data.startswith("sch_info:"))
async def callback_sch_info(callback: CallbackQuery, session: AsyncSession):
    """Подробная информация из напоминания."""
    sch_id = int(callback.data.split(":")[1])
    sch = await get_schedule_item(session, sch_id)
    if not sch:
        await callback.answer("Информация не найдена.", show_alert=True)
        return

    act = sch.activity
    text = (
        f"ℹ️ *{act.icon} {act.title}*\n"
        f"👧 Ребёнок: {act.child.name}\n"
        f"🕓 Время: {sch.start_time.strftime('%H:%M')} – {sch.end_time.strftime('%H:%M')}\n"
    )
    if act.location:
        text += f"📍 Место: {act.location.name} ({act.location.address})\n"
    if act.teacher_name:
        text += f"👤 Преподаватель: {act.teacher_name}\n"
    if act.items_to_bring:
        text += f"🎒 С собой: {act.items_to_bring}\n"

    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data.startswith("child_ack:"))
async def callback_child_ack(callback: CallbackQuery):
    """Ребёнок нажал '👍 Всё понятно!'."""
    await callback.answer("Отлично! Удачного занятия! 🌟", show_alert=True)
    await callback.message.edit_reply_markup(reply_markup=None)


@router.callback_query(F.data.startswith("child_done:"))
async def callback_child_done(callback: CallbackQuery, session: AsyncSession):
    """Ребёнок нажал '✅ Я на занятии!'."""
    sch_id = int(callback.data.split(":")[1])
    await mark_schedule_completed(session, sch_id, is_completed=True)
    await callback.answer("Молодец! Ты вовремя пришёл на занятие! 🏆", show_alert=True)
    await callback.message.edit_reply_markup(reply_markup=None)
