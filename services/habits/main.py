import os

from fastapi import FastAPI, HTTPException, Header, Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import models

app = FastAPI(title="Habits Service")
engine = create_engine(os.environ["DATABASE_URL"])
Session = sessionmaker(bind=engine)


@app.on_event("startup")
def startup():
    models.Base.metadata.create_all(engine)


def get_user_id(x_user_id: str = Header(None)):
    if not x_user_id:
        raise HTTPException(401)
    return int(x_user_id)


@app.get("/")
def list_habits(user_id: int = Depends(get_user_id)):
    db = Session()
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


@app.post("/")
def create_habit(body: dict, user_id: int = Depends(get_user_id)):
    db = Session()
    if_then = (
        f"After I {body['anchor']}, I will {body['tiny_behavior']}, "
        f"then I will {body['celebration']}."
    )
    habit = models.Habit(
        user_id=user_id,
        name=body["name"],
        anchor=body["anchor"],
        tiny_behavior=body["tiny_behavior"],
        celebration=body["celebration"],
        if_then=if_then,
        cue_time=body.get("cue_time", ""),
    )
    db.add(habit)
    db.commit()
    db.refresh(habit)
    return {"id": habit.id, "if_then": habit.if_then}


@app.delete("/{habit_id}")
def delete_habit(habit_id: int, user_id: int = Depends(get_user_id)):
    db = Session()
    habit = db.query(models.Habit).filter_by(
        id=habit_id, user_id=user_id
    ).first()
    if not habit:
        raise HTTPException(404)
    habit.active = False
    db.commit()
    return {"ok": True}
