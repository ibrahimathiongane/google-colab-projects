import asyncio
import logging
import os
from contextlib import asynccontextmanager

import models
import reminders
import schemas
from db import SessionLocal, engine, get_db
from fastapi import Depends, FastAPI, Header, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("notifications")

REMINDER_INTERVAL = int(os.environ.get("REMINDER_INTERVAL_SECONDS", "30"))


def _tick() -> None:
    """One scheduler pass (runs in a thread — pywebpush blocks on HTTP)."""
    db = SessionLocal()
    try:
        sent = reminders.send_due(db)
        if sent:
            logger.info("tick sent %s reminder(s)", sent)
    finally:
        db.close()


async def reminder_loop() -> None:
    while True:
        await asyncio.sleep(REMINDER_INTERVAL)
        try:
            await asyncio.to_thread(_tick)
        except Exception:  # the loop must survive anything one tick throws
            logger.exception("reminder tick failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Schema is owned by the `migrations` service (Alembic), not by us.
    # Tests (and one-off runs) can silence the scheduler with REMINDER_LOOP=off.
    task = None
    if os.environ.get("REMINDER_LOOP", "on").lower() != "off":
        task = asyncio.create_task(reminder_loop())
    try:
        yield
    finally:
        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        engine.dispose()


app = FastAPI(title="Notifications Service", lifespan=lifespan)


def require_user_id(x_user_id: str | None = Header(None)) -> int:
    if not x_user_id:
        raise HTTPException(401, "Authentication required")
    try:
        return int(x_user_id)
    except ValueError:
        raise HTTPException(401, "Invalid user identity") from None


def _configured(name: str) -> str:
    return os.environ.get(name, "").strip()


@app.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(503, "database unavailable") from None
    return {"status": "ok"}


@app.get("/vapid-public-key")
def vapid_public_key():
    key = _configured("VAPID_PUBLIC_KEY")
    if not key:
        raise HTTPException(503, "Notifications are not configured")
    return {"publicKey": key}


@app.get("/")
def status(
    user_id: int = Depends(require_user_id),
    db: Session = Depends(get_db),
):
    count = (
        db.query(models.PushSubscription).filter_by(user_id=user_id).count()
    )
    return {"subscribed": count > 0}


@app.post("/subscribe")
def subscribe(
    body: schemas.SubscribeIn,
    user_id: int = Depends(require_user_id),
    db: Session = Depends(get_db),
):
    if not _configured("VAPID_PUBLIC_KEY"):
        # Never let users enable a reminder that could never be delivered.
        raise HTTPException(503, "Notifications are not configured")

    row = (
        db.query(models.PushSubscription)
        .filter_by(endpoint=body.endpoint)
        .first()
    )
    if row is None:
        db.add(
            models.PushSubscription(
                user_id=user_id,
                endpoint=body.endpoint,
                p256dh=body.keys.p256dh,
                auth=body.keys.auth,
                tz_offset=body.tz_offset,
                lang=body.lang,
            )
        )
    else:
        # The endpoint identifies the device: refresh it for the caller
        # (keys rotate, and a re-login may change tz/language).
        row.user_id = user_id
        row.p256dh = body.keys.p256dh
        row.auth = body.keys.auth
        row.tz_offset = body.tz_offset
        row.lang = body.lang
    db.commit()
    return {"subscribed": True}


@app.post("/unsubscribe")
def unsubscribe(
    body: schemas.UnsubscribeIn,
    user_id: int = Depends(require_user_id),
    db: Session = Depends(get_db),
):
    # Scoped by user: never touch another account's subscription.
    row = (
        db.query(models.PushSubscription)
        .filter_by(endpoint=body.endpoint, user_id=user_id)
        .first()
    )
    if row is not None:
        db.delete(row)
        db.commit()
    return {"subscribed": False}
