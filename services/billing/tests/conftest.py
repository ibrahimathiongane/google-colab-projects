import os
import pathlib
import sys
import tempfile

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

_TMP = tempfile.mkdtemp(prefix="billing-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP}/billing.db"
os.environ["STRIPE_SECRET_KEY"] = "sk_test_dummy_key_not_used_in_tests"
os.environ["STRIPE_WEBHOOK_SECRET"] = "whsec_test_secret"
os.environ["STRIPE_PRICE_PRO"] = "price_pro_test"
os.environ["STRIPE_PRICE_LIFETIME"] = "price_lifetime_test"

import main
import models
from db import engine
from fastapi.testclient import TestClient

USER = {"X-User-Id": "1"}


@pytest.fixture()
def client():
    models.Base.metadata.create_all(engine)
    with TestClient(main.app) as test_client:
        yield test_client
    with engine.begin() as conn:
        for table in reversed(models.Base.metadata.sorted_tables):
            conn.execute(table.delete())
