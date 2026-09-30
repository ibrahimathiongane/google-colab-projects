import logging
import os
from contextlib import asynccontextmanager
from datetime import date as date_cls
from datetime import timedelta

import models
from db import engine, get_db
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("insights")


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    engine.dispose()


app = FastAPI(title="Insights Service", lifespan=lifespan)


def require_user_id(x_user_id: str | None = Header(None)) -> int:
    if not x_user_id:
        raise HTTPException(401, "Authentication required")
    try:
        return int(x_user_id)
    except ValueError:
        raise HTTPException(401, "Invalid user identity") from None


@app.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(503, "database unavailable") from None
    return {"status": "ok"}


def _miss_days_and_recovery(
    checkins, created_day: date_cls, today: date_cls
) -> tuple[set[date_cls], list[int]]:
    """Return the set of missed days and the list of recovery delays.

    A day counts as *missed* when there is no completed check-in for it —
    whether the user explicitly undid it or simply did not check in at
    all. Days before the habit existed are never misses.
    """
    completed_days = {c.date for c in checkins if c.completed}
    start = max(created_day, today - timedelta(days=365))
    missed: set[date_cls] = set()
    recovery: list[int] = []
    miss_start: date_cls | None = None

    day = start
    while day <= today:
        if day in completed_days:
            if miss_start is not None:
                recovery.append((day - miss_start).days)
                miss_start = None
        else:
            missed.add(day)
            if miss_start is None:
                miss_start = day
        day += timedelta(days=1)
    return missed, recovery


@app.get("/summary")
def summary(
    tz_offset: int = Query(default=0, ge=-840, le=840),
    user_id: int = Depends(require_user_id),
    db: Session = Depends(get_db),
):
    """Per-habit metrics.

    ``tz_offset`` is the caller's UTC offset in minutes (the browser's
    ``Date.getTimezoneOffset()`` negated), used to report the "best hour"
    in the user's local time instead of server UTC.
    """
    habits = (
        db.query(models.Habit).filter_by(user_id=user_id, active=True).all()
    )
    today = date_cls.today()
    offset = timedelta(minutes=tz_offset)
    result = []

    for h in habits:
        created_day = h.created_at.date()
        checkins = (
            db.query(models.CheckIn).filter_by(habit_id=h.id).all()
        )
        elapsed_days = max((today - created_day).days + 1, 1)
        completed = sum(1 for c in checkins if c.completed)

        # Denominator is days the habit has existed, not rows logged:
        # skipping a day must not improve the score.
        rate = min(completed / elapsed_days, 1.0)

        times = [
            (c.created_at + offset).hour
            for c in checkins
            if c.completed and c.created_at
        ]
        best_hour = max(set(times), key=times.count) if times else None

        missed, recovery = _miss_days_and_recovery(
            checkins, created_day, today
        )
        avg_recovery = (
            sum(recovery) / len(recovery) if recovery else None
        )

        auto_scores = [
            c.automaticity for c in checkins if c.automaticity is not None
        ]
        avg_auto = sum(auto_scores) / len(auto_scores) if auto_scores else 0
        strength = (rate * 0.6 + (avg_auto / 10) * 0.4) * 100

        result.append(
            {
                "habit_id": h.id,
                "name": h.name,
                "if_then": h.if_then,
                "total_checkins": len(checkins),
                "completed": completed,
                "missed_days": len(missed),
                "elapsed_days": elapsed_days,
                "success_rate": round(rate * 100, 1),
                "best_hour": best_hour,
                "avg_recovery_days": (
                    round(avg_recovery, 1) if avg_recovery is not None else None
                ),
                "habit_strength": round(strength, 1),
            }
        )
    return result
