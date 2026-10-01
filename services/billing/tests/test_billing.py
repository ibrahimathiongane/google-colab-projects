import hashlib
import hmac
import json
import time

import main
import models
from db import SessionLocal

SECRET = "whsec_test_secret"
USER = {"X-User-Id": "1"}


def _sign(payload: bytes, secret: str = SECRET) -> str:
    """Stripe's signature scheme: HMAC-SHA256(secret, f"{ts}.{payload}")."""
    ts = int(time.time())
    mac = hmac.new(secret.encode(), f"{ts}.".encode() + payload, hashlib.sha256)
    return f"t={ts},v1={mac.hexdigest()}"


def post_event(client, event: dict, secret: str = SECRET, signature: str | None = None):
    raw = json.dumps(event).encode()
    sig = signature if signature is not None else _sign(raw, secret)
    return client.post("/webhooks", content=raw, headers={"stripe-signature": sig})


def event(etype: str, obj: dict) -> dict:
    return {"id": "evt_test", "object": "event", "type": etype, "data": {"object": obj}}


# --- Status -------------------------------------------------------------------


def test_status_defaults_to_free(client):
    resp = client.get("/", headers=USER)
    assert resp.status_code == 200
    assert resp.json() == {
        "plan": "free",
        "subscription_status": None,
        "current_period_end": None,
        "cancel_at_period_end": False,
        "has_customer": False,
    }


def test_status_requires_identity(client):
    assert client.get("/").status_code == 401


# --- Checkout / portal -------------------------------------------------------


def test_checkout_pro_uses_the_subscription_price(client, monkeypatch):
    captured = {}

    def fake_checkout(**kwargs):
        captured.update(kwargs)
        return "https://checkout.stripe.com/pay/cs_test"

    monkeypatch.setattr(main.stripe_api, "create_checkout_session", fake_checkout)
    resp = client.post("/checkout", json={"plan": "pro"}, headers=USER)
    assert resp.status_code == 200
    assert resp.json() == {"url": "https://checkout.stripe.com/pay/cs_test"}
    assert captured["mode"] == "subscription"
    assert captured["price"] == "price_pro_test"
    assert captured["customer"] is None
    assert captured["plan"] == "pro"
    assert captured["user_id"] == 1
    assert captured["success_url"].endswith("/plan?checkout=success")


def test_checkout_lifetime_uses_one_time_payment(client, monkeypatch):
    captured = {}
    monkeypatch.setattr(
        main.stripe_api,
        "create_checkout_session",
        lambda **kwargs: captured.update(kwargs) or "https://checkout.stripe.com/pay/one",
    )
    resp = client.post("/checkout", json={"plan": "lifetime"}, headers=USER)
    assert resp.status_code == 200
    assert captured["mode"] == "payment"
    assert captured["price"] == "price_lifetime_test"


def test_checkout_rejects_unknown_plan(client):
    resp = client.post("/checkout", json={"plan": "enterprise"}, headers=USER)
    assert resp.status_code == 422


def test_checkout_is_503_when_the_price_is_not_configured(client, monkeypatch):
    monkeypatch.delenv("STRIPE_PRICE_PRO")
    resp = client.post("/checkout", json={"plan": "pro"}, headers=USER)
    assert resp.status_code == 503


def test_portal_without_customer_is_400(client):
    resp = client.post("/portal", headers=USER)
    assert resp.status_code == 400


def test_portal_returns_the_stripe_url(client, monkeypatch):
    db = SessionLocal()
    try:
        db.add(
            models.BillingCustomer(user_id=1, stripe_customer_id="cus_123")
        )
        db.commit()
    finally:
        db.close()
    monkeypatch.setattr(
        main.stripe_api,
        "create_portal_session",
        lambda **kwargs: "https://billing.stripe.com/p/session",
    )
    resp = client.post("/portal", headers=USER)
    assert resp.status_code == 200
    assert resp.json() == {"url": "https://billing.stripe.com/p/session"}


# --- Webhooks -----------------------------------------------------------------


def test_webhook_rejects_an_invalid_signature(client):
    resp = post_event(
        client,
        event("checkout.session.completed", {}),
        signature="t=1,v1=deadbeef",
    )
    assert resp.status_code == 400


def test_webhook_ignores_unknown_event_types(client):
    resp = post_event(client, event("charge.refunded", {"id": "ch_1"}))
    assert resp.status_code == 200
    assert resp.json() == {"received": True}


def test_checkout_completed_lifetime_grants_lifetime(client):
    resp = post_event(
        client,
        event(
            "checkout.session.completed",
            {
                "id": "cs_1",
                "customer": "cus_life",
                "client_reference_id": "1",
                "subscription": None,
                "metadata": {"user_id": "1", "plan": "lifetime"},
            },
        ),
    )
    assert resp.status_code == 200
    status = client.get("/", headers=USER).json()
    assert status["plan"] == "lifetime"
    assert status["has_customer"] is True


def test_checkout_completed_pro_activates_the_plan(client):
    resp = post_event(
        client,
        event(
            "checkout.session.completed",
            {
                "id": "cs_2",
                "customer": "cus_pro",
                "client_reference_id": "1",
                "subscription": "sub_123",
                "metadata": {"user_id": "1", "plan": "pro"},
            },
        ),
    )
    assert resp.status_code == 200
    status = client.get("/", headers=USER).json()
    assert status["plan"] == "pro"
    assert status["subscription_status"] == "active"


def test_subscription_updated_syncs_status_and_period(client):
    # Establish the customer mapping first (checkout event).
    post_event(
        client,
        event(
            "checkout.session.completed",
            {
                "id": "cs_3",
                "customer": "cus_sync",
                "client_reference_id": "1",
                "subscription": "sub_sync",
                "metadata": {"user_id": "1", "plan": "pro"},
            },
        ),
    )
    resp = post_event(
        client,
        event(
            "customer.subscription.updated",
            {
                "id": "sub_sync",
                "customer": "cus_sync",
                "status": "past_due",
                "cancel_at_period_end": True,
                "current_period_end": 1893456000,  # 2030-01-01
                "items": {"data": [{"price": {"id": "price_pro_test"}}]},
                "metadata": {},
            },
        ),
    )
    assert resp.status_code == 200
    status = client.get("/", headers=USER).json()
    # past_due keeps the access (dunning grace) and is reported honestly.
    assert status["plan"] == "pro"
    assert status["subscription_status"] == "past_due"
    assert status["cancel_at_period_end"] is True
    assert status["current_period_end"].startswith("2030-01-01")


def test_subscription_deleted_falls_back_to_free(client):
    post_event(
        client,
        event(
            "checkout.session.completed",
            {
                "id": "cs_4",
                "customer": "cus_del",
                "client_reference_id": "1",
                "subscription": "sub_del",
                "metadata": {"user_id": "1", "plan": "pro"},
            },
        ),
    )
    assert client.get("/", headers=USER).json()["plan"] == "pro"

    resp = post_event(
        client,
        event(
            "customer.subscription.deleted",
            {
                "id": "sub_del",
                "customer": "cus_del",
                "status": "canceled",
                "metadata": {},
            },
        ),
    )
    assert resp.status_code == 200
    assert client.get("/", headers=USER).json()["plan"] == "free"


def test_invoice_paid_reactivates_a_subscription(client):
    post_event(
        client,
        event(
            "checkout.session.completed",
            {
                "id": "cs_5",
                "customer": "cus_inv",
                "client_reference_id": "1",
                "subscription": "sub_inv",
                "metadata": {"user_id": "1", "plan": "pro"},
            },
        ),
    )
    # Simulate a failed renewal that left the row in an unpaid state.
    db = SessionLocal()
    try:
        row = db.query(models.BillingSubscription).one()
        row.status = "canceled"
        db.commit()
    finally:
        db.close()

    resp = post_event(
        client,
        event("invoice.paid", {"id": "in_1", "subscription": "sub_inv"}),
    )
    assert resp.status_code == 200
    status = client.get("/", headers=USER).json()
    assert status["plan"] == "pro"
    assert status["subscription_status"] == "active"


def test_webhook_without_secret_is_503(client, monkeypatch):
    monkeypatch.delenv("STRIPE_WEBHOOK_SECRET")
    resp = post_event(client, event("invoice.paid", {}))
    assert resp.status_code == 503
