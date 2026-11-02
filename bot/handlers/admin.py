import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.services.statistics_service import get_system_statistics

logger = logging.getLogger(__name__)
router = Router(name="admin_router")


def is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь администратором."""
    if not settings.admin_ids:
        # Если ADMIN_IDS не заданы, разрешаем доступ для отладки
        return True
    return user_id in settings.admin_ids


def format_stats_text(stats: dict) -> str:
    """Форматирует метрики бота в читаемый отчёт."""
    types_breakdown = "\n".join([
        f"   • `{ntype}`: {count}" for ntype, count in stats["notifications_by_type"].items()
    ]) or "   • _Пока нет отправленных_"

    lines = [
        "📊 *Панель администратора «Мой распорядок»*\n",
        f"👥 *Пользователи (родители):* `{stats['users_count']}`",
        f"👧 *Профили детей:* `{stats['children_count']}`",
        f"📌 *Всего занятий:* `{stats['total_activities']}` (активных: `{stats['active_activities']}`)",
        f"🗓️ *Слотов расписания:* `{stats['total_schedules']}`",
        "",
        f"📨 *Отправлено напоминаний:* `{stats['total_notifications']}`",
        f"⚠️ *Ошибок отправки:* `{stats['failed_notifications']}`",
        "",
        "*Разбивка напоминаний по типам:*",
        types_breakdown,
    ]
    return "\n".join(lines)


@router.message(Command("admin"))
@router.message(Command("stats"))
async def handle_admin_panel(message: Message, session: AsyncSession):
    """Отображение административной панели со статистикой системы."""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет доступа к административной панели.")
        return

    stats = await get_system_statistics(session)
    text = format_stats_text(stats)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить статистику", callback_data="admin:refresh")],
        [InlineKeyboardButton(text="🔙 Закрыть", callback_data="cancel_action")],
    ])

    await message.answer(text=text, parse_mode="Markdown", reply_markup=kb)


@router.callback_query(F.data == "admin:refresh")
async def callback_admin_refresh(callback: CallbackQuery, session: AsyncSession):
    """Обновление статистики в админке."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён.", show_alert=True)
        return

    stats = await get_system_statistics(session)
    text = format_stats_text(stats)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить статистику", callback_data="admin:refresh")],
        [InlineKeyboardButton(text="🔙 Закрыть", callback_data="cancel_action")],
    ])

    await callback.message.edit_text(text=text, parse_mode="Markdown", reply_markup=kb)
    await callback.answer("Статистика обновлена!")
