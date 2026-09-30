from datetime import date as date_cls
from datetime import timedelta

from conftest import USER_A, make_habit

TODAY = date_cls.today().isoformat()


def checkin(client, habit_id, day=TODAY, headers=USER_A, **overrides):
    payload = {"habit_id": habit_id, "date": day, "completed": True}
    payload.update(overrides)
    return client.post("/checkin", json=payload, headers=headers)


def test_requires_authentication(client):
    habit = make_habit(1)
    assert checkin(client, habit, headers={}).status_code == 401
    assert client.get("/streaks", headers={}).status_code == 401


def test_checkin_on_someone_elses_habit_is_404(client):
    victim_habit = make_habit(2)
    resp = checkin(client, victim_habit, headers=USER_A)
    assert resp.status_code == 404
    # Nothing was written for the attacker either.
    assert client.get("/streaks", headers=USER_A).json() == []


def test_checkin_is_upserted_per_day(client):
    habit = make_habit(1)
    assert checkin(client, habit).status_code == 200
    # Same day again: the row is updated, not duplicated.
    assert checkin(client, habit, completed=False).status_code == 200

    rows = client.get(f"/today?date={TODAY}", headers=USER_A).json()
    assert len(rows) == 1
    assert rows[0]["completed"] is False


def test_automaticity_bounds_are_enforced(client):
    habit = make_habit(1)
    assert checkin(client, habit, automaticity=0).status_code == 422
    assert checkin(client, habit, automaticity=11).status_code == 422
    assert checkin(client, habit, automaticity=7).status_code == 200


def test_invalid_date_is_422_not_500(client):
    habit = make_habit(1)
    assert checkin(client, habit, day="2026-02-30").status_code == 422
    assert checkin(client, habit, day="yesterday").status_code == 422


def test_today_rejects_malformed_date(client):
    assert (
        client.get("/today?date=not-a-date", headers=USER_A).status_code
        == 422
    )


def test_range_validates_bounds_and_ownership(client):
    habit = make_habit(1)
    other = make_habit(2)
    assert (
        client.get(
            f"/range?habit_id={habit}&days=0", headers=USER_A
        ).status_code
        == 422
    )
    assert (
        client.get(
            f"/range?habit_id={habit}&days=9999", headers=USER_A
        ).status_code
        == 422
    )
    assert (
        client.get(
            f"/range?habit_id={other}&days=30", headers=USER_A
        ).status_code
        == 404
    )


def _seed_days(habit_id: int, days_ago: list[int]):
    import models
    from db import SessionLocal

    db = SessionLocal()
    try:
        for offset in days_ago:
            db.add(
                models.CheckIn(
                    habit_id=habit_id,
                    user_id=1,
                    date=date_cls.today() - timedelta(days=offset),
                    completed=True,
                )
            )
        db.commit()
    finally:
        db.close()


def test_streak_counts_consecutive_days(client):
    habit = make_habit(1)
    _seed_days(habit, [0, 1, 2])
    streaks = client.get("/streaks", headers=USER_A).json()
    assert streaks[0]["streak"] == 3
    assert streaks[0]["completed_checkins"] == 3


def test_missing_today_keeps_the_streak_alive(client):
    """Grace: the day is not over, so yesterday's run still counts."""
    habit = make_habit(1)
    _seed_days(habit, [1, 2])
    assert client.get("/streaks", headers=USER_A).json()[0]["streak"] == 2


def test_a_gap_breaks_the_streak(client):
    habit = make_habit(1)
    _seed_days(habit, [0, 2])  # yesterday missing
    assert client.get("/streaks", headers=USER_A).json()[0]["streak"] == 1


def test_streak_is_not_capped_at_365(client):
    habit = make_habit(1)
    _seed_days(habit, list(range(0, 400)))
    assert client.get("/streaks", headers=USER_A).json()[0]["streak"] == 400


def test_streaks_only_include_own_habits(client):
    make_habit(1, "Mine")
    make_habit(2, "Theirs")
    assert len(client.get("/streaks", headers=USER_A).json()) == 1
