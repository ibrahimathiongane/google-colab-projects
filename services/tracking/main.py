import os
from datetime import date, timedelta

from fastapi import FastAPI, HTTPException, Header, Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import models

app = FastAPI(title="Tracking Service")
engine = create_engine(os.environ["DATABASE_URL"])
Session = sessionmaker(bind=engine)


@app.on_event("startup")
def startup():
    models.Base.metadata.create_all(engine)


def get_user_id(x_user_id: str = Header(None)):
    if not x_user_id:
        raise HTTPException(401)
    return int(x_user_id)


@app.post("/checkin")
def checkin(body: dict, user_id: int = Depends(get_user_id)):
    db = Session()
    d = date.fromisoformat(body["date"])
    existing = (
        db.query(models.CheckIn)
        .filter_by(habit_id=body["habit_id"], date=d)
        .first()
    )
    if existing:
        existing.completed = body["completed"]
        existing.automaticity = body.get("automaticity")
        existing.note = body.get("note", "")
    else:
        existing = models.CheckIn(
            habit_id=body["habit_id"],
            user_id=user_id,
            date=d,
            completed=body["completed"],
            automaticity=body.get("automaticity"),
            note=body.get("note", ""),
        )
        db.add(existing)
    db.commit()
    return {"ok": True}


@app.get("/today")
def today(date_str: str, user_id: int = Depends(get_user_id)):
    db = Session()
    d = date.fromisoformat(date_str)
    checkins = (
        db.query(models.CheckIn).filter_by(user_id=user_id, date=d).all()
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
def range_(habit_id: int, days: int = 30, user_id: int = Depends(get_user_id)):
    db = Session()
    start = date.today() - timedelta(days=days)
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
def streaks(user_id: int = Depends(get_user_id)):
    db = Session()
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
        today = date.today()
        for i in range(365):
            d = today - timedelta(days=i)
            if d in dates:
                streak += 1
            elif i == 0:
                continue
            else:
                break
        result.append(
            {
                "habit_id": h.id,
                "streak": streak,
                "total_checkins": len(dates),
            }
        )
    return result
