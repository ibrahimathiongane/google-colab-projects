"""Reminder scheduling: which devices get a push right now, and sending it.

Time model
----------
Each subscription stores the device's UTC offset (minutes east) captured
at subscribe time — exactly what the insights page already sends as
``tz_offset``. "Now" for a device is ``utcnow + tz_offset``, and a habit
is due between its ``cue_time`` and ``cue_time + CUE_WINDOW_MINUTES``.
The window absorbs the loop's 30-second granularity so a reminder is
never missed (the anti-duplicate log keeps it to exactly one send).

Dedupe: ``reminder_logs`` has a unique (subscription_id, habit_id, date)
— one push per device, per habit, per *local* day. Habits already
completed that day are skipped; a failed send is not logged, so it is
retried on the next tick.
"""

import json
import logging
import os
from datetime import UTC, date, datetime, timedelta

import models
from pywebpush import WebPushException, webpush
from sqlalchemy.orm import Session

logger = logging.getLogger("notifications")

# Send window: from cue_time up to this many minutes late.
CUE_WINDOW_MINUTES = 5
# A stale reminder is useless — give the browser 10 minutes to show it.
PUSH_TTL_SECONDS = 600
DAY_MINUTES = 24 * 60

# Push copy lives here (the service composes the payload; the SW only
# displays it). Falls back to English for unknown/empty languages.
COPY = {
    "en": {
        "title": "Habit reminder",
        "body": "It's time for \u201c{name}\u201d.",
        "body_anchor": "It's time for \u201c{name}\u201d \u2014 {anchor}.",
    },
    "fr": {
        "title": "Rappel d'habitude",
        "body": "Il est l'heure de \u00ab\u00a0{name}\u00bb.",
        "body_anchor": "Il est l'heure de \u00ab\u00a0{name}\u00bb \u2014 {anchor}.",
    },
}


def _minutes(hhmm: str) -> int | None:
    """Parse 'HH:MM' into minutes past midnight (None when unusable)."""
    try:
        hours, minutes = hhmm.split(":")
        value = int(hours) * 60 + int(minutes)
    except (ValueError, AttributeError):
        return None
    return value if 0 <= value < DAY_MINUTES else None


def compose_payload(lang: str, habit: models.Habit) -> dict:
    copy = COPY.get(lang) or COPY["en"]
    body_key = "body_anchor" if habit.anchor else "body"
    body = copy[body_key].format(name=habit.name, anchor=habit.anchor)
    return {"title": copy["title"], "body": body, "url": "/"}


def push(sub: models.PushSubscription, payload: dict) -> None:
    """Send one Web Push message (kept thin so tests can monkeypatch it)."""
    webpush(
        subscription_info={
            "endpoint": sub.endpoint,
            "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
        },
        data=json.dumps(payload, ensure_ascii=False),
        vapid_private_key=os.environ.get("VAPID_PRIVATE_KEY", ""),
        vapid_claims={"sub": os.environ.get("VAPID_SUBJECT", "mailto:admin@localhost")},
        ttl=PUSH_TTL_SECONDS,
    )


def due_habits(
    db: Session, sub: models.PushSubscription, now: datetime | None = None
) -> list[tuple[models.Habit, date]]:
    """Habits to remind THIS device about right now, with their local day.

    The day belongs to the cue: a 23:58 cue reminded at 00:01 belongs to
    yesterday's log (and checks yesterday's check-in), not today's.
    """
    now = now or datetime.now(UTC)
    local = now + timedelta(minutes=sub.tz_offset)
    local_minutes = local.hour * 60 + local.minute
    day = local.date()

    habits = (
        db.query(models.Habit)
        .filter(models.Habit.user_id == sub.user_id, models.Habit.active.is_(True))
        .all()
    )

    candidates: list[tuple[models.Habit, date]] = []
    for habit in habits:
        cue = _minutes(habit.cue_time)
        if cue is None:
            continue
        # Minutes since the cue (wrapping past midnight so a 23:58 cue
        # still fires at 00:01 — but 08:00 does not fire at 00:10).
        delta = local_minutes - cue
        if delta < 0:
            delta += DAY_MINUTES
            cue_day = day - timedelta(days=1)
        else:
            cue_day = day
        if delta <= CUE_WINDOW_MINUTES:
            candidates.append((habit, cue_day))

    due = []
    for habit, cue_day in candidates:
        completed = (
            db.query(models.CheckIn)
            .filter_by(habit_id=habit.id, date=cue_day, completed=True)
            .first()
            is not None
        )
        logged = (
            db.query(models.ReminderLog)
            .filter_by(subscription_id=sub.id, habit_id=habit.id, date=cue_day)
            .first()
            is not None
        )
        if not completed and not logged:
            due.append((habit, cue_day))
    return due


def send_due(db: Session, now: datetime | None = None) -> int:
    """Send every pending reminder. Returns how many pushes went out."""
    now = now or datetime.now(UTC)
    sent = 0
    for sub in db.query(models.PushSubscription).all():
        for habit, cue_day in due_habits(db, sub, now):
            try:
                push(sub, compose_payload(sub.lang, habit))
            except (WebPushException, OSError) as exc:
                # WebPushException covers HTTP answers; connection errors
                # surface as OSError (requests' errors inherit IOError).
                status = getattr(getattr(exc, "response", None), "status_code", None)
                if status in (404, 410):
                    # The push service says the endpoint is gone — drop it.
                    logger.info("stale subscription removed endpoint=%s", sub.endpoint)
                    db.delete(sub)
                    db.commit()
                    break
                # Transient failure: no log row, so the next tick retries.
                logger.warning(
                    "push failed user=%s habit=%s status=%s",
                    sub.user_id,
                    habit.id,
                    status,
                )
                continue
            db.add(
                models.ReminderLog(
                    subscription_id=sub.id, habit_id=habit.id, date=cue_day
                )
            )
            db.commit()
            sent += 1
            logger.info("reminder sent user=%s habit=%s", sub.user_id, habit.id)
    return sent
