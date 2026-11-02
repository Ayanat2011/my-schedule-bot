import logging
from datetime import date, timedelta
from typing import List
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession

from bot.services.user_service import get_user, get_children, get_child
from bot.services.activity_service import (
    get_user_schedule_for_date,
    get_child_schedule_for_date,
    get_schedule_item,
    mark_schedule_completed,
    toggle_schedule_cancellation,
)
from bot.utils.time_utils import (
    get_user_now,
    format_russian_date,
    get_day_name,
    get_week_date_range,
)
from bot.keyboards.inline import get_schedule_view_keyboard, get_children_keyboard
from bot.keyboards.reply import get_main_reply_keyboard

logger = logging.getLogger(__name__)
router = Router(name="schedule_router")


def format_schedule_list_text(schedules, title_header: str) -> str:
    """Форматирует список занятий в красивый текст с эмодзи и деталями."""
    if not schedules:
        return (
            f"📅 *{title_header}*\n\n"
            f"🎉 На этот день занятий не запланировано!\n"
            f"Отличный повод отдохнуть или провести время всей семьёй! 🌈"
        )

    lines = [f"📅 *{title_header}*\n"]

    for i, sch in enumerate(schedules, 1):
        act = sch.activity
        child = act.child
        start_str = sch.start_time.strftime("%H:%M")
        end_str = sch.end_time.strftime("%H:%M")

        status_prefix = ""
        if sch.is_completed:
            status_prefix = "✅ _[Выполнено]_ "
        elif sch.is_cancelled:
            status_prefix = "❌ _[Отменено]_ "

        lines.append(
            f"*{i}.* {status_prefix}{act.icon} *{act.title}* ({child.color_emoji} {child.name})\n"
            f"   🕓 Время: *{start_str} – {end_str}*"
        )

        if act.location:
            loc_str = act.location.name
            if act.location.address:
                loc_str += f" ({act.location.address})"
            lines.append(f"   📍 Место: {loc_str}")

        if act.teacher_name:
            lines.append(f"   👤 Преподаватель: {act.teacher_name}")

        if act.items_to_bring:
            lines.append(f"   🎒 Взять с собой: {act.items_to_bring}")

        lines.append("")  # пустая строка для разделения

    return "\n".join(lines)


@router.message(Command("schedule"))
@router.message(F.text == "📅 Моё расписание")
async def show_schedule_menu(message: Message, session: AsyncSession):
    """Показывает меню расписания и расписание на сегодня."""
    user = await get_user(session, message.from_user.id)
    if not user:
        await message.answer("Сначала запустите бота командой /start", reply_markup=get_main_reply_keyboard())
        return

    user_now = get_user_now(user.timezone)
    today = user_now.date()

    schedules = await get_user_schedule_for_date(session, user.id, today)
    header = f"Расписание на сегодня, {format_russian_date(today)}"
    text = format_schedule_list_text(schedules, header)

    await message.answer(
        text=text,
        parse_mode="Markdown",
        reply_markup=get_schedule_view_keyboard(),
    )


@router.callback_query(F.data == "view_schedule:today")
async def callback_schedule_today(callback: CallbackQuery, session: AsyncSession):
    """Просмотр расписания на сегодня."""
    user = await get_user(session, callback.from_user.id)
    tz = user.timezone if user else "Europe/Moscow"
    user_now = get_user_now(tz)
    today = user_now.date()

    schedules = await get_user_schedule_for_date(session, callback.from_user.id, today)
    header = f"Расписание на сегодня, {format_russian_date(today)}"
    text = format_schedule_list_text(schedules, header)

    await callback.message.edit_text(
        text=text,
        parse_mode="Markdown",
        reply_markup=get_schedule_view_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "view_schedule:tomorrow")
async def callback_schedule_tomorrow(callback: CallbackQuery, session: AsyncSession):
    """Просмотр расписания на завтра."""
    user = await get_user(session, callback.from_user.id)
    tz = user.timezone if user else "Europe/Moscow"
    user_now = get_user_now(tz)
    tomorrow = user_now.date() + timedelta(days=1)

    schedules = await get_user_schedule_for_date(session, callback.from_user.id, tomorrow)
    header = f"Расписание на завтра, {format_russian_date(tomorrow)}"
    text = format_schedule_list_text(schedules, header)

    await callback.message.edit_text(
        text=text,
        parse_mode="Markdown",
        reply_markup=get_schedule_view_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "view_schedule:week")
async def callback_schedule_week(callback: CallbackQuery, session: AsyncSession):
    """Просмотр расписания на всю текущую неделю."""
    user = await get_user(session, callback.from_user.id)
    tz = user.timezone if user else "Europe/Moscow"
    user_now = get_user_now(tz)
    today = user_now.date()
    monday, sunday = get_week_date_range(today)

    lines = [f"🗓️ *Расписание на неделю ({monday.day} – {sunday.day} {format_russian_date(sunday).split()[1]}):*\n"]

    total_week_activities = 0
    current_d = monday
    while current_d <= sunday:
        schedules = await get_user_schedule_for_date(session, callback.from_user.id, current_d)
        day_title = format_russian_date(current_d)
        is_today_mark = " 👈 (Сегодня)" if current_d == today else ""

        if schedules:
            lines.append(f"📌 *{day_title}*{is_today_mark}:")
            for sch in schedules:
                act = sch.activity
                child = act.child
                time_range = f"{sch.start_time.strftime('%H:%M')}–{sch.end_time.strftime('%H:%M')}"
                lines.append(f"  • {act.icon} *{time_range}* — {act.title} ({child.name})")
            lines.append("")
            total_week_activities += len(schedules)
        else:
            lines.append(f"⚪ _{day_title}_: выходной{is_today_mark}\n")

        current_d += timedelta(days=1)

    if total_week_activities == 0:
        lines.append("🎉 На этой неделе пока нет запланированных занятий.")

    await callback.message.edit_text(
        text="\n".join(lines),
        parse_mode="Markdown",
        reply_markup=get_schedule_view_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "view_schedule:by_child")
async def callback_schedule_by_child(callback: CallbackQuery, session: AsyncSession):
    """Выбор ребёнка для фильтрации расписания."""
    children = await get_children(session, callback.from_user.id)
    if not children:
        await callback.answer("У вас пока нет добавленных детей.", show_alert=True)
        return

    kb = get_children_keyboard(children, callback_prefix="sch_child")
    await callback.message.edit_text(
        text="👧 Выберите ребёнка для просмотра расписания:",
        reply_markup=kb,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("sch_child:"))
async def callback_show_child_schedule(callback: CallbackQuery, session: AsyncSession):
    """Показ расписания конкретного ребёнка."""
    child_id = int(callback.data.split(":")[1])
    child = await get_child(session, child_id)
    if not child:
        await callback.answer("Ребёнок не найден.", show_alert=True)
        return

    user = await get_user(session, callback.from_user.id)
    tz = user.timezone if user else "Europe/Moscow"
    user_now = get_user_now(tz)
    today = user_now.date()

    schedules = await get_child_schedule_for_date(session, child_id, today)
    header = f"Расписание: {child.color_emoji} {child.name} на сегодня, {format_russian_date(today)}"
    text = format_schedule_list_text(schedules, header)

    await callback.message.edit_text(
        text=text,
        parse_mode="Markdown",
        reply_markup=get_schedule_view_keyboard(),
    )
    await callback.answer()
