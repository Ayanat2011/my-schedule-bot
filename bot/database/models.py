from datetime import datetime, time, date
from typing import List, Optional
from sqlalchemy import (
    BigInteger,
    Integer,
    String,
    Text,
    Boolean,
    Time,
    Date,
    DateTime,
    ForeignKey,
    func,
    Index,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Базовый класс для моделей SQLAlchemy."""
    pass


class User(Base):
    """Модель родителя / пользователя бота."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # Telegram ID пользователя
    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    full_name: Mapped[str] = mapped_column(String(128), default="")
    role: Mapped[str] = mapped_column(String(32), default="parent")  # parent, child, admin
    timezone: Mapped[str] = mapped_column(String(64), default="Europe/Moscow")

    # Настройки уведомлений
    is_notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    quiet_hours_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    quiet_hours_start: Mapped[Optional[time]] = mapped_column(Time, default=time(22, 0), nullable=True)
    quiet_hours_end: Mapped[Optional[time]] = mapped_column(Time, default=time(7, 0), nullable=True)

    # Утренний дайджест
    morning_digest_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    morning_digest_time: Mapped[time] = mapped_column(Time, default=time(8, 0))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    # Связи
    children: Mapped[List["Child"]] = relationship(
        "Child",
        back_populates="parent",
        cascade="all, delete-orphan",
        order_by="Child.id"
    )
    locations: Mapped[List["Location"]] = relationship(
        "Location",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="Location.name"
    )


class Child(Base):
    """Модель профиля ребёнка."""
    __tablename__ = "children"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    parent_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    telegram_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, unique=True)
    color_emoji: Mapped[str] = mapped_column(String(16), default="👧")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Связи
    parent: Mapped["User"] = relationship("User", back_populates="children")
    activities: Mapped[List["Activity"]] = relationship(
        "Activity",
        back_populates="child",
        cascade="all, delete-orphan",
        order_by="Activity.id"
    )


class Location(Base):
    """Модель места проведения занятий."""
    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)  # Например, "Школа №12", "Бассейн Волна"
    address: Mapped[str] = mapped_column(String(255), default="")    # Например, "ул. Пушкина, д. 10"
    note: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Например, "2 этаж, каб. 24"
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Связи
    user: Mapped["User"] = relationship("User", back_populates="locations")
    activities: Mapped[List["Activity"]] = relationship("Activity", back_populates="location")


class Activity(Base):
    """Модель занятия (кружок, урок, тренировка)."""
    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    child_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("children.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    location_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("locations.id", ondelete="SET NULL"),
        nullable=True
    )

    title: Mapped[str] = mapped_column(String(150), nullable=False)  # Например, "Футбол", "Английский"
    category: Mapped[str] = mapped_column(String(50), default="Другое")  # Спорт, Танцы, Школа, Музыка и т.д.
    icon: Mapped[str] = mapped_column(String(16), default="📌")
    teacher_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    teacher_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    items_to_bring: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Список вещей: форма, вода, ноты...
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)  # Можно временно отключить всё занятие
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Связи
    child: Mapped["Child"] = relationship("Child", back_populates="activities")
    location: Mapped[Optional["Location"]] = relationship("Location", back_populates="activities")
    schedules: Mapped[List["Schedule"]] = relationship(
        "Schedule",
        back_populates="activity",
        cascade="all, delete-orphan",
        order_by="Schedule.start_time"
    )
    reminder_setting: Mapped[Optional["ReminderSetting"]] = relationship(
        "ReminderSetting",
        back_populates="activity",
        uselist=False,
        cascade="all, delete-orphan"
    )


class Schedule(Base):
    """Модель слота расписания для занятия (день недели или конкретная дата)."""
    __tablename__ = "schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    activity_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("activities.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    is_recurring: Mapped[bool] = mapped_column(Boolean, default=True)  # True = еженедельно, False = разовое
    day_of_week: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 0=Понедельник, 6=Воскресенье
    specific_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)  # Для разовых событий

    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)

    # Статусы отмены и выполнения
    is_cancelled: Mapped[bool] = mapped_column(Boolean, default=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)

    # Связи
    activity: Mapped["Activity"] = relationship("Activity", back_populates="schedules")


class ReminderSetting(Base):
    """Настройки напоминаний для конкретного занятия."""
    __tablename__ = "reminder_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    activity_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("activities.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )

    remind_1_day: Mapped[bool] = mapped_column(Boolean, default=True)    # За 1 день (24ч или накануне)
    remind_2_hours: Mapped[bool] = mapped_column(Boolean, default=True)  # За 2 часа
    remind_30_min: Mapped[bool] = mapped_column(Boolean, default=True)   # За 30 минут
    remind_10_min: Mapped[bool] = mapped_column(Boolean, default=True)   # За 10 минут

    notify_parent: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_child: Mapped[bool] = mapped_column(Boolean, default=True)
    custom_minutes_before: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Связи
    activity: Mapped["Activity"] = relationship("Activity", back_populates="reminder_setting")


class NotificationLog(Base):
    """Журнал отправленных уведомлений для защиты от дублей."""
    __tablename__ = "notification_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    activity_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("activities.id", ondelete="SET NULL"),
        nullable=True
    )
    schedule_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("schedules.id", ondelete="SET NULL"),
        nullable=True
    )
    notification_type: Mapped[str] = mapped_column(String(32), nullable=False)  # 1_day, 2_hours, 30_min, 10_min, morning_digest
    target_datetime: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    status: Mapped[str] = mapped_column(String(32), default="sent")  # sent, failed, suppressed

    __table_args__ = (
        Index("ix_notification_dedup", "schedule_id", "notification_type", "target_datetime", "user_id"),
    )
