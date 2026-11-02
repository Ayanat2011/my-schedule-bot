import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from bot.services.user_service import get_or_create_user, get_children
from bot.keyboards.reply import get_main_reply_keyboard
from bot.keyboards.inline import get_schedule_view_keyboard

logger = logging.getLogger(__name__)
router = Router(name="common_router")


@router.message(CommandStart())
async def handle_start(message: Message, session: AsyncSession, state: FSMContext):
    """Обработчик команды /start."""
    await state.clear()
    user = await get_or_create_user(
        session=session,
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
    )

    children = await get_children(session, user.id)

    welcome_text = (
        f"👋 *Здравствуйте, {message.from_user.first_name}!*\n\n"
        f"Добро пожаловать в бота *«Мой распорядок»* — вашего надёжного семейного помощника "
        f"по расписанию и умным напоминаниям! 🗓️✨\n\n"
        f"🎯 *Что умеет этот бот:*\n"
        f"• Хранить расписание уроков, секций, кружков и репетиторов для всех ваших детей.\n"
        f"• Отправлять умные напоминания за 1 день, 2 часа, 30 и 10 минут.\n"
        f"• Напоминать взять нужные вещи: спортивную форму, воду, учебники, инструмент 🎒\n"
        f"• Присылать бодрое утреннее расписание на день ☀️\n"
        f"• Уведомлять как родителя, так и самого ребёнка в Telegram 👧👦\n\n"
    )

    if not children:
        welcome_text += (
            "💡 *С чего начать:*\n"
            "У вас пока не добавлено ни одного ребёнка. Нажмите кнопку *«👧 Мои дети»* "
            "или *«➕ Добавить занятие»*, чтобы создать первый профиль!"
        )
    else:
        children_names = ", ".join([f"{ch.color_emoji} {ch.name}" for ch in children])
        welcome_text += f"👧 *Ваши дети в системе:* {children_names}\n\nВыберите нужный раздел в меню ниже 👇"

    await message.answer(
        text=welcome_text,
        parse_mode="Markdown",
        reply_markup=get_main_reply_keyboard(),
    )


@router.message(Command("help"))
@router.message(F.text == "❓ Помощь")
async def handle_help(message: Message):
    """Обработчик справки и помощи."""
    help_text = (
        "📖 *Руководство по использованию бота «Мой распорядок»*\n\n"
        "🔹 *1. Добавление детей (👧 Мои дети)*\n"
        "Добавьте имена и возраст детей. Если у ребёнка есть свой Telegram-аккаунт, "
        "вы можете указать его ID, и ребёнок будет получать личные добрые и мотивирующие напоминания!\n\n"
        "🔹 *2. Расписание (📅 Моё расписание)*\n"
        "Смотрите планы на сегодня, завтра или всю неделю. Можно фильтровать по конкретному ребёнку.\n\n"
        "🔹 *3. Добавление занятий (➕ Добавить занятие)*\n"
        "Укажите название, категорию, дни недели, время, место проведения, преподавателя "
        "и список вещей, которые нужно не забыть взять.\n\n"
        "🔹 *4. Умные напоминания (🔔 Настройки напоминаний)*\n"
        "Автоматические напоминания приходят:\n"
        "• За 1 день\n"
        "• За 2 часа\n"
        "• За 30 минут\n"
        "• За 10 минут\n"
        "Вы можете гибко отключать или включать любые интервалы для каждого занятия.\n\n"
        "🔹 *5. Места занятий (📍 Места занятий)*\n"
        "Сохраняйте адреса школ, бассейнов и студий, чтобы не вводить их каждый раз заново.\n\n"
        "🔹 *6. Настройки (⚙️ Настройки)*\n"
        "Настройте ваш часовой пояс, время утреннего дайджеста и «тихие часы», "
        "в которые бот не будет вас беспокоить.\n\n"
        "💡 *Команды бота:*\n"
        "/start — Главное меню\n"
        "/schedule — Расписание\n"
        "/add — Добавить занятие\n"
        "/children — Мои дети\n"
        "/settings — Настройки бота\n"
        "/cancel — Отмена текущего действия"
    )
    await message.answer(help_text, parse_mode="Markdown", reply_markup=get_main_reply_keyboard())


@router.message(Command("cancel"))
@router.message(F.text == "❌ Отмена")
async def handle_cancel_text(message: Message, state: FSMContext):
    """Сброс FSM-состояния по тексту кнопки."""
    current_state = await state.get_state()
    if current_state:
        await state.clear()
        await message.answer("Действие отменено. Возвращаемся в главное меню.", reply_markup=get_main_reply_keyboard())
    else:
        await message.answer("Главное меню:", reply_markup=get_main_reply_keyboard())


@router.callback_query(F.data == "cancel_action")
async def handle_cancel_callback(callback: CallbackQuery, state: FSMContext):
    """Сброс FSM-состояния по Inline кнопке."""
    await state.clear()
    await callback.message.edit_text("❌ Действие отменено.")
    await callback.answer()
