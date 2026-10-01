import main
from fastapi.testclient import TestClient

client = TestClient(main.app)


def test_upgrade_requires_a_matching_token(monkeypatch):
    monkeypatch.setenv("MIGRATE_TOKEN", "sekrit")
    assert client.post("/upgrade").status_code == 401
    res = client.post("/upgrade", headers={"X-Migrate-Token": "wrong"})
    assert res.status_code == 401


def test_upgrade_refuses_when_no_secret_is_configured(monkeypatch):
    monkeypatch.delenv("MIGRATE_TOKEN", raising=False)
    res = client.post("/upgrade", headers={"X-Migrate-Token": "anything"})
    assert res.status_code == 401


def test_upgrade_runs_alembic_to_head(monkeypatch):
    applied = []
    monkeypatch.setenv("MIGRATE_TOKEN", "sekrit")
    monkeypatch.setattr(
        main.command, "upgrade", lambda cfg, revision: applied.append(revision)
    )
    res = client.post("/upgrade", headers={"X-Migrate-Token": "sekrit"})
    assert res.status_code == 200
    assert res.json() == {"status": "upgraded"}
    assert applied == ["head"]


def test_health_is_public():
    assert client.get("/health").json() == {"status": "ok"}
