import os
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("USERS_URL", "http://users:8000")
os.environ.setdefault("HABITS_URL", "http://habits:8000")
os.environ.setdefault("TRACKING_URL", "http://tracking:8000")
os.environ.setdefault("INSIGHTS_URL", "http://insights:8000")
os.environ.setdefault("BILLING_URL", "http://billing:8000")
os.environ.setdefault("NOTIFICATIONS_URL", "http://notifications:8000")

import httpx
import main
from fastapi.testclient import TestClient


class Recorder:
    """Captures what the gateway actually sends downstream."""

    def __init__(self):
        self.requests: list[httpx.Request] = []
        self.status_code = 200
        self.body = {"ok": True}

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return httpx.Response(self.status_code, json=self.body)


@pytest.fixture
def client():
    recorder = Recorder()
    with TestClient(main.app) as test_client:
        # Replace the real connection pool with a mock transport.
        main.app.state.client = httpx.AsyncClient(
            transport=httpx.MockTransport(recorder.handler)
        )
        test_client.recorder = recorder
        yield test_client
