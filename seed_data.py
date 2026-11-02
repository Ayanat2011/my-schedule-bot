"""
Скрипт для заполнения базы данных демонстрационными данными.
Создаёт семью с двумя детьми (Алиса и Максим), несколькими местами занятий
и реалистичным недельным расписанием (школа, английский, плавание, танцы, футбол, робототехника).
"""

import asyncio
from datetime import time, date
from bot.database.session import init_db, async_session_maker, engine
from bot.services.user_service import get_or_create_user, create_child
from bot.services.activity_service import create_location, create_activity


async def seed():
    print("Инициализация таблиц базы данных...")
    await init_db()

    async with async_session_maker() as session:
        # 1. Создаём тестового родителя
        parent_tg_id = 999999999
        user = await get_or_create_user(
            session=session,
            telegram_id=parent_tg_id,
            username="demo_parent",
            full_name="Анна Иванова",
        )
        print(f"Родитель создан: {user.full_name} (ID: {user.id})")

        # 2. Создаём детей
        alisa = await create_child(
            session=session,
            parent_id=user.id,
            name="Алиса",
            age=10,
            color_emoji="👧",
            telegram_id=888888881,  # тестовый личный аккаунт Алисы
        )
        maksim = await create_child(
            session=session,
            parent_id=user.id,
            name="Максим",
            age=8,
            color_emoji="👦",
            telegram_id=None,
        )
        print(f"Дети созданы: {alisa.name} (10 лет) и {maksim.name} (8 лет)")

        # 3. Создаём локации
        loc_school = await create_location(
            session=session,
            user_id=user.id,
            name="Школа №12",
            address="ул. Пушкина, д. 15",
            note="Главный вход, 2 этаж",
        )
        loc_pool = await create_location(
            session=session,
            user_id=user.id,
            name="Бассейн «Волна»",
            address="пр. Мира, д. 42",
            note="Секция 3, шкафчики 10-25",
        )
        loc_stadium = await create_location(
            session=session,
            user_id=user.id,
            name="Спортивный комплекс «Олимп»",
            address="ул. Спортивная, д. 8",
            note="Поле №2",
        )
        loc_english = await create_location(
            session=session,
            user_id=user.id,
            name="Языковой центр Oxford Kids",
            address="ул. Ленина, д. 100, офис 405",
        )
        print("Локации созданы.")

        # 4. Занятия для Алисы
        # Школа (Пн-Пт)
        await create_activity(
            session=session,
            child_id=alisa.id,
            title="Школьные уроки",
            category="Школа",
            icon="📚",
            start_time=time(8, 30),
            end_time=time(13, 15),
            days_of_week=[0, 1, 2, 3, 4],  # Пн, Вт, Ср, Чт, Пт
            location_id=loc_school.id,
            teacher_name="Марина Васильевна",
            items_to_bring="Сменная обувь, дневник, учебники, пенал, пропуск",
        )

        # Английский (Вт, Чт)
        await create_activity(
            session=session,
            child_id=alisa.id,
            title="Английский язык",
            category="Английский",
            icon="🇬🇧",
            start_time=time(15, 0),
            end_time=time(16, 30),
            days_of_week=[1, 3],  # Вт, Чт
            location_id=loc_english.id,
            teacher_name="Елена Сергеевна",
            items_to_bring="Рабочая тетрадь Round-up, словарь, цветные ручки",
        )

        # Плавание (Пн, Ср, Пт)
        await create_activity(
            session=session,
            child_id=alisa.id,
            title="Секция плавания",
            category="Плавание",
            icon="🏊",
            start_time=time(17, 30),
            end_time=time(19, 0),
            days_of_week=[0, 2, 4],  # Пн, Ср, Пт
            location_id=loc_pool.id,
            teacher_name="Виктор Алексеевич",
            items_to_bring="Слитный купальник, силиконовая шапочка, очки, полотенце, шлёпанцы, вода",
        )

        # 5. Занятия для Максима
        # Футбол (Вт, Чт, Сб)
        await create_activity(
            session=session,
            child_id=maksim.id,
            title="Тренировка по футболу",
            category="Футбол",
            icon="⚽",
            start_time=time(16, 0),
            end_time=time(17, 30),
            days_of_week=[1, 3, 5],  # Вт, Чт, Сб
            location_id=loc_stadium.id,
            teacher_name="Иван Петрович",
            items_to_bring="Форма, бутсы сороконожки, щитки, бутылка негазированной воды 0.5л",
        )

        # Робототехника (Ср)
        await create_activity(
            session=session,
            child_id=maksim.id,
            title="Кружок робототехники",
            category="Творчество",
            icon="🤖",
            start_time=time(15, 0),
            end_time=time(16, 30),
            days_of_week=[2],  # Среда
            teacher_name="Арсений Олегович",
            items_to_bring="Флешка, блокнот, ручка",
        )

        print("Все тестовые занятия успешно созданы!")

    await engine.dispose()
    print("Готово! База данных заполнена тестовыми данными.")


if __name__ == "__main__":
    asyncio.run(seed())
