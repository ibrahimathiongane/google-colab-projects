import hashlib

import jwt
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
