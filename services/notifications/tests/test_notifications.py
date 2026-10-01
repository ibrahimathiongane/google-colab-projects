from datetime import UTC, date, datetime
from types import SimpleNamespace

import models
import reminders
from conftest import SUBSCRIBE, USER, USER_B
from pywebpush import WebPushException


def make_habit(db, **overrides):
    habit = models.Habit(
        user_id=1,
        name="Boire un verre",
        anchor="après mon café",
        cue_time="08:00",
        active=True,
    )
    for key, value in overrides.items():
        setattr(habit, key, value)
    db.add(habit)
    db.commit()
    return habit


def make_subscription(db, **overrides):
    row = models.PushSubscription(
        user_id=1,
        endpoint=SUBSCRIBE["endpoint"],
        p256dh=SUBSCRIBE["keys"]["p256dh"],
        auth=SUBSCRIBE["keys"]["auth"],
        tz_offset=0,
        lang="en",
    )
    for key, value in overrides.items():
        setattr(row, key, value)
    db.add(row)
    db.commit()
    return row


def make_checkin(db, habit_id, day, completed=True):
    db.add(
        models.CheckIn(habit_id=habit_id, date=day, completed=completed)
    )
    db.commit()


# --- Endpoints ---------------------------------------------------------------


def test_requires_authentication(client):
    assert client.get("/").status_code == 401
    assert client.post("/subscribe", json=SUBSCRIBE).status_code == 401
    assert (
        client.post("/unsubscribe", json={"endpoint": "x"}).status_code == 401
    )


def test_vapid_public_key_is_returned(client):
    resp = client.get("/vapid-public-key", headers=USER)
    assert resp.status_code == 200
    assert resp.json() == {"publicKey": "test_public_key_b64url"}


def test_unconfigured_service_refuses_to_subscribe(client, monkeypatch):
    monkeypatch.delenv("VAPID_PUBLIC_KEY")
    assert client.get("/vapid-public-key", headers=USER).status_code == 503
    resp = client.post("/subscribe", json=SUBSCRIBE, headers=USER)
    assert resp.status_code == 503
    assert resp.json()["detail"] == "Notifications are not configured"


def test_subscribe_upserts_by_endpoint(client):
    resp = client.post("/subscribe", json=SUBSCRIBE, headers=USER)
    assert resp.status_code == 200
    assert resp.json() == {"subscribed": True}
    assert client.get("/", headers=USER).json() == {"subscribed": True}

    # Same endpoint again with a new tz/lang → one row, refreshed.
    updated = {**SUBSCRIBE, "tz_offset": 120, "lang": "fr"}
    client.post("/subscribe", json=updated, headers=USER)

    from db import SessionLocal

    db = SessionLocal()
    try:
        rows = db.query(models.PushSubscription).all()
        assert len(rows) == 1
        assert rows[0].tz_offset == 120
        assert rows[0].lang == "fr"
        assert rows[0].user_id == 1
    finally:
        db.close()


def test_unsubscribe_scopes_to_the_owner(client):
    from db import SessionLocal

    db = SessionLocal()
    try:
        make_subscription(db, user_id=1)
    finally:
        db.close()

    # Another user cannot remove it.
    resp = client.post(
        "/unsubscribe", json={"endpoint": SUBSCRIBE["endpoint"]},
        headers=USER_B,
    )
    assert resp.status_code == 200
    assert client.get("/", headers=USER).json() == {"subscribed": True}

    # The owner can — and the call is idempotent.
    for _ in range(2):
        resp = client.post(
            "/unsubscribe",
            json={"endpoint": SUBSCRIBE["endpoint"]},
            headers=USER,
        )
        assert resp.status_code == 200
        assert resp.json() == {"subscribed": False}
    assert client.get("/", headers=USER).json() == {"subscribed": False}


# --- Scheduler ---------------------------------------------------------------


def test_reminder_is_sent_within_the_cue_window(client, db, sent):
    make_habit(db, cue_time="08:00")
    make_subscription(db)

    now = datetime(2026, 10, 1, 8, 1, tzinfo=UTC)
    assert reminders.send_due(db, now=now) == 1
    assert len(sent) == 1
    endpoint, payload = sent[0]
    assert endpoint == SUBSCRIBE["endpoint"]
    assert payload["title"] == "Habit reminder"
    assert "Boire un verr" in payload["body"]
    assert "après mon café" in payload["body"]
    assert payload["url"] == "/"

    # Exactly one push per device/habit/day: the log blocks a second pass.
    assert reminders.send_due(db, now=now) == 0
    assert len(sent) == 1


def test_no_reminder_outside_the_window(client, db, sent):
    make_habit(db, cue_time="08:00")
    make_subscription(db)

    # Too early, too late, far away.
    for stamp in ("07:55", "09:00", "12:30"):
        hour, minute = map(int, stamp.split(":"))
        now = datetime(2026, 10, 1, hour, minute, tzinfo=UTC)
        assert reminders.send_due(db, now=now) == 0, stamp
    assert sent == []


def test_no_reminder_when_the_habit_is_completed(client, db, sent):
    habit = make_habit(db, cue_time="08:00")
    make_subscription(db)
    now = datetime(2026, 10, 1, 8, 1, tzinfo=UTC)

    # completed=False (user unchecked) → still worth reminding.
    make_checkin(db, habit.id, date(2026, 10, 1), completed=False)
    assert reminders.send_due(db, now=now) == 1

    make_checkin(db, habit.id, date(2026, 10, 1), completed=True)
    # The first send already logged today — use a fresh habit to isolate.
    second = make_habit(db, name="Étirer", cue_time="08:00")
    make_checkin(db, second.id, date(2026, 10, 1), completed=True)
    assert reminders.send_due(db, now=now) == 0


def test_reminder_honours_the_device_timezone(client, db, sent):
    make_habit(db, cue_time="08:00")
    make_subscription(db, tz_offset=120)  # UTC+2 (e.g. Paris)

    # 06:01 UTC = 08:01 local → due.
    assert reminders.send_due(db, now=datetime(2026, 10, 1, 6, 1, tzinfo=UTC)) == 1
    # 05:59 UTC = 07:59 local → too early (same day, nothing else to send).
    assert reminders.send_due(db, now=datetime(2026, 10, 1, 5, 59, tzinfo=UTC)) == 0


def test_inactive_habits_are_never_reminded(client, db, sent):
    make_habit(db, cue_time="08:00", active=False)
    make_subscription(db)
    now = datetime(2026, 10, 1, 8, 1, tzinfo=UTC)
    assert reminders.send_due(db, now=now) == 0
    assert sent == []


def test_french_copy_is_used_for_fr_devices(client, db, sent):
    make_habit(db, cue_time="08:00")
    make_subscription(db, lang="fr")
    reminders.send_due(db, now=datetime(2026, 10, 1, 8, 1, tzinfo=UTC))
    _, payload = sent[0]
    assert payload["title"] == "Rappel d'habitude"
    assert "Il est l'heure de" in payload["body"]


def test_cue_just_after_midnight_belongs_to_yesterday(client, db, sent):
    habit = make_habit(db, cue_time="23:58")
    make_subscription(db)
    now = datetime(2026, 10, 2, 0, 1, tzinfo=UTC)  # 3 minutes after the cue

    # Today's check-in must not block yesterday's cue.
    make_checkin(db, habit.id, date(2026, 10, 2), completed=True)
    assert reminders.send_due(db, now=now) == 1

    # The log lands on the cue's day, so tomorrow's pass won't re-send.
    from db import SessionLocal

    session = SessionLocal()
    try:
        logs = session.query(models.ReminderLog).all()
        assert [log.date for log in logs] == [date(2026, 10, 1)]
    finally:
        session.close()


def test_stale_subscription_is_deleted_on_gone_response(client, db, sent, monkeypatch):
    make_habit(db, cue_time="08:00")
    sub = make_subscription(db)

    def gone(subscription, payload):
        raise WebPushException(
            "Gone", response=SimpleNamespace(status_code=410)
        )

    monkeypatch.setattr(reminders, "push", gone)
    now = datetime(2026, 10, 1, 8, 1, tzinfo=UTC)
    assert reminders.send_due(db, now=now) == 0

    assert db.query(models.PushSubscription).filter_by(id=sub.id).first() is None
    # Nothing was logged for the failed send.
    assert db.query(models.ReminderLog).count() == 0


def test_transient_failure_is_retried_next_tick(client, db, sent, monkeypatch):
    make_habit(db, cue_time="08:00")
    make_subscription(db)
    now = datetime(2026, 10, 1, 8, 1, tzinfo=UTC)

    def boom(subscription, payload):
        raise WebPushException(
            "Internal", response=SimpleNamespace(status_code=500)
        )

    monkeypatch.setattr(reminders, "push", boom)
    assert reminders.send_due(db, now=now) == 0
    # Not logged → the next tick may retry and succeed.
    assert db.query(models.ReminderLog).count() == 0


def test_network_failure_keeps_the_subscription(client, db, sent, monkeypatch):
    """Connection errors (OSError) must not abort the pass or drop the sub."""
    make_habit(db, cue_time="08:00")
    make_subscription(db)
    now = datetime(2026, 10, 1, 8, 1, tzinfo=UTC)

    monkeypatch.setattr(
        reminders, "push", lambda *args: (_ for _ in ()).throw(OSError("down"))
    )
    assert reminders.send_due(db, now=now) == 0
    assert db.query(models.PushSubscription).count() == 1
    assert db.query(models.ReminderLog).count() == 0
