from datetime import time, date
from bot.utils.time_utils import (
    parse_time,
    get_day_name,
    is_in_quiet_hours,
    format_time_range,
    format_russian_date,
    get_week_date_range,
)


def test_parse_time():
    """Тестирование парсинга времени."""
    assert parse_time("14:30") == time(14, 30)
    assert parse_time("08.15") == time(8, 15)
    assert parse_time("9:00") == time(9, 0)
    assert parse_time("0:00") == time(0, 0)
    assert parse_time("23:59") == time(23, 59)

    # Некорректные форматы
    assert parse_time("24:00") is None
    assert parse_time("12:65") is None
    assert parse_time("invalid") is None
    assert parse_time("") is None


def test_get_day_name():
    """Тестирование названий дней недели."""
    assert get_day_name(0, short=False) == "Понедельник"
    assert get_day_name(0, short=True) == "Пн"
    assert get_day_name(4, short=False) == "Пятница"
    assert get_day_name(6, short=False) == "Воскресенье"
    assert get_day_name(6, short=True) == "Вс"


def test_format_time_range():
    """Тестирование форматирования диапазона времени."""
    t1 = time(15, 30)
    t2 = time(17, 0)
    assert format_time_range(t1, t2) == "15:30 – 17:00"


def test_is_in_quiet_hours():
    """Тестирование логики тихих часов (включая переход через полночь)."""
    start_q = time(22, 0)
    end_q = time(7, 0)

    # Внутри тихих часов (ночью)
    assert is_in_quiet_hours(time(22, 0), start_q, end_q) is True
    assert is_in_quiet_hours(time(23, 30), start_q, end_q) is True
    assert is_in_quiet_hours(time(0, 0), start_q, end_q) is True
    assert is_in_quiet_hours(time(6, 59), start_q, end_q) is True

    # Вне тихих часов (днём)
    assert is_in_quiet_hours(time(7, 0), start_q, end_q) is False
    assert is_in_quiet_hours(time(12, 0), start_q, end_q) is False
    assert is_in_quiet_hours(time(21, 59), start_q, end_q) is False

    # Дневной интервал (без перехода через полночь: 13:00 - 15:00)
    day_start = time(13, 0)
    day_end = time(15, 0)
    assert is_in_quiet_hours(time(14, 0), day_start, day_end) is True
    assert is_in_quiet_hours(time(12, 59), day_start, day_end) is False
    assert is_in_quiet_hours(time(15, 0), day_start, day_end) is False


def test_get_week_date_range():
    """Тестирование вычисления начала и конца недели."""
    # 2026-11-04 это среда
    test_d = date(2026, 11, 4)
    mon, sun = get_week_date_range(test_d)
    assert mon == date(2026, 11, 2)
    assert sun == date(2026, 11, 8)
    assert mon.weekday() == 0
    assert sun.weekday() == 6
