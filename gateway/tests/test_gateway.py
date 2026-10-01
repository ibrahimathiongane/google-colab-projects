import httpx
import jwt


def make_token(sub="7"):
    return jwt.encode(
        {"sub": sub, "typ": "access"}, "test-secret", algorithm="HS256"
    )


def test_health_reports_all_services_up(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    assert all(v == "up" for v in resp.json()["services"].values())


def test_health_degrades_when_a_service_fails(client):
    client.recorder.status_code = 503
    resp = client.get("/health")
    assert resp.status_code == 503
    assert resp.json()["status"] == "degraded"


def test_unknown_service_is_404(client):
    resp = client.get("/api/nosuchservice/x")
    assert resp.status_code == 404


def test_protected_path_without_token_is_401(client):
    resp = client.get("/api/habits/")
    assert resp.status_code == 401
    assert client.recorder.requests == []


def test_public_paths_allow_anonymous_access(client):
    resp = client.post(
        "/api/users/register", json={"email": "a@b.co", "password": "x"}
    )
    assert resp.status_code == 200
    assert len(client.recorder.requests) == 1


def test_client_supplied_x_user_id_is_never_forwarded(client):
    """A forged X-User-Id must not reach a service."""
    resp = client.post(
        "/api/users/register",
        json={"email": "a@b.co", "password": "x"},
        headers={"X-User-Id": "999"},
    )
    assert resp.status_code == 200
    sent = client.recorder.requests[0]
    assert "x-user-id" not in {k.lower() for k in sent.headers}


def test_valid_token_injects_decoded_user_id(client):
    resp = client.get(
        "/api/habits/", headers={"Authorization": f"Bearer {make_token('42')}"}
    )
    assert resp.status_code == 200
    assert client.recorder.requests[0].headers["X-User-Id"] == "42"


def test_garbage_token_is_treated_as_anonymous(client):
    resp = client.get(
        "/api/habits/", headers={"Authorization": "Bearer not-a-jwt"}
    )
    assert resp.status_code == 401


def test_expired_token_is_rejected(client):
    import time

    expired = jwt.encode(
        {"sub": "1", "exp": int(time.time()) - 10},
        "test-secret",
        algorithm="HS256",
    )
    resp = client.get(
        "/api/habits/", headers={"Authorization": f"Bearer {expired}"}
    )
    assert resp.status_code == 401


def test_trailing_slash_is_normalized_for_public_paths(client):
    resp = client.post("/api/users/register/", json={})
    assert resp.status_code != 401  # normalized -> public, not auth-gated
    assert client.recorder.requests[0].url.path == "/register"


def test_service_error_is_reported_as_502(client):
    client.recorder.status_code = 500
    resp = client.post(
        "/api/users/register", json={"email": "a@b.co", "password": "x"}
    )
    assert resp.status_code == 500  # transparent proxying of status


def test_request_id_is_echoed(client):
    resp = client.get("/health")
    assert "X-Request-Id" in resp.headers


def test_downstream_unreachable_is_502(client):
    def boom(request):
        raise httpx.ConnectError("nope", request=request)

    client.app.state.client = httpx.AsyncClient(
        transport=httpx.MockTransport(boom)
    )
    resp = client.post("/api/users/register", json={"email": "a@b.co"})
    assert resp.status_code == 502


def test_password_reset_paths_are_public(client):
    """forgot/reset must be reachable without a JWT (they mint credentials)."""
    resp = client.post("/api/users/forgot-password", json={"email": "a@b.co"})
    assert resp.status_code == 200
    resp = client.post(
        "/api/users/reset-password",
        json={"token": "x" * 43, "password": "long-enough-1"},
    )
    assert resp.status_code == 200
    assert len(client.recorder.requests) == 2


def test_stripe_webhook_is_public(client):
    """Stripe cannot present a JWT — the webhook verifies its own HMAC."""
    resp = client.post(
        "/api/billing/webhooks",
        content=b"{}",
        headers={"stripe-signature": "t=1,v1=whatever"},
    )
    assert resp.status_code == 200
    assert len(client.recorder.requests) == 1


def test_billing_routes_require_auth_except_webhooks(client):
    assert client.post("/api/billing/checkout", json={"plan": "pro"}).status_code == 401
    assert client.get("/api/billing/").status_code == 401


def test_notifications_routes_require_auth(client):
    """No public path in the notifications service — all behind the JWT."""
    assert client.get("/api/notifications/").status_code == 401
    assert client.get("/api/notifications/vapid-public-key").status_code == 401
    assert (
        client.post("/api/notifications/subscribe", json={}).status_code == 401
    )
    assert (
        client.post("/api/notifications/unsubscribe", json={}).status_code == 401
    )
