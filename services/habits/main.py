import logging
import os
from contextlib import asynccontextmanager

import models
import schemas
from db import engine, get_db
from fastapi import Depends, FastAPI, Header, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("habits")


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    engine.dispose()


app = FastAPI(title="Habits Service", lifespan=lifespan)


def require_user_id(x_user_id: str | None = Header(None)) -> int:
    if not x_user_id:
        raise HTTPException(401, "Authentication required")
    try:
        return int(x_user_id)
    except ValueError:
        raise HTTPException(401, "Invalid user identity") from None


def if_then_sentence(anchor: str, tiny_behavior: str, celebration: str) -> str:
    # Implementation intention (Gollwitzer): the sentence is the habit's
    # identity, generated from the recipe the user filled in.
    return (
        f"After I {anchor}, I will {tiny_behavior}, "
        f"then I will {celebration}."
    )


# --- Plan gate (free = 1 habit) ---------------------------------------------
# The plan is read from the shared billing tables (no service hop); the
# billing service owns any writes. Existing habits are never retro-limited:
# only creating a new one beyond the limit is blocked.
FREE_HABIT_LIMIT = 1
PAID_STATUSES = ("active", "trialing", "past_due")  # mirror of billing


def current_plan(db: Session, user_id: int) -> str:
    row = (
        db.query(models.BillingSubscription).filter_by(user_id=user_id).first()
    )
    if row is None:
        return "free"
    if row.plan == "lifetime":
        return "lifetime"
    if row.plan == "pro" and row.status in PAID_STATUSES:
        return "pro"
    return "free"


def habit_payload(habit: models.Habit) -> dict:
    return {
        "id": habit.id,
        "name": habit.name,
        "anchor": habit.anchor,
        "tiny_behavior": habit.tiny_behavior,
        "celebration": habit.celebration,
        "if_then": habit.if_then,
        "cue_time": habit.cue_time,
        "created_at": habit.created_at.isoformat(),
    }


@app.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(503, "database unavailable") from None
    return {"status": "ok"}


@app.get("/")
def list_habits(
    user_id: int = Depends(require_user_id),
    db: Session = Depends(get_db),
):
    habits = (
        db.query(models.Habit).filter_by(user_id=user_id, active=True).all()
    )
    return [habit_payload(h) for h in habits]


@app.post("/", status_code=201)
def create_habit(
    body: schemas.CreateHabitIn,
    user_id: int = Depends(require_user_id),
    db: Session = Depends(get_db),
):
    if current_plan(db, user_id) == "free":
        active = (
            db.query(models.Habit)
            .filter_by(user_id=user_id, active=True)
            .count()
        )
        if active >= FREE_HABIT_LIMIT:
            raise HTTPException(
                402, "Free plan allows one habit — upgrade to Pro"
            )
    habit = models.Habit(
        user_id=user_id,
        name=body.name,
        anchor=body.anchor,
        tiny_behavior=body.tiny_behavior,
        celebration=body.celebration,
        if_then=if_then_sentence(body.anchor, body.tiny_behavior, body.celebration),
        cue_time=body.cue_time,
    )
    db.add(habit)
    db.commit()
    db.refresh(habit)
    logger.info("habit created id=%s user=%s", habit.id, user_id)
    return habit_payload(habit)


@app.put("/{habit_id}")
def update_habit(
    habit_id: int,
    body: schemas.UpdateHabitIn,
    user_id: int = Depends(require_user_id),
    db: Session = Depends(get_db),
):
    habit = (
        db.query(models.Habit)
        .filter_by(id=habit_id, user_id=user_id, active=True)
        .first()
    )
    if not habit:
        raise HTTPException(404, "Habit not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(habit, field, value)
    # The sentence is derived from the recipe: keep it in sync on every edit.
    habit.if_then = if_then_sentence(
        habit.anchor, habit.tiny_behavior, habit.celebration
    )
    db.commit()
    db.refresh(habit)
    logger.info("habit updated id=%s user=%s", habit.id, user_id)
    return habit_payload(habit)


@app.delete("/{habit_id}")
def delete_habit(
    habit_id: int,
    user_id: int = Depends(require_user_id),
    db: Session = Depends(get_db),
):
    habit = (
        db.query(models.Habit)
        .filter_by(id=habit_id, user_id=user_id, active=True)
        .first()
    )
    if not habit:
        raise HTTPException(404, "Habit not found")
    habit.active = False
    db.commit()
    return {"ok": True}
