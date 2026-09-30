from conftest import USER_A, USER_B, valid_habit


def test_requires_authentication(client):
    assert client.get("/").status_code == 401
    assert client.post("/", json=valid_habit()).status_code == 401
    assert client.put("/1", json={"name": "x"}).status_code == 401
    assert client.delete("/1").status_code == 401


def test_create_returns_generated_if_then(client):
    resp = client.post("/", json=valid_habit(), headers=USER_A)
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] > 0
    assert body["if_then"] == (
        "After I apres mon cafe, I will boire un verre d'eau, "
        "then I will sourire."
    )


def test_list_returns_only_own_active_habits(client):
    client.post("/", json=valid_habit(), headers=USER_A)
    client.post("/", json=valid_habit(name="Autre"), headers=USER_B)

    mine = client.get("/", headers=USER_A).json()
    assert len(mine) == 1
    assert mine[0]["name"] == "Boire un verre"

    # Soft delete removes it from the active list.
    habit_id = mine[0]["id"]
    assert (
        client.delete(f"/{habit_id}", headers=USER_A).status_code == 200
    )
    assert client.get("/", headers=USER_A).json() == []


def test_blank_fields_are_rejected(client):
    resp = client.post(
        "/", json=valid_habit(anchor="   "), headers=USER_A
    )
    assert resp.status_code == 422


def test_missing_field_is_422_not_500(client):
    resp = client.post("/", json={"name": "x"}, headers=USER_A)
    assert resp.status_code == 422


def test_invalid_cue_time_is_rejected(client):
    resp = client.post(
        "/", json=valid_habit(cue_time="25:99"), headers=USER_A
    )
    assert resp.status_code == 422
    resp = client.post(
        "/", json=valid_habit(cue_time="8h30"), headers=USER_A
    )
    assert resp.status_code == 422


def test_delete_someone_elses_habit_is_404(client):
    created = client.post("/", json=valid_habit(), headers=USER_B).json()
    resp = client.delete(f"/{created['id']}", headers=USER_A)
    assert resp.status_code == 404
    # Victim still sees their habit.
    assert len(client.get("/", headers=USER_B).json()) == 1


def test_delete_twice_is_404(client):
    created = client.post("/", json=valid_habit(), headers=USER_A).json()
    assert (
        client.delete(f"/{created['id']}", headers=USER_A).status_code == 200
    )
    assert (
        client.delete(f"/{created['id']}", headers=USER_A).status_code == 404
    )


def test_update_changes_fields_and_regenerates_if_then(client):
    created = client.post("/", json=valid_habit(), headers=USER_A).json()

    resp = client.put(
        f"/{created['id']}",
        json={"anchor": "apres mon jogging", "celebration": "high five"},
        headers=USER_A,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["anchor"] == "apres mon jogging"
    assert body["celebration"] == "high five"
    # untouched fields survive
    assert body["name"] == "Boire un verre"
    assert body["tiny_behavior"] == "boire un verre d'eau"
    # the implementation intention follows the recipe
    assert body["if_then"] == (
        "After I apres mon jogging, I will boire un verre d'eau, "
        "then I will high five."
    )


def test_update_single_field_keeps_the_rest(client):
    created = client.post("/", json=valid_habit(), headers=USER_A).json()

    resp = client.put(f"/{created['id']}", json={"cue_time": "07:15"},
                      headers=USER_A)
    assert resp.status_code == 200
    body = resp.json()
    assert body["cue_time"] == "07:15"
    assert body["if_then"] == created["if_then"]
    assert body["name"] == created["name"]


def test_update_someone_elses_habit_is_404(client):
    created = client.post("/", json=valid_habit(), headers=USER_B).json()
    resp = client.put(f"/{created['id']}", json={"name": "Hacked"},
                      headers=USER_A)
    assert resp.status_code == 404
    # Victim's habit is untouched.
    mine = client.get("/", headers=USER_B).json()
    assert mine[0]["name"] == "Boire un verre"


def test_update_of_deleted_habit_is_404(client):
    created = client.post("/", json=valid_habit(), headers=USER_A).json()
    client.delete(f"/{created['id']}", headers=USER_A)
    resp = client.put(f"/{created['id']}", json={"name": "Back"},
                      headers=USER_A)
    assert resp.status_code == 404


def test_update_unknown_habit_is_404(client):
    assert client.put("/9999", json={"name": "x"}, headers=USER_A).status_code == 404


def test_update_validation(client):
    created = client.post("/", json=valid_habit(), headers=USER_A).json()
    habit_id = created["id"]

    # Bad cue time -> 422, not a broken row.
    assert (
        client.put(
            f"/{habit_id}", json={"cue_time": "99:99"}, headers=USER_A
        ).status_code
        == 422
    )
    # Blank / null name -> 422.
    assert (
        client.put(f"/{habit_id}", json={"name": "   "}, headers=USER_A).status_code
        == 422
    )
    assert (
        client.put(f"/{habit_id}", json={"name": None}, headers=USER_A).status_code
        == 422
    )
    # Empty payload -> 422 (nothing to update).
    assert client.put(f"/{habit_id}", json={}, headers=USER_A).status_code == 422

    # Nothing was applied by the failed calls.
    after = client.get("/", headers=USER_A).json()[0]
    assert after == created
