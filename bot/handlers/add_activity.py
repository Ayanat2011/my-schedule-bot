import logging
from datetime import datetime, date
from typing import Set
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from bot.states.fsm import AddActivityFSM, AddChildFSM
from bot.services.user_service import get_user, get_children, get_child
from bot.services.activity_service import (
    create_activity,
    get_locations,
    create_location,
)
from bot.utils.time_utils import (
    parse_time,
    DAYS_OF_WEEK,
    get_day_name,
)
from bot.keyboards.inline import (
    get_categories_keyboard,
    get_days_selector_keyboard,
    get_children_keyboard,
    get_locations_keyboard,
)
from bot.keyboards.reply import (
    get_main_reply_keyboard,
    get_cancel_reply_keyboard,
    get_skip_or_cancel_reply_keyboard,
)

logger = logging.getLogger(__name__)
router = Router(name="add_activity_router")


@router.message(Command("add"))
@router.message(F.text == "➕ Добавить занятие")
async def start_add_activity(message: Message, session: AsyncSession, state: FSMContext):
    """Начало мастера добавления нового занятия."""
    await state.clear()
    children = await get_children(session, message.from_user.id)

    if not children:
        await message.answer(
            "⚠️ *У вас пока нет добавленных детей!*\n\n"
            "Чтобы составить расписание, сначала добавьте профиль ребёнка (имя и возраст).",
            parse_mode="Markdown",
            reply_markup=get_main_reply_keyboard(),
        )
        return

    if len(children) == 1:
        # Автоматически выбираем единственного ребёнка
        child = children[0]
        await state.update_data(child_id=child.id, child_name=child.name, child_emoji=child.color_emoji)
        await state.set_state(AddActivityFSM.select_category)
        await message.answer(
            f"Создаём занятие для: {child.color_emoji} *{child.name}*\n\n"
            f"Выберите направление (категорию) занятия:",
            parse_mode="Markdown",
            reply_markup=get_categories_keyboard(),
        )
    else:
        # Предлагаем выбрать ребёнка
        await state.set_state(AddActivityFSM.select_child)
        kb = get_children_keyboard(children, callback_prefix="add_act_child")
        await message.answer(
            "👧 *Для кого из детей вы хотите добавить занятие?*\nВыберите ребёнка:",
            parse_mode="Markdown",
            reply_markup=kb,
        )


@router.callback_query(AddActivityFSM.select_child, F.data.startswith("add_act_child:"))
async def process_select_child(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Выбор ребёнка из списка."""
    child_id = int(callback.data.split(":")[1])
    child = await get_child(session, child_id)
    if not child:
        await callback.answer("Ошибка: ребёнок не найден.", show_alert=True)
        return

    await state.update_data(child_id=child.id, child_name=child.name, child_emoji=child.color_emoji)
    await state.set_state(AddActivityFSM.select_category)

    await callback.message.edit_text(
        f"Выбран ребёнок: {child.color_emoji} *{child.name}*\n\n"
        f"Теперь выберите направление занятия:",
        parse_mode="Markdown",
        reply_markup=get_categories_keyboard(),
    )
    await callback.answer()


@router.callback_query(AddActivityFSM.select_category, F.data.startswith("select_cat:"))
async def process_select_category(callback: CallbackQuery, state: FSMContext):
    """Выбор категории занятия."""
    parts = callback.data.split(":")
    cat_name = parts[1]
    icon = parts[2]

    await state.update_data(category=cat_name, icon=icon, default_title=cat_name)
    await state.set_state(AddActivityFSM.input_title)

    await callback.message.delete()
    await callback.message.answer(
        f"Выбрано: {icon} *{cat_name}*\n\n"
        f"Введите точное название занятия (например: _«Английский с носителем»_, _«Секция плавания Дельфин»_)\n"
        f"или отправьте точку `.` чтобы оставить стандартное название «*{cat_name}*»:",
        parse_mode="Markdown",
        reply_markup=get_cancel_reply_keyboard(),
    )
    await callback.answer()


@router.message(AddActivityFSM.input_title)
async def process_input_title(message: Message, state: FSMContext):
    """Ввод названия занятия."""
    data = await state.get_data()
    title = message.text.strip()
    if title == "." or not title:
        title = data.get("default_title", "Занятие")

    await state.update_data(title=title, selected_days=[0])  # по умолчанию Пн
    await state.set_state(AddActivityFSM.select_days)

    await message.answer(
        f"Название сохранено: *{title}*\n\n"
        f"🗓️ Теперь укажите дни недели проведения занятия (можно выбрать несколько):\n"
        f"Нажмите на нужные дни и затем нажмите *«✅ Готово»*.",
        parse_mode="Markdown",
        reply_markup=get_days_selector_keyboard({0}),
    )


@router.callback_query(AddActivityFSM.select_days, F.data.startswith("toggle_day:"))
async def process_toggle_day(callback: CallbackQuery, state: FSMContext):
    """Переключение дня недели."""
    day_idx = int(callback.data.split(":")[1])
    data = await state.get_data()
    current_days: Set[int] = set(data.get("selected_days", []))

    if day_idx in current_days:
        if len(current_days) > 1:
            current_days.remove(day_idx)
    else:
        current_days.add(day_idx)

    await state.update_data(selected_days=list(current_days))
    await callback.message.edit_reply_markup(reply_markup=get_days_selector_keyboard(current_days))
    await callback.answer()


@router.callback_query(AddActivityFSM.select_days, F.data == "select_day_type:onetime")
async def process_select_onetime(callback: CallbackQuery, state: FSMContext):
    """Переключение на ввод разовой даты."""
    await state.set_state(AddActivityFSM.input_date)
    await callback.message.edit_text(
        "📅 Введите дату проведения разового занятия в формате *ДД.ММ.ГГГГ* (например: `15.11.2026`):",
        parse_mode="Markdown",
    )
    await callback.answer()


@router.message(AddActivityFSM.input_date)
async def process_input_date(message: Message, state: FSMContext):
    """Обработка ввода конкретной даты."""
    text = message.text.strip()
    try:
        dt = datetime.strptime(text, "%d.%m.%Y").date()
    except ValueError:
        await message.answer(
            "⚠️ Неверный формат даты! Пожалуйста, укажите дату в виде *ДД.ММ.ГГГГ* (например, `15.11.2026`):",
            parse_mode="Markdown",
            reply_markup=get_cancel_reply_keyboard(),
        )
        return

    await state.update_data(specific_date=dt.isoformat(), is_recurring=False)
    await state.set_state(AddActivityFSM.input_start_time)

    await message.answer(
        f"Дата зафиксирована: *{text}*\n\n"
        f"🕓 Введите *время начала* занятия (например: `16:00` или `16.00`):",
        parse_mode="Markdown",
        reply_markup=get_cancel_reply_keyboard(),
    )


@router.callback_query(AddActivityFSM.select_days, F.data == "days_selected_done")
async def process_days_done(callback: CallbackQuery, state: FSMContext):
    """Подтверждение выбора регулярных дней недели."""
    data = await state.get_data()
    days = data.get("selected_days", [])
    if not days:
        await callback.answer("Выберите хотя бы один день недели!", show_alert=True)
        return

    day_names = ", ".join([get_day_name(d, short=False) for d in sorted(days)])
    await state.update_data(is_recurring=True)
    await state.set_state(AddActivityFSM.input_start_time)

    await callback.message.delete()
    await callback.message.answer(
        f"Выбранные дни: *{day_names}*\n\n"
        f"🕓 Введите *время начала* занятия (например: `15:30`):",
        parse_mode="Markdown",
        reply_markup=get_cancel_reply_keyboard(),
    )
    await callback.answer()


@router.message(AddActivityFSM.input_start_time)
async def process_start_time(message: Message, state: FSMContext):
    """Обработка ввода времени начала."""
    t = parse_time(message.text)
    if not t:
        await message.answer(
            "⚠️ Не удалось распознать время. Введите в формате `ЧЧ:ММ` (например: `14:30` или `09:00`):",
            parse_mode="Markdown",
            reply_markup=get_cancel_reply_keyboard(),
        )
        return

    await state.update_data(start_time=t.strftime("%H:%M"))
    await state.set_state(AddActivityFSM.input_end_time)

    await message.answer(
        f"Начало: *{t.strftime('%H:%M')}*\n\n"
        f"🕓 Введите *время окончания* занятия (например: `17:00`):",
        parse_mode="Markdown",
        reply_markup=get_cancel_reply_keyboard(),
    )


@router.message(AddActivityFSM.input_end_time)
async def process_end_time(message: Message, session: AsyncSession, state: FSMContext):
    """Обработка ввода времени окончания."""
    t = parse_time(message.text)
    if not t:
        await message.answer(
            "⚠️ Неверный формат времени окончания. Введите в формате `ЧЧ:ММ` (например: `17:00`):",
            parse_mode="Markdown",
            reply_markup=get_cancel_reply_keyboard(),
        )
        return

    data = await state.get_data()
    start_t = parse_time(data["start_time"])
    if start_t and t <= start_t:
        await message.answer(
            "⚠️ Время окончания должно быть позже времени начала занятия!\n"
            f"Начало было указано: *{data['start_time']}*. Введите время окончания заново:",
            parse_mode="Markdown",
            reply_markup=get_cancel_reply_keyboard(),
        )
        return

    await state.update_data(end_time=t.strftime("%H:%M"))
    await state.set_state(AddActivityFSM.select_location)

    # Загружаем сохранённые места пользователя
    locations = await get_locations(session, message.from_user.id)
    kb = get_locations_keyboard(locations, include_new_btn=True)

    await message.answer(
        f"Время зафиксировано: *{data['start_time']} – {t.strftime('%H:%M')}*\n\n"
        f"📍 Укажите *место проведения* занятия:",
        parse_mode="Markdown",
        reply_markup=kb,
    )


@router.callback_query(AddActivityFSM.select_location, F.data.startswith("select_loc:"))
async def process_select_location(callback: CallbackQuery, state: FSMContext):
    """Выбор или добавление места."""
    action = callback.data.split(":")[1]

    if action == "none":
        await state.update_data(location_id=None, location_text=None)
        await state.set_state(AddActivityFSM.input_teacher)
        await callback.message.delete()
        await callback.message.answer(
            "👤 Введите *имя преподавателя или тренера* (необязательно)\n"
            "или нажмите *«⏭️ Пропустить»*:",
            parse_mode="Markdown",
            reply_markup=get_skip_or_cancel_reply_keyboard(),
        )
    elif action == "new":
        await state.set_state(AddActivityFSM.input_new_location_name)
        await callback.message.delete()
        await callback.message.answer(
            "📍 Введите *название нового места* (например: _«Бассейн Дельфин»_ или _«Школа №15»_):",
            parse_mode="Markdown",
            reply_markup=get_cancel_reply_keyboard(),
        )
    else:
        loc_id = int(action)
        await state.update_data(location_id=loc_id)
        await state.set_state(AddActivityFSM.input_teacher)
        await callback.message.delete()
        await callback.message.answer(
            "👤 Введите *имя преподавателя или тренера* (необязательно)\n"
            "или нажмите *«⏭️ Пропустить»*:",
            parse_mode="Markdown",
            reply_markup=get_skip_or_cancel_reply_keyboard(),
        )
    await callback.answer()


@router.message(AddActivityFSM.input_new_location_name)
async def process_new_location_name(message: Message, state: FSMContext):
    """Ввод названия новой локации."""
    name = message.text.strip()
    await state.update_data(new_loc_name=name)
    await state.set_state(AddActivityFSM.input_new_location_address)
    await message.answer(
        f"Место: *{name}*\n\n"
        f"Введите *адрес* (например: _«ул. Ленина, д. 25, каб. 10»_) или нажмите *«⏭️ Пропустить»*:",
        parse_mode="Markdown",
        reply_markup=get_skip_or_cancel_reply_keyboard(),
    )


@router.message(AddActivityFSM.input_new_location_address)
async def process_new_location_address(message: Message, session: AsyncSession, state: FSMContext):
    """Ввод адреса новой локации и её сохранение."""
    addr = message.text.strip()
    if addr == "⏭️ Пропустить":
        addr = ""

    data = await state.get_data()
    loc = await create_location(
        session=session,
        user_id=message.from_user.id,
        name=data["new_loc_name"],
        address=addr,
    )
    await state.update_data(location_id=loc.id)
    await state.set_state(AddActivityFSM.input_teacher)

    await message.answer(
        f"✅ Место *«{loc.name}»* успешно сохранено!\n\n"
        f"👤 Введите *имя преподавателя или тренера* (или нажмите *«⏭️ Пропустить»*):",
        parse_mode="Markdown",
        reply_markup=get_skip_or_cancel_reply_keyboard(),
    )


@router.message(AddActivityFSM.input_teacher)
async def process_input_teacher(message: Message, state: FSMContext):
    """Ввод преподавателя."""
    text = message.text.strip()
    teacher = None if text == "⏭️ Пропустить" else text
    await state.update_data(teacher_name=teacher)
    await state.set_state(AddActivityFSM.input_items)

    await message.answer(
        "🎒 *Что нужно взять с собой на занятие?*\n\n"
        "Например: _«Спортивная форма, кроссовки, бутылка воды»_ или _«Учебник, тетрадь в клетку, пенал»_.\n\n"
        "Бот будет напоминать об этих вещах перед каждым занятием! 💧\n"
        "Если вещей нет, нажмите *«⏭️ Пропустить»*:",
        parse_mode="Markdown",
        reply_markup=get_skip_or_cancel_reply_keyboard(),
    )


@router.message(AddActivityFSM.input_items)
async def process_input_items(message: Message, state: FSMContext):
    """Ввод списка необходимых вещей."""
    text = message.text.strip()
    items = None if text == "⏭️ Пропустить" else text
    await state.update_data(items_to_bring=items)
    await state.set_state(AddActivityFSM.input_notes)

    await message.answer(
        "📝 Дополнительные заметки (например, _«Вход со двора»_, _«Вторая смена»_) "
        "или нажмите *«⏭️ Пропустить»*:",
        parse_mode="Markdown",
        reply_markup=get_skip_or_cancel_reply_keyboard(),
    )


@router.message(AddActivityFSM.input_notes)
async def process_input_notes(message: Message, session: AsyncSession, state: FSMContext):
    """Завершение мастера добавления занятия и сохранение в БД."""
    text = message.text.strip()
    notes = None if text == "⏭️ Пропустить" else text

    data = await state.get_data()

    start_t = parse_time(data["start_time"])
    end_t = parse_time(data["end_time"])
    is_recurring = data.get("is_recurring", True)

    specific_d = None
    days = None
    if not is_recurring:
        specific_d = date.fromisoformat(data["specific_date"])
    else:
        days = data.get("selected_days", [0])

    activity = await create_activity(
        session=session,
        child_id=data["child_id"],
        title=data["title"],
        category=data.get("category", "Другое"),
        icon=data.get("icon", "📌"),
        start_time=start_t,
        end_time=end_t,
        days_of_week=days,
        specific_date=specific_d,
        location_id=data.get("location_id"),
        teacher_name=data.get("teacher_name"),
        items_to_bring=data.get("items_to_bring"),
        notes=notes,
    )

    await state.clear()

    # Формируем красивую карточку результата
    days_str = ""
    if is_recurring:
        days_str = ", ".join([get_day_name(d) for d in sorted(days)])
    else:
        days_str = f"Разово: {specific_d.strftime('%d.%m.%Y')}"

    summary_text = (
        f"🎉 *Занятие успешно добавлено!*\n\n"
        f"👧 Ребёнок: *{data['child_emoji']} {data['child_name']}*\n"
        f"📌 Занятие: {activity.icon} *{activity.title}*\n"
        f"🗓️ Дни: *{days_str}*\n"
        f"🕓 Время: *{data['start_time']} – {data['end_time']}*\n"
    )

    if activity.location:
        summary_text += f"📍 Место: {activity.location.name}\n"
    if activity.teacher_name:
        summary_text += f"👤 Преподаватель: {activity.teacher_name}\n"
    if activity.items_to_bring:
        summary_text += f"🎒 С собой: {activity.items_to_bring}\n"

    summary_text += (
        f"\n🔔 *Умные напоминания активированы!*\n"
        f"Вы будете получать уведомления за 1 день, 2 часа, 30 и 10 минут до начала."
    )

    await message.answer(
        text=summary_text,
        parse_mode="Markdown",
        reply_markup=get_main_reply_keyboard(),
    )
