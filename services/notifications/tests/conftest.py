import os
import pathlib
import sys
import tempfile

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

_TMP = tempfile.mkdtemp(prefix="notifications-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP}/notifications.db"
os.environ["VAPID_PUBLIC_KEY"] = "test_public_key_b64url"
os.environ["VAPID_PRIVATE_KEY"] = "test_private_key_b64url"
# Keep the scheduler quiet in tests.
os.environ["REMINDER_LOOP"] = "off"

import main
import models
import reminders
from db import SessionLocal, engine
from fastapi.testclient import TestClient

USER = {"X-User-Id": "1"}
USER_B = {"X-User-Id": "2"}

SUBSCRIBE = {
    "endpoint": "https://push.example.com/endpoint-1",
    "keys": {"p256dh": "p256dh-key", "auth": "auth-key"},
    "tz_offset": 0,
    "lang": "en",
}


@pytest.fixture()
def client():
    models.Base.metadata.create_all(engine)
    with TestClient(main.app) as test_client:
        yield test_client
    with engine.begin() as conn:
        for table in reversed(models.Base.metadata.sorted_tables):
            conn.execute(table.delete())


@pytest.fixture()
def db():
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture()
def sent(monkeypatch):
    """Capture pushes instead of hitting the network."""
    calls: list[tuple[str, dict]] = []

    def fake_push(sub, payload):
        calls.append((sub.endpoint, payload))

    monkeypatch.setattr(reminders, "push", fake_push)
    return calls
