import os
import pathlib
import sys
import tempfile

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

_TMP = tempfile.mkdtemp(prefix="tracking-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP}/tracking.db"

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


def make_habit(user_id: int, name: str = "Habit") -> int:
    db = SessionLocal()
    try:
        habit = models.Habit(user_id=user_id, name=name, active=True)
        db.add(habit)
        db.commit()
        db.refresh(habit)
        return habit.id
    finally:
        db.close()
