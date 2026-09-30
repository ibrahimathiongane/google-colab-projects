from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Habit(Base):
    """Mirror of the habits service table (shared database)."""

    __tablename__ = "habits"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, index=True)
    name = Column(String(120), nullable=False)
    anchor = Column(String(255), nullable=False, default="")
    tiny_behavior = Column(String(255), nullable=False, default="")
    celebration = Column(String(255), nullable=False, default="")
    if_then = Column(String(512), nullable=False, default="")
    cue_time = Column(String(5), nullable=False, default="")
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class CheckIn(Base):
    __tablename__ = "checkins"
    __table_args__ = (
        UniqueConstraint("habit_id", "date", name="uq_habit_date"),
    )

    id = Column(Integer, primary_key=True)
    habit_id = Column(
        Integer,
        ForeignKey("habits.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(Integer, nullable=False, index=True)
    date = Column(Date, nullable=False)
    completed = Column(Boolean, nullable=False, default=True)
    automaticity = Column(Integer)
    note = Column(String(500), nullable=False, default="")
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
