import hashlib
from datetime import UTC, datetime, timedelta

import jwt
import mailer
import models
from db import SessionLocal

PASSWORD = "motdepasse1"


def register(client, email="alice@test.dev", password=PASSWORD, name="Alice"):
    return client.post(
        "/register", json={"email": email, "password": password, "name": name}
    )


def test_register_rejects_short_password(client):
    resp = register(client, password="abc")
    assert resp.status_code == 422


def test_register_rejects_invalid_email(client):
    resp = register(client, email="not-an-email")
    assert resp.status_code == 422


def test_register_returns_tokens_and_user(client):
    resp = register(client)
    assert resp.status_code == 200
    payload = resp.json()
    assert set(payload) == {"token", "refresh_token", "user"}
    assert payload["user"]["email"] == "alice@test.dev"
    assert payload["user"]["name"] == "Alice"


def test_password_is_never_stored_in_clear(client):
    register(client)
    db = SessionLocal()
    try:
        user = db.query(models.User).one()
        assert user.password_hash != PASSWORD
        assert user.password_hash.startswith("$2b$")
    finally:
        db.close()


def test_duplicate_email_is_rejected(client):
    register(client)
    resp = register(client)
    assert resp.status_code == 400


def test_me_requires_identity_header(client):
    assert client.get("/me").status_code == 401
    assert client.get("/me", headers={"X-User-Id": "nope"}).status_code == 401


def test_me_returns_user(client):
    register(client)
    resp = client.get("/me", headers={"X-User-Id": "1"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "alice@test.dev"


def test_me_unknown_user_is_404(client):
    assert (
        client.get("/me", headers={"X-User-Id": "9999"}).status_code == 404
    )


def test_login_with_wrong_password_is_401(client):
    register(client)
    resp = client.post(
        "/login", json={"email": "alice@test.dev", "password": "wrongpass"}
    )
    assert resp.status_code == 401


def test_login_success(client):
    register(client)
    resp = client.post(
        "/login", json={"email": "alice@test.dev", "password": PASSWORD}
    )
    assert resp.status_code == 200
    token = resp.json()["token"]
    claims = jwt.decode(
        token, "test-secret-that-is-longer-than-32-bytes!!", algorithms=["HS256"]
    )
    assert claims["sub"] == "1"
    assert claims["typ"] == "access"


def test_login_is_rate_limited_after_five_failures(client):
    register(client)
    statuses = []
    for _ in range(6):
        resp = client.post(
            "/login",
            json={"email": "alice@test.dev", "password": "wrongpass"},
        )
        statuses.append(resp.status_code)
    assert statuses[:5] == [401] * 5
    assert statuses[5] == 429


def test_refresh_rotates_token(client):
    first = register(client).json()["refresh_token"]
    resp = client.post("/refresh", json={"refresh_token": first})
    assert resp.status_code == 200
    # The presented token is consumed: replaying it must fail.
    replay = client.post("/refresh", json={"refresh_token": first})
    assert replay.status_code == 401


def test_refresh_rejects_unknown_token(client):
    resp = client.post(
        "/refresh", json={"refresh_token": "x" * 64}
    )
    assert resp.status_code == 401


def test_logout_revokes_refresh_token(client):
    token = register(client).json()["refresh_token"]
    assert client.post("/logout", json={"refresh_token": token}).status_code == 200
    assert (
        client.post("/refresh", json={"refresh_token": token}).status_code == 401
    )


def test_refresh_token_hash_is_stored_not_the_raw_value(client):
    raw = register(client).json()["refresh_token"]
    db = SessionLocal()
    try:
        stored = {row.token_hash for row in db.query(models.RefreshToken)}
    finally:
        db.close()
    assert hashlib.sha256(raw.encode()).hexdigest() in stored
    assert raw not in stored


# --- Password reset -----------------------------------------------------------

def _extract_token(url: str) -> str:
    from urllib.parse import parse_qs, urlparse

    return parse_qs(urlparse(url).query)["token"][0]


def _capture_reset_link(client, monkeypatch, email):
    """Perform forgot-password and return the raw token from the link."""
    sent = {}

    def fake_send(to, reset_url, ttl_minutes=30):
        sent["to"] = to
        sent["url"] = reset_url

    monkeypatch.setattr(mailer, "send_reset_email", fake_send)
    resp = client.post("/forgot-password", json={"email": email})
    assert resp.status_code == 200
    assert "url" in sent, "an email should have been sent for an existing account"
    return _extract_token(sent["url"])


def test_forgot_password_answers_200_for_unknown_email(client):
    resp = client.post("/forgot-password", json={"email": "ghost@test.dev"})
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


def test_forgot_password_gives_the_same_answer_whether_or_not_the_account_exists(
    client,
):
    register(client)
    known = client.post("/forgot-password", json={"email": "alice@test.dev"})
    unknown = client.post("/forgot-password", json={"email": "ghost@test.dev"})
    assert known.status_code == unknown.status_code
    assert known.json() == unknown.json()


def test_forgot_password_stores_only_the_token_hash(client, monkeypatch):
    register(client)
    raw = _capture_reset_link(client, monkeypatch, "alice@test.dev")
    db = SessionLocal()
    try:
        user = db.query(models.User).one()
        stored = user.reset_token_hash
        assert user.reset_expires_at is not None
    finally:
        db.close()
    assert stored == hashlib.sha256(raw.encode()).hexdigest()
    assert stored != raw


def test_reset_password_with_valid_token_works(client, monkeypatch):
    register(client)
    token = _capture_reset_link(client, monkeypatch, "alice@test.dev")

    resp = client.post(
        "/reset-password", json={"token": token, "password": "nouveau-motdepasse"}
    )
    assert resp.status_code == 200

    assert (
        client.post(
            "/login",
            json={"email": "alice@test.dev", "password": "nouveau-motdepasse"},
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/login", json={"email": "alice@test.dev", "password": PASSWORD}
        ).status_code
        == 401
    )


def test_reset_password_revokes_every_existing_session(client, monkeypatch):
    refresh = register(client).json()["refresh_token"]
    token = _capture_reset_link(client, monkeypatch, "alice@test.dev")
    client.post("/reset-password", json={"token": token, "password": PASSWORD * 2})
    resp = client.post("/refresh", json={"refresh_token": refresh})
    assert resp.status_code == 401


def test_reset_password_rejects_expired_token(client, monkeypatch):
    register(client)
    token = _capture_reset_link(client, monkeypatch, "alice@test.dev")
    db = SessionLocal()
    try:
        user = db.query(models.User).one()
        user.reset_expires_at = datetime.now(UTC) - timedelta(minutes=1)
        db.commit()
    finally:
        db.close()
    resp = client.post(
        "/reset-password", json={"token": token, "password": PASSWORD * 2}
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Invalid or expired reset link"


def test_reset_password_token_is_single_use(client, monkeypatch):
    register(client)
    token = _capture_reset_link(client, monkeypatch, "alice@test.dev")
    payload = {"token": token, "password": PASSWORD * 2}
    assert client.post("/reset-password", json=payload).status_code == 200
    # Replay with the same token: the link was consumed.
    payload["password"] = PASSWORD * 3
    assert client.post("/reset-password", json=payload).status_code == 400


def test_reset_password_rejects_unknown_token(client):
    resp = client.post(
        "/reset-password", json={"token": "y" * 43, "password": PASSWORD * 2}
    )
    assert resp.status_code == 400


def test_reset_password_requires_a_strong_password(client, monkeypatch):
    register(client)
    token = _capture_reset_link(client, monkeypatch, "alice@test.dev")
    resp = client.post("/reset-password", json={"token": token, "password": "abc"})
    assert resp.status_code == 422


def test_forgot_password_is_rate_limited_per_email(client):
    register(client)
    statuses = []
    for _ in range(4):
        resp = client.post("/forgot-password", json={"email": "alice@test.dev"})
        statuses.append(resp.status_code)
    assert statuses[:3] == [200] * 3
    assert statuses[3] == 429
