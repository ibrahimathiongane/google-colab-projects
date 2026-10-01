from sqlalchemy import Boolean, Column, Date, DateTime, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class PushSubscription(Base):
    """Mirror of push_subscriptions: one row per opted-in device.

    ``tz_offset`` is minutes east of UTC, captured at subscribe time for
    that device (reminders fire at the cue_time in device-local time).
    """

    __tablename__ = "push_subscriptions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, index=True)
    endpoint = Column(String(512), nullable=False, unique=True, index=True)
    p256dh = Column(String(128), nullable=False)
    auth = Column(String(64), nullable=False)
    tz_offset = Column(Integer, nullable=False, default=0)
    lang = Column(String(5), nullable=False, default="en")
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ReminderLog(Base):
    """Mirror of reminder_logs: at most one push per device/habit/local day."""

    __tablename__ = "reminder_logs"
    __table_args__ = (
        UniqueConstraint(
            "subscription_id", "habit_id", "date", name="uq_reminder_day"
        ),
    )

    id = Column(Integer, primary_key=True)
    subscription_id = Column(Integer, nullable=False, index=True)
    habit_id = Column(Integer, nullable=False, index=True)
    date = Column(Date, nullable=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Habit(Base):
    """Mirror of habits (read-only from this service)."""

    __tablename__ = "habits"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, index=True)
    name = Column(String(120), nullable=False)
    anchor = Column(String(255), nullable=False, default="")
    cue_time = Column(String(5), nullable=False, default="")
    active = Column(Boolean, nullable=False, default=True)


class CheckIn(Base):
    """Mirror of checkins (read-only from this service)."""

    __tablename__ = "checkins"

    id = Column(Integer, primary_key=True)
    habit_id = Column(Integer, nullable=False, index=True)
    date = Column(Date, nullable=False)
    completed = Column(Boolean, nullable=False, default=True)
