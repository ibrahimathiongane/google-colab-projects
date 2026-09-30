from sqlalchemy import Boolean, Column, DateTime, Integer, String, func
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Habit(Base):
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
