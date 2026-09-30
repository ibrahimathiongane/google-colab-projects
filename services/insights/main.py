import os
from datetime import date

from fastapi import FastAPI, HTTPException, Header, Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import models

app = FastAPI(title="Insights Service")
engine = create_engine(os.environ["DATABASE_URL"])
Session = sessionmaker(bind=engine)


@app.on_event("startup")
def startup():
    models.Base.metadata.create_all(engine)


def get_user_id(x_user_id: str = Header(None)):
    if not x_user_id:
        raise HTTPException(401)
    return int(x_user_id)


@app.get("/summary")
def summary(user_id: int = Depends(get_user_id)):
    db = Session()
    habits = (
        db.query(models.Habit).filter_by(user_id=user_id, active=True).all()
    )
    result = []
    for h in habits:
        checkins = (
            db.query(models.CheckIn)
            .filter_by(habit_id=h.id, user_id=user_id)
            .all()
        )
        total = len(checkins)
        completed = sum(1 for c in checkins if c.completed)
        rate = completed / total if total else 0

        times = [
            c.created_at.hour
            for c in checkins
            if c.completed and c.created_at
        ]
        best_hour = max(set(times), key=times.count) if times else None

        sorted_checkins = sorted(checkins, key=lambda c: c.date)
        recovery_days = []
        last_miss = None
        for c in sorted_checkins:
            if not c.completed:
                last_miss = c.date
            elif last_miss is not None:
                recovery_days.append((c.date - last_miss).days)
                last_miss = None
        avg_recovery = (
            sum(recovery_days) / len(recovery_days) if recovery_days else None
        )

        auto_scores = [c.automaticity for c in checkins if c.automaticity]
        avg_auto = sum(auto_scores) / len(auto_scores) if auto_scores else 0
        strength = (
            (rate * 0.6 + (avg_auto / 10) * 0.4) * 100 if total else 0
        )

        result.append(
            {
                "habit_id": h.id,
                "name": h.name,
                "if_then": h.if_then,
                "total_checkins": total,
                "completed": completed,
                "success_rate": round(rate * 100, 1),
                "best_hour": best_hour,
                "avg_recovery_days": (
                    round(avg_recovery, 1) if avg_recovery else None
                ),
                "habit_strength": round(strength, 1),
            }
        )
    return result
