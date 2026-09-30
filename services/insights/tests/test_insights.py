from conftest import USER_A, USER_B, seed


def test_requires_authentication(client):
    assert client.get("/summary").status_code == 401


def test_no_habits_returns_empty_list(client):
    assert client.get("/summary", headers=USER_A).json() == []


def test_only_own_active_habits_are_reported(client):
    seed(user_id=1)
    seed(user_id=2)
    assert len(client.get("/summary", headers=USER_A).json()) == 1
    assert len(client.get("/summary", headers=USER_B).json()) == 1


def test_inactive_habit_is_excluded(client):
    habit_id = seed(user_id=1)
    import models
    from db import SessionLocal

    db = SessionLocal()
    try:
        db.query(models.Habit).filter_by(id=habit_id).update(
            {"active": False}
        )
        db.commit()
    finally:
        db.close()
    assert client.get("/summary", headers=USER_A).json() == []


def test_fresh_habit_completed_today_is_100_percent(client):
    seed(user_id=1, created_days_ago=0, checkins=[(0, True, 7, 9)])
    item = client.get("/summary", headers=USER_A).json()[0]
    assert item["elapsed_days"] == 1
    assert item["completed"] == 1
    assert item["success_rate"] == 100.0
    assert item["missed_days"] == 0


def test_skipping_days_hurts_the_success_rate(client):
    """Days without any check-in are misses, not invisible gaps."""
    seed(user_id=1, created_days_ago=4, checkins=[(0, True, None, 9)])
    item = client.get("/summary", headers=USER_A).json()[0]
    assert item["elapsed_days"] == 5
    assert item["success_rate"] == 20.0
    assert item["missed_days"] == 4


def test_explicit_undo_counts_as_a_miss(client):
    seed(
        user_id=1,
        created_days_ago=1,
        checkins=[(1, True, None, 9), (0, False, None, 9)],
    )
    item = client.get("/summary", headers=USER_A).json()[0]
    assert item["missed_days"] == 1
    assert item["success_rate"] == 50.0


def test_recovery_measures_the_delay_before_bouncing_back(client):
    # Created 4 days ago, done on day-3, silent for 2 days, done today.
    seed(
        user_id=1,
        created_days_ago=4,
        checkins=[(3, True, None, 9), (0, True, None, 9)],
    )
    item = client.get("/summary", headers=USER_A).json()[0]
    # First break: 1 day back. Second break: 2 days back. Mean = 1.5
    assert item["avg_recovery_days"] == 1.5


def test_recovery_is_null_without_any_miss(client):
    seed(user_id=1, created_days_ago=0, checkins=[(0, True, None, 9)])
    item = client.get("/summary", headers=USER_A).json()[0]
    assert item["avg_recovery_days"] is None


def test_best_hour_is_converted_to_local_time(client):
    seed(user_id=1, created_days_ago=0, checkins=[(0, True, None, 9)])
    utc_item = client.get("/summary?tz_offset=0", headers=USER_A).json()[0]
    paris_item = client.get("/summary?tz_offset=120", headers=USER_A).json()[0]
    assert utc_item["best_hour"] == 9
    assert paris_item["best_hour"] == 11


def test_habit_strength_combines_consistency_and_automaticity(client):
    seed(user_id=1, created_days_ago=0, checkins=[(0, True, 8, 9)])
    item = client.get("/summary", headers=USER_A).json()[0]
    # (1.0 * 0.6 + 0.8 * 0.4) * 100
    assert item["habit_strength"] == 92.0


def test_tz_offset_is_validated(client):
    assert (
        client.get("/summary?tz_offset=5000", headers=USER_A).status_code
        == 422
    )
