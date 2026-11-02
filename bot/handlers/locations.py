import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from bot.states.fsm import AddLocationFSM
from bot.services.activity_service import (
    get_locations,
    create_location,
    delete_location,
    get_location,
)
from bot.keyboards.reply import (
    get_main_reply_keyboard,
    get_cancel_reply_keyboard,
    get_skip_or_cancel_reply_keyboard,
)

logger = logging.getLogger(__name__)
router = Router(name="locations_router")


@router.message(F.text == "📍 Места занятий")
async def show_locations_list(message: Message, session: AsyncSession):
    """Показывает список всех сохранённых мест занятий."""
    locations = await get_locations(session, message.from_user.id)

    if not locations:
        text = (
            "📍 *Сохранённые места проведения занятий*\n\n"
            "У вас пока нет сохранённых мест. Сохраняйте адреса школ, бассейнов "
            "и спортивных секций, чтобы быстро выбирать их при создании расписания!"
        )
        buttons = [
            [InlineKeyboardButton(text="➕ Добавить новое место", callback_data="loc_add:new")]
        ]
    else:
        text = "📍 *Ваши сохранённые места занятий:*\n\n"
        buttons = []
        for loc in locations:
            note_str = f"\n   _Примечание: {loc.note}_" if loc.note else ""
            text += f"🏢 *{loc.name}*\n   📍 {loc.address or 'Адрес не указан'}{note_str}\n\n"
            buttons.append([
                InlineKeyboardButton(text=f"🗑️ Удалить «{loc.name}»", callback_data=f"loc_del:{loc.id}")
            ])
        buttons.append([InlineKeyboardButton(text="➕ Добавить ещё место", callback_data="loc_add:new")])

    buttons.append([InlineKeyboardButton(text="🔙 Закрыть", callback_data="cancel_action")])

    await message.answer(
        text=text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )


@router.callback_query(F.data == "loc_add:new")
async def start_add_location(callback: CallbackQuery, state: FSMContext):
    """Начало мастера добавления места."""
    await state.clear()
    await state.set_state(AddLocationFSM.input_name)

    await callback.message.delete()
    await callback.message.answer(
        "📍 *Добавление места занятия*\n\n"
        "Введите *название места* (например: _«Школа №12»_, _«Дворец спорта Юность»_, _«Студия танца»_):",
        parse_mode="Markdown",
        reply_markup=get_cancel_reply_keyboard(),
    )
    await callback.answer()


@router.message(AddLocationFSM.input_name)
async def process_location_name(message: Message, state: FSMContext):
    """Ввод названия места."""
    name = message.text.strip()
    if not name or len(name) > 100:
        await message.answer("Пожалуйста, введите корректное название (до 100 символов):")
        return

    await state.update_data(name=name)
    await state.set_state(AddLocationFSM.input_address)

    await message.answer(
        f"Название: *{name}*\n\n"
        f"Введите *адрес* (например: _«ул. Победы, д. 14, каб. 3»_) или нажмите *«⏭️ Пропустить»*:",
        parse_mode="Markdown",
        reply_markup=get_skip_or_cancel_reply_keyboard(),
    )


@router.message(AddLocationFSM.input_address)
async def process_location_address(message: Message, state: FSMContext):
    """Ввод адреса места."""
    text = message.text.strip()
    address = "" if text == "⏭️ Пропустить" else text

    await state.update_data(address=address)
    await state.set_state(AddLocationFSM.input_note)

    await message.answer(
        "📝 Введите дополнительное примечание (например: _«Вход со двора, домофон 15»_) "
        "или нажмите *«⏭️ Пропустить»*:",
        parse_mode="Markdown",
        reply_markup=get_skip_or_cancel_reply_keyboard(),
    )


@router.message(AddLocationFSM.input_note)
async def process_location_note(message: Message, session: AsyncSession, state: FSMContext):
    """Ввод примечания и сохранение локации."""
    text = message.text.strip()
    note = None if text == "⏭️ Пропустить" else text

    data = await state.get_data()
    loc = await create_location(
        session=session,
        user_id=message.from_user.id,
        name=data["name"],
        address=data["address"],
        note=note,
    )
    await state.clear()

    await message.answer(
        f"🎉 Место *«{loc.name}»* успешно добавлено!\n"
        f"Теперь вы можете быстро выбирать его при создании расписания.",
        parse_mode="Markdown",
        reply_markup=get_main_reply_keyboard(),
    )


@router.callback_query(F.data.startswith("loc_del:"))
async def callback_location_delete(callback: CallbackQuery, session: AsyncSession):
    """Удаление сохранённого места."""
    loc_id = int(callback.data.split(":")[1])
    success = await delete_location(session, loc_id, callback.from_user.id)
    if success:
        await callback.answer("Место удалено.", show_alert=True)
        await callback.message.edit_text("✅ Место проведения успешно удалено.")
    else:
        await callback.answer("Не удалось удалить место.", show_alert=True)
