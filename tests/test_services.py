import pytest
from datetime import time, date
from bot.services.user_service import (
    get_or_create_user,
    get_user,
    create_child,
    get_children,
    delete_child,
)
from bot.services.activity_service import (
    create_location,
    get_locations,
    create_activity,
    get_activity,
    get_user_schedule_for_date,
    toggle_activity_active,
    toggle_schedule_cancellation,
    mark_schedule_completed,
    update_reminder_settings,
)


@pytest.mark.asyncio
async def test_user_and_child_crud(test_session):
    """Тестирование создания родителя и профилей детей."""
    # 1. Создание пользователя
    user = await get_or_create_user(
        session=test_session,
        telegram_id=123456,
        username="test_parent",
        full_name="Иван Петров",
    )
    assert user.id == 123456
    assert user.full_name == "Иван Петров"

    # 2. Добавление детей
    child1 = await create_child(
        session=test_session,
        parent_id=user.id,
        name="Алиса",
        age=9,
        color_emoji="👧",
    )
    child2 = await create_child(
        session=test_session,
        parent_id=user.id,
        name="Максим",
        age=6,
        color_emoji="👦",
    )

    children = await get_children(test_session, user.id)
    assert len(children) == 2
    assert children[0].name == "Алиса"
    assert children[1].name == "Максим"

    # 3. Удаление ребёнка
    deleted = await delete_child(test_session, child2.id)
    assert deleted is True

    children_after = await get_children(test_session, user.id)
    assert len(children_after) == 1
    assert children_after[0].name == "Алиса"


@pytest.mark.asyncio
async def test_activity_and_schedule_queries(test_session):
    """Тестирование создания занятий и выборки расписания на дату."""
    user = await get_or_create_user(test_session, 555555, "mom", "Анна")
    child = await create_child(test_session, user.id, "Даша", 11)

    # Создаём локацию
    loc = await create_location(test_session, user.id, "Бассейн Дельфин", "ул. Мира, 1")
    assert loc.name == "Бассейн Дельфин"

    # Создаём регулярное занятие (по средам и пятницам, 16:00 - 17:30)
    # 2=Среда, 4=Пятница
    act = await create_activity(
        session=test_session,
        child_id=child.id,
        title="Плавание",
        category="Плавание",
        icon="🏊",
        start_time=time(16, 0),
        end_time=time(17, 30),
        days_of_week=[2, 4],
        location_id=loc.id,
        items_to_bring="Купальник, шапочка, очки, полотенце",
    )

    assert act.title == "Плавание"
    assert len(act.schedules) == 2
    assert act.reminder_setting is not None
    assert act.reminder_setting.remind_30_min is True

    # Проверяем расписание на среду (2026-11-04 - это среда, weekday=2)
    wednesday_date = date(2026, 11, 4)
    schedules_wed = await get_user_schedule_for_date(test_session, user.id, wednesday_date)
    assert len(schedules_wed) == 1
    assert schedules_wed[0].activity.title == "Плавание"

    # Проверяем расписание на вторник (2026-11-03 - вторник, weekday=1)
    tuesday_date = date(2026, 11, 3)
    schedules_tue = await get_user_schedule_for_date(test_session, user.id, tuesday_date)
    assert len(schedules_tue) == 0

    # Создаём разовое занятие на вторник (2026-11-03)
    one_off_act = await create_activity(
        session=test_session,
        child_id=child.id,
        title="Стоматолог",
        category="Другое",
        icon="🦷",
        start_time=time(10, 0),
        end_time=time(11, 0),
        specific_date=tuesday_date,
    )
    schedules_tue_after = await get_user_schedule_for_date(test_session, user.id, tuesday_date)
    assert len(schedules_tue_after) == 1
    assert schedules_tue_after[0].activity.title == "Стоматолог"


@pytest.mark.asyncio
async def test_schedule_status_toggles(test_session):
    """Тестирование отметок выполнения и отмены занятия."""
    user = await get_or_create_user(test_session, 777777, "dad", "Сергей")
    child = await create_child(test_session, user.id, "Коля", 8)

    act = await create_activity(
        session=test_session,
        child_id=child.id,
        title="Футбол",
        category="Футбол",
        icon="⚽",
        start_time=time(15, 0),
        end_time=time(16, 30),
        days_of_week=[0],
    )
    sch_id = act.schedules[0].id

    # 1. Отметка о выполнении
    completed = await mark_schedule_completed(test_session, sch_id, is_completed=True)
    assert completed is True

    # 2. Отмена занятия на сегодня
    cancelled = await toggle_schedule_cancellation(test_session, sch_id)
    assert cancelled is True

    uncancelled = await toggle_schedule_cancellation(test_session, sch_id)
    assert uncancelled is False

    # 3. Приостановка всего занятия
    active = await toggle_activity_active(test_session, act.id)
    assert active is False

    # 4. Обновление напоминаний
    rem = await update_reminder_settings(test_session, act.id, remind_10_min=False)
    assert rem.remind_10_min is False
    assert rem.remind_30_min is True
