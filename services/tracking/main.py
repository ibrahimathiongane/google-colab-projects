import logging
import os
from contextlib import asynccontextmanager
from datetime import date as date_cls
from datetime import timedelta

import models
import schemas
from db import engine, get_db
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("tracking")

# Safety bound so a corrupt row set can never spin forever.
MAX_STREAK_DAYS = 36500


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    engine.dispose()


app = FastAPI(title="Tracking Service", lifespan=lifespan)


def require_user_id(x_user_id: str | None = Header(None)) -> int:
    if not x_user_id:
        raise HTTPException(401, "Authentication required")
    try:
        return int(x_user_id)
    except ValueError:
        raise HTTPException(401, "Invalid user identity") from None


def owned_habit(db: Session, habit_id: int, user_id: int) -> models.Habit:
    """Return the habit only if it belongs to this user (and is active).

    Prevents writing check-ins onto someone else's habit.
    """
    habit = (
        db.query(models.Habit)
        .filter_by(id=habit_id, user_id=user_id, active=True)
        .first()
    )
    if not habit:
        raise HTTPException(404, "Habit not found")
    return habit


@app.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(503, "database unavailable") from None
    return {"status": "ok"}


@app.post("/checkin")
def checkin(
    body: schemas.CheckInIn,
    user_id: int = Depends(require_user_id),
    db: Session = Depends(get_db),
):
    owned_habit(db, body.habit_id, user_id)
    day = date_cls.fromisoformat(body.date)

    existing = (
        db.query(models.CheckIn)
        .filter_by(habit_id=body.habit_id, date=day)
        .first()
    )
    if existing:
        # Re-checking toggles/overwrites: one row per (habit, day).
        existing.completed = body.completed
        existing.automaticity = body.automaticity
        existing.note = body.note
    else:
        db.add(
            models.CheckIn(
                habit_id=body.habit_id,
                user_id=user_id,
                date=day,
                completed=body.completed,
                automaticity=body.automaticity,
                note=body.note,
            )
        )
    db.commit()
    return {"ok": True}


@app.get("/today")
def today(
    date: str = Query(pattern=r"^\d{4}-\d{2}-\d{2}$"),
    user_id: int = Depends(require_user_id),
    db: Session = Depends(get_db),
):
    try:
        day = date_cls.fromisoformat(date)
    except ValueError:
        raise HTTPException(422, "date must be a valid YYYY-MM-DD date") from None
    checkins = (
        db.query(models.CheckIn).filter_by(user_id=user_id, date=day).all()
    )
    return [
        {
            "habit_id": c.habit_id,
            "completed": c.completed,
            "automaticity": c.automaticity,
        }
        for c in checkins
    ]


@app.get("/range")
def range_(
    habit_id: int = Query(gt=0),
    days: int = Query(default=30, ge=1, le=366),
    user_id: int = Depends(require_user_id),
    db: Session = Depends(get_db),
):
    owned_habit(db, habit_id, user_id)
    start = date_cls.today() - timedelta(days=days)
    checkins = (
        db.query(models.CheckIn)
        .filter_by(habit_id=habit_id, user_id=user_id)
        .filter(models.CheckIn.date >= start)
        .order_by(models.CheckIn.date)
        .all()
    )
    return [
        {
            "date": c.date.isoformat(),
            "completed": c.completed,
            "automaticity": c.automaticity,
        }
        for c in checkins
    ]


@app.get("/streaks")
def streaks(
    user_id: int = Depends(require_user_id),
    db: Session = Depends(get_db),
):
    """Consecutive completed days, oldest-anchored on today.

    A missing check-in *today* does not break the streak (grace): the
    user still has the rest of the day to complete it. Only yesterday
    and earlier count. There is no upper cap — long streaks stay honest.
    """
    habits = (
        db.query(models.Habit).filter_by(user_id=user_id, active=True).all()
    )
    result = []
    for h in habits:
        checkins = (
            db.query(models.CheckIn)
            .filter_by(habit_id=h.id, user_id=user_id, completed=True)
            .order_by(models.CheckIn.date)
            .all()
        )
        dates = {c.date for c in checkins}
        streak = 0
        today = date_cls.today()
        for i in range(MAX_STREAK_DAYS):
            day = today - timedelta(days=i)
            if day in dates:
                streak += 1
            elif i == 0:
                continue  # today is not over yet: grace
            else:
                break
        result.append(
            {
                "habit_id": h.id,
                "streak": streak,
                "completed_checkins": len(dates),
            }
        )
    return result
