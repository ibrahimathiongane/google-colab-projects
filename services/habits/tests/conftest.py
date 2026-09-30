import os
import pathlib
import sys
import tempfile

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

_TMP = tempfile.mkdtemp(prefix="habits-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP}/habits.db"

import main
import models
from db import engine
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


def valid_habit(**overrides):
    payload = {
        "name": "Boire un verre",
        "anchor": "apres mon cafe",
        "tiny_behavior": "boire un verre d'eau",
        "celebration": "sourire",
        "cue_time": "08:30",
    }
    payload.update(overrides)
    return payload
