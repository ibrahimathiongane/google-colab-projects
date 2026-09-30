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
