import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import UTC, datetime

import models
import schemas
import stripe
import stripe_api
from db import engine, get_db
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("billing")

# Statuses that still entitle the user to the paid plan (past_due covers
# Stripe's dunning retries after a failed renewal).
PAID_STATUSES = ("active", "trialing", "past_due")
APP_URL = os.environ.get("APP_URL", "http://localhost:5173").rstrip("/")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Schema is owned by the `migrations` service (Alembic), not by us.
    yield
    engine.dispose()


app = FastAPI(title="Billing Service", lifespan=lifespan)


def require_user_id(x_user_id: str | None = Header(None)) -> int:
    if not x_user_id:
        raise HTTPException(401, "Authentication required")
    try:
        return int(x_user_id)
    except ValueError:
        raise HTTPException(401, "Invalid user identity") from None


def entitled_plan(row: models.BillingSubscription | None) -> str:
    """Plan the user currently pays for ('free' when nothing applies)."""
    if row is None:
        return "free"
    if row.plan == "lifetime":
        return "lifetime"
    if row.plan == "pro" and row.status in PAID_STATUSES:
        return "pro"
    return "free"


@app.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(503, "database unavailable") from None
    return {"status": "ok"}


@app.get("/")
def status(
    user_id: int = Depends(require_user_id),
    db: Session = Depends(get_db),
):
    row = (
        db.query(models.BillingSubscription).filter_by(user_id=user_id).first()
    )
    customer = db.query(models.BillingCustomer).filter_by(user_id=user_id).first()
    return {
        "plan": entitled_plan(row),
        "subscription_status": row.status if row else None,
        "current_period_end": (
            row.current_period_end.isoformat()
            if row and row.current_period_end
            else None
        ),
        "cancel_at_period_end": bool(row.cancel_at_period_end) if row else False,
        "has_customer": customer is not None,
    }


@app.post("/checkout")
def checkout(
    body: schemas.CheckoutIn,
    user_id: int = Depends(require_user_id),
    db: Session = Depends(get_db),
):
    env_name = "STRIPE_PRICE_PRO" if body.plan == "pro" else "STRIPE_PRICE_LIFETIME"
    price = os.environ.get(env_name, "").strip()
    if not price:
        raise HTTPException(503, "Billing is not configured")

    customer = db.query(models.BillingCustomer).filter_by(user_id=user_id).first()
    try:
        url = stripe_api.create_checkout_session(
            customer=customer.stripe_customer_id if customer else None,
            price=price,
            mode="subscription" if body.plan == "pro" else "payment",
            plan=body.plan,
            user_id=user_id,
            success_url=f"{APP_URL}/plan?checkout=success",
            cancel_url=f"{APP_URL}/plan?checkout=cancel",
        )
    except stripe_api.ConfigurationError:
        raise HTTPException(503, "Billing is not configured") from None
    logger.info("checkout started user=%s plan=%s", user_id, body.plan)
    return {"url": url}


@app.post("/portal")
def portal(
    user_id: int = Depends(require_user_id),
    db: Session = Depends(get_db),
):
    customer = db.query(models.BillingCustomer).filter_by(user_id=user_id).first()
    if customer is None:
        raise HTTPException(400, "No billing account yet")
    try:
        url = stripe_api.create_portal_session(
            customer=customer.stripe_customer_id,
            return_url=f"{APP_URL}/plan",
        )
    except stripe_api.ConfigurationError:
        raise HTTPException(503, "Billing is not configured") from None
    return {"url": url}


# --- Webhooks ----------------------------------------------------------------
# Handlers never call the Stripe API back: everything they need is in the
# event payload (keeps the endpoint fast and idempotent under retries).


def _upsert_customer(db: Session, user_id: int, stripe_customer_id: str) -> None:
    row = db.query(models.BillingCustomer).filter_by(user_id=user_id).first()
    if row is None:
        db.add(
            models.BillingCustomer(
                user_id=user_id, stripe_customer_id=stripe_customer_id
            )
        )
    else:
        row.stripe_customer_id = stripe_customer_id
    db.commit()


def _upsert_subscription(db: Session, user_id: int, **fields) -> None:
    row = db.query(models.BillingSubscription).filter_by(user_id=user_id).first()
    if row is None:
        db.add(models.BillingSubscription(user_id=user_id, **fields))
    else:
        for key, value in fields.items():
            setattr(row, key, value)
    db.commit()


def _user_from_attribution(db: Session, obj: dict) -> int | None:
    """Resolve the user from customer id or metadata (checkout sets both)."""
    customer_id = obj.get("customer")
    if customer_id:
        customer = (
            db.query(models.BillingCustomer)
            .filter_by(stripe_customer_id=customer_id)
            .first()
        )
        if customer is not None:
            return customer.user_id
    metadata = obj.get("metadata") or {}
    raw = metadata.get("user_id") or obj.get("client_reference_id")
    try:
        return int(raw) if raw else None
    except (TypeError, ValueError):
        return None


def _from_ts(ts) -> datetime | None:
    return datetime.fromtimestamp(ts, UTC) if ts else None


def handle_checkout_completed(db: Session, session: dict) -> None:
    user_id = _user_from_attribution(db, session)
    if user_id is None:
        logger.warning("checkout without user attribution: %s", session.get("id"))
        return
    if session.get("customer"):
        _upsert_customer(db, user_id, session["customer"])
    metadata = session.get("metadata") or {}
    if metadata.get("plan") == "lifetime":
        _upsert_subscription(
            db,
            user_id,
            plan="lifetime",
            status="active",
            stripe_subscription_id=None,
            price_id="",
            current_period_end=None,
            cancel_at_period_end=False,
        )
    else:
        _upsert_subscription(
            db,
            user_id,
            plan="pro",
            status="active",
            stripe_subscription_id=session.get("subscription"),
        )
    logger.info("checkout completed user=%s plan=%s", user_id, metadata.get("plan"))


def handle_subscription(db: Session, sub: dict) -> None:
    """customer.subscription.updated / .deleted — full object in the payload."""
    user_id = _user_from_attribution(db, sub)
    if user_id is None:
        logger.warning("subscription without user attribution: %s", sub.get("id"))
        return
    if sub.get("customer"):
        _upsert_customer(db, user_id, sub["customer"])

    price_id = ""
    items = (sub.get("items") or {}).get("data") or []
    if items:
        price_id = ((items[0].get("price") or {}).get("id")) or ""
    period_end = sub.get("current_period_end")
    _upsert_subscription(
        db,
        user_id,
        plan="pro",
        status=sub.get("status") or "canceled",
        stripe_subscription_id=sub.get("id"),
        price_id=price_id,
        current_period_end=_from_ts(period_end),
        cancel_at_period_end=bool(sub.get("cancel_at_period_end")),
    )
    logger.info(
        "subscription synced user=%s status=%s", user_id, sub.get("status")
    )


def handle_invoice_paid(db: Session, invoice: dict) -> None:
    """A renewal succeeded: re-activate the stored subscription row."""
    sub_id = invoice.get("subscription")
    if not sub_id:
        # Newer invoice payloads nest the reference under `parent`.
        parent = invoice.get("parent") or {}
        sub_id = (parent.get("subscription_details") or {}).get("subscription")
    if not sub_id:
        logger.info("invoice.paid without subscription reference")
        return
    row = (
        db.query(models.BillingSubscription)
        .filter_by(stripe_subscription_id=sub_id)
        .first()
    )
    if row is not None and row.status not in PAID_STATUSES:
        row.status = "active"
        db.commit()
        logger.info("invoice paid → subscription reactivated user=%s", row.user_id)


HANDLERS = {
    "checkout.session.completed": handle_checkout_completed,
    "customer.subscription.updated": handle_subscription,
    "customer.subscription.deleted": handle_subscription,
    "invoice.paid": handle_invoice_paid,
}


@app.post("/webhooks")
async def webhooks(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")
    secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    if not secret:
        raise HTTPException(503, "STRIPE_WEBHOOK_SECRET is not configured")
    try:
        # Verifies the HMAC signature (and raises on tampered payloads).
        stripe.Webhook.construct_event(payload, signature, secret)
    except (ValueError, stripe.SignatureVerificationError):
        raise HTTPException(400, "Invalid signature") from None

    # Handle plain dicts: StripeObject does not expose .get().
    event = json.loads(payload)
    event_type = event.get("type", "")
    handler = HANDLERS.get(event_type)
    if handler is None:
        logger.info("ignoring event type=%s", event_type)
        return {"received": True}
    handler(db, event.get("data", {}).get("object") or {})
    return {"received": True}
