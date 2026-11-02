import pytest
from datetime import datetime, time
from bot.services.reminder_service import (
    is_notification_already_sent,
    record_notification_log,
)
from bot.utils.text_helpers import (
    format_child_reminder_message,
    format_parent_reminder_message,
    format_morning_digest_message,
    format_reminder_countdown_text,
)


@pytest.mark.asyncio
async def test_notification_deduplication(test_session):
    """Тестирование защиты от повторной отправки одинаковых напоминаний."""
    user_id = 999111
    schedule_id = 42
    target_dt = datetime(2026, 11, 4, 16, 0, 0)
    notif_type = "30_min"

    # Сначала напоминание не отправлено
    already = await is_notification_already_sent(
        session=test_session,
        user_id=user_id,
        schedule_id=schedule_id,
        notification_type=notif_type,
        target_datetime=target_dt,
    )
    assert already is False

    # Логируем отправку
    await record_notification_log(
        session=test_session,
        user_id=user_id,
        notification_type=notif_type,
        target_datetime=target_dt,
        schedule_id=schedule_id,
        status="sent",
    )

    # Теперь проверка должна вернуть True
    already_after = await is_notification_already_sent(
        session=test_session,
        user_id=user_id,
        schedule_id=schedule_id,
        notification_type=notif_type,
        target_datetime=target_dt,
    )
    assert already_after is True


def test_child_reminder_message_format():
    """Тестирование формирования детского сообщения с эмодзи и вещами."""
    msg = format_child_reminder_message(
        child_name="Алиса",
        activity_icon="⚽",
        activity_title="Футбол",
        start_time_str="16:00",
        end_time_str="17:30",
        location_name="Спортивная школа Олимп",
        location_address="ул. Мира, 10",
        teacher_name="Иван Петрович",
        items_to_bring="спортивную форму и воду",
        notification_type="30_min",
    )

    assert "Привет, Алиса!" in msg
    assert "⚽ *Футбол*" in msg
    assert "16:00" in msg
    assert "Спортивная школа Олимп" in msg
    assert "До занятия осталось 30 минут!" in msg
    assert "спортивную форму и воду" in msg


def test_morning_digest_format():
    """Тестирование формирования утреннего дайджеста."""
    activities = {
        "Алиса": [
            {"icon": "📚", "time_str": "08:30–13:30", "title": "Школа", "location": "Школа №12"},
            {"icon": "🇬🇧", "time_str": "15:00–16:30", "title": "Английский", "location": ""},
        ]
    }
    digest = format_morning_digest_message(
        recipient_name="Алиса",
        is_parent=False,
        activities_by_child=activities,
    )

    assert "Доброе утро, Алиса!" in digest
    assert "08:30–13:30" in digest
    assert "Школа" in digest
    assert "Английский" in digest
