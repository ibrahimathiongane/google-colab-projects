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
    return [
        {
            "id": h.id,
            "name": h.name,
            "anchor": h.anchor,
            "tiny_behavior": h.tiny_behavior,
            "celebration": h.celebration,
            "if_then": h.if_then,
            "cue_time": h.cue_time,
            "created_at": h.created_at.isoformat(),
        }
        for h in habits
    ]


@app.post("/", status_code=201)
def create_habit(
    body: schemas.CreateHabitIn,
    user_id: int = Depends(require_user_id),
    db: Session = Depends(get_db),
):
    # Implementation intention (Gollwitzer): the sentence is the habit's
    # identity, generated from the recipe the user filled in.
    if_then = (
        f"After I {body.anchor}, I will {body.tiny_behavior}, "
        f"then I will {body.celebration}."
    )
    habit = models.Habit(
        user_id=user_id,
        name=body.name,
        anchor=body.anchor,
        tiny_behavior=body.tiny_behavior,
        celebration=body.celebration,
        if_then=if_then,
        cue_time=body.cue_time,
    )
    db.add(habit)
    db.commit()
    db.refresh(habit)
    logger.info("habit created id=%s user=%s", habit.id, user_id)
    return {"id": habit.id, "if_then": habit.if_then}


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
