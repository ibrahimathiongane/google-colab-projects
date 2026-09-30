import os
import pathlib
import sys
import tempfile

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

_TMP = tempfile.mkdtemp(prefix="insights-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP}/insights.db"

from datetime import UTC

import main
import models
from db import SessionLocal, engine
from fastapi.testclient import TestClient

USER_A = {"X-User-Id": "1"}
USER_B = {"X-User-Id": "2"}


@pytest.fixture()
def client():
    models.Base.metadata.create_all(engine)
    with TestClient(main.app) as test_client:
        yield test_client
    with engine.begin() as conn:
        for table in reversed(models.Base.metadata.sorted_tables):
            conn.execute(table.delete())


def seed(
    user_id: int = 1,
    created_days_ago: int = 0,
    checkins=(),
) -> int:
    """Create a habit (optionally backdated) with the given check-ins.

    ``checkins`` is an iterable of ``(days_ago, completed, automaticity,
    hour_utc)`` tuples.
    """
    from datetime import datetime, timedelta

    db = SessionLocal()
    try:
        habit = models.Habit(
            user_id=user_id,
            name="Habit",
            if_then="if then",
            active=True,
            created_at=datetime.now(UTC)
            - timedelta(days=created_days_ago),
        )
        db.add(habit)
        db.flush()
        for days_ago, completed, automaticity, hour in checkins:
            day = datetime.now(UTC).date() - timedelta(days=days_ago)
            moment = datetime(
                day.year, day.month, day.day, hour, tzinfo=UTC
            )
            db.add(
                models.CheckIn(
                    habit_id=habit.id,
                    user_id=user_id,
                    date=day,
                    completed=completed,
                    automaticity=automaticity,
                    created_at=moment,
                )
            )
        db.commit()
        return habit.id
    finally:
        db.close()
