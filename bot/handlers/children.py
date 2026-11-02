import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from bot.states.fsm import AddChildFSM
from bot.services.user_service import (
    get_children,
    create_child,
    get_child,
    update_child,
    delete_child,
)
from bot.keyboards.reply import (
    get_main_reply_keyboard,
    get_cancel_reply_keyboard,
    get_skip_or_cancel_reply_keyboard,
)

logger = logging.getLogger(__name__)
router = Router(name="children_router")

CHILD_EMOJIS = ["👧", "👦", "🧒", "🌟", "⚽", "🎨", "🚀", "🩰", "🏊", "🎸"]


@router.message(Command("children"))
@router.message(F.text == "👧 Мои дети")
async def show_children_list(message: Message, session: AsyncSession):
    """Отображает список всех детей пользователя и кнопку добавления."""
    children = await get_children(session, message.from_user.id)

    if not children:
        text = (
            "👧 *У вас пока нет добавленных детей.*\n\n"
            "Добавьте профиль ребёнка, чтобы начать вести расписание уроков и секций!"
        )
        buttons = [
            [InlineKeyboardButton(text="➕ Добавить ребёнка", callback_data="child_add:new")]
        ]
    else:
        text = "👧 *Профили ваших детей:*\n\n"
        buttons = []
        for ch in children:
            age_str = f", {ch.age} лет" if ch.age else ""
            tg_status = f"✅ Telegram привязан (`{ch.telegram_id}`)" if ch.telegram_id else "⚪ Telegram не привязан"
            act_count = len(ch.activities) if ch.activities else 0

            text += (
                f"{ch.color_emoji} *{ch.name}*{age_str}\n"
                f"   • Занятий: {act_count}\n"
                f"   • {tg_status}\n\n"
            )
            buttons.append([
                InlineKeyboardButton(
                    text=f"{ch.color_emoji} {ch.name} — Управление",
                    callback_data=f"child_view:{ch.id}"
                )
            ])
        buttons.append([InlineKeyboardButton(text="➕ Добавить ещё ребёнка", callback_data="child_add:new")])

    buttons.append([InlineKeyboardButton(text="🔙 Закрыть", callback_data="cancel_action")])

    await message.answer(
        text=text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )


@router.callback_query(F.data == "child_add:new")
async def start_add_child(callback: CallbackQuery, state: FSMContext):
    """Начало FSM добавления нового ребёнка."""
    await state.clear()
    await state.set_state(AddChildFSM.input_name)

    await callback.message.delete()
    await callback.message.answer(
        "👧 *Добавление профиля ребёнка*\n\n"
        "Введите *имя ребёнка* (например: _Алиса_, _Максим_, _Данил_):",
        parse_mode="Markdown",
        reply_markup=get_cancel_reply_keyboard(),
    )
    await callback.answer()


@router.message(AddChildFSM.input_name)
async def process_child_name(message: Message, state: FSMContext):
    """Обработка имени ребёнка."""
    name = message.text.strip()
    if not name or len(name) > 50:
        await message.answer("Пожалуйста, введите корректное имя (до 50 символов):")
        return

    await state.update_data(name=name)
    await state.set_state(AddChildFSM.input_age)

    await message.answer(
        f"Имя: *{name}*\n\n"
        f"Введите *возраст ребёнка* (например: `10`) или нажмите *«⏭️ Пропустить»*:",
        parse_mode="Markdown",
        reply_markup=get_skip_or_cancel_reply_keyboard(),
    )


@router.message(AddChildFSM.input_age)
async def process_child_age(message: Message, state: FSMContext):
    """Обработка возраста ребёнка."""
    text = message.text.strip()
    age = None
    if text != "⏭️ Пропустить":
        if text.isdigit() and 1 <= int(text) <= 25:
            age = int(text)
        else:
            await message.answer(
                "Пожалуйста, введите возраст числом (от 1 до 25) или нажмите *«⏭️ Пропустить»*:",
                parse_mode="Markdown",
                reply_markup=get_skip_or_cancel_reply_keyboard(),
            )
            return

    await state.update_data(age=age)
    await state.set_state(AddChildFSM.select_emoji)

    # Клавиатура выбора иконки
    row1 = [InlineKeyboardButton(text=em, callback_data=f"child_em:{em}") for em in CHILD_EMOJIS[:5]]
    row2 = [InlineKeyboardButton(text=em, callback_data=f"child_em:{em}") for em in CHILD_EMOJIS[5:]]
    kb = InlineKeyboardMarkup(inline_keyboard=[row1, row2])

    await message.answer(
        "Выберите значок-эмодзи для профиля ребёнка:",
        reply_markup=kb,
    )


@router.callback_query(AddChildFSM.select_emoji, F.data.startswith("child_em:"))
async def process_child_emoji(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора эмодзи."""
    em = callback.data.split(":")[1]
    await state.update_data(emoji=em)
    await state.set_state(AddChildFSM.input_telegram_id)

    await callback.message.delete()
    await callback.message.answer(
        f"Значок выбран: {em}\n\n"
        f"📱 *Привязка Telegram ребёнка (необязательно)*\n\n"
        f"Если у ребёнка есть свой Telegram и вы хотите, чтобы он получал личные бодрые "
        f"напоминания и утренний план на день, укажите его числовой *Telegram ID* (например, `987654321`).\n\n"
        f"💡 _Узнать свой ID ребёнок может в боте @userinfobot._\n\n"
        f"Если привязывать не нужно, просто нажмите *«⏭️ Пропустить»*:",
        parse_mode="Markdown",
        reply_markup=get_skip_or_cancel_reply_keyboard(),
    )
    await callback.answer()


@router.message(AddChildFSM.input_telegram_id)
async def process_child_telegram_id(message: Message, session: AsyncSession, state: FSMContext):
    """Обработка привязки Telegram ID и создание профиля в БД."""
    text = message.text.strip()
    tg_id = None
    if text != "⏭️ Пропустить":
        if text.isdigit():
            tg_id = int(text)
        else:
            await message.answer(
                "ID должен состоять только из цифр. Попробуйте ещё раз или нажмите *«⏭️ Пропустить»*:",
                reply_markup=get_skip_or_cancel_reply_keyboard(),
            )
            return

    data = await state.get_data()
    child = await create_child(
        session=session,
        parent_id=message.from_user.id,
        name=data["name"],
        age=data.get("age"),
        color_emoji=data.get("emoji", "👧"),
        telegram_id=tg_id,
    )
    await state.clear()

    age_info = f", возраст: {child.age} лет" if child.age else ""
    tg_info = f"\n📱 Личный Telegram привязан (`{child.telegram_id}`)" if child.telegram_id else ""

    await message.answer(
        f"🎉 *Профиль ребёнка успешно создан!*\n\n"
        f"{child.color_emoji} *{child.name}*{age_info}{tg_info}\n\n"
        f"Теперь вы можете добавить для него уроки и кружки с помощью кнопки *«➕ Добавить занятие»*!",
        parse_mode="Markdown",
        reply_markup=get_main_reply_keyboard(),
    )


@router.callback_query(F.data.startswith("child_view:"))
async def callback_child_view(callback: CallbackQuery, session: AsyncSession):
    """Просмотр и управление профилем ребёнка."""
    child_id = int(callback.data.split(":")[1])
    child = await get_child(session, child_id)
    if not child:
        await callback.answer("Профиль не найден.", show_alert=True)
        return

    age_str = f"{child.age} лет" if child.age else "не указан"
    tg_status = f"`{child.telegram_id}`" if child.telegram_id else "не привязан"

    text = (
        f"👧 *Профиль ребёнка:* {child.color_emoji} *{child.name}*\n\n"
        f"🎂 Возраст: {age_str}\n"
        f"📱 Telegram: {tg_status}\n"
        f"📚 Занятий в расписании: {len(child.activities)}\n"
    )

    buttons = [
        [
            InlineKeyboardButton(text="🗑️ Удалить профиль", callback_data=f"child_del:{child.id}"),
        ],
        [
            InlineKeyboardButton(text="🔙 Назад к списку", callback_data="child_back:list"),
        ]
    ]

    await callback.message.edit_text(
        text=text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await callback.answer()


@router.callback_query(F.data == "child_back:list")
async def callback_child_back_list(callback: CallbackQuery, session: AsyncSession):
    """Возврат к списку детей."""
    children = await get_children(session, callback.from_user.id)
    buttons = []
    text = "👧 *Профили ваших детей:*\n\n"
    for ch in children:
        buttons.append([
            InlineKeyboardButton(
                text=f"{ch.color_emoji} {ch.name} — Управление",
                callback_data=f"child_view:{ch.id}"
            )
        ])
    buttons.append([InlineKeyboardButton(text="➕ Добавить ещё ребёнка", callback_data="child_add:new")])
    buttons.append([InlineKeyboardButton(text="🔙 Закрыть", callback_data="cancel_action")])

    await callback.message.edit_text(
        text=text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("child_del:"))
async def callback_child_del(callback: CallbackQuery, session: AsyncSession):
    """Удаление профиля ребёнка."""
    child_id = int(callback.data.split(":")[1])
    success = await delete_child(session, child_id)
    if success:
        await callback.answer("Профиль ребёнка и его занятия удалены.", show_alert=True)
        await callback.message.edit_text("✅ Профиль успешно удалён.")
    else:
        await callback.answer("Не удалось удалить профиль.", show_alert=True)
