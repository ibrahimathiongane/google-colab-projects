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
    active = Column(Boolean, nullable=False, default=True)


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
    automaticity = Column(Integer)  # 1-10 self-report
    note = Column(String(500), nullable=False, default="")
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
