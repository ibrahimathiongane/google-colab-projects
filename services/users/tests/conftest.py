import os
import pathlib
import sys
import tempfile

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

_TMP = tempfile.mkdtemp(prefix="users-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP}/users.db"
os.environ["JWT_SECRET"] = "test-secret-that-is-longer-than-32-bytes!!"

import main
import models
import rate_limit
from db import engine
from fastapi.testclient import TestClient


@pytest.fixture()
def client():
    models.Base.metadata.create_all(engine)
    rate_limit.reset()
    with TestClient(main.app) as test_client:
        yield test_client
    with engine.begin() as conn:
        for table in reversed(models.Base.metadata.sorted_tables):
            conn.execute(table.delete())
    rate_limit.reset()
