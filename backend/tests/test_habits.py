"""
backend/tests/test_habits.py
─────────────────────────────────────────────────────────────
Test suites for green habits logging, CRUD operations,
gamification (points/level-up), and pagination.

``auth_headers`` fixture is provided by conftest.py — no local helper needed.
"""

from __future__ import annotations

import datetime


def test_list_habits(client) -> None:
    """Unauthenticated habit catalogue listing should succeed and contain default habits."""
    response = client.get("/api/habits/list")
    assert response.status_code == 200
    data = response.json()
    assert "walk_instead_of_drive" in data
    assert data["walk_instead_of_drive"]["points"] == 20


def test_list_habits_contains_all_defaults(client) -> None:
    """All seven default habits should be present in the catalogue."""
    response = client.get("/api/habits/list")
    data = response.json()
    expected_slugs = {
        "walk_instead_of_drive",
        "turn_off_ac",
        "plant_based_day",
        "recycle_bottles",
        "short_shower",
        "air_dry_clothes",
        "unplug_idle",
    }
    assert expected_slugs.issubset(set(data.keys()))


def test_log_habit_rewards(client, auth_headers) -> None:
    """Logging a habit should award points and CO₂ savings to the user."""
    response = client.post(
        "/api/habits/log",
        json={"habit_name": "walk_instead_of_drive"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["habit_name"] == "walk_instead_of_drive"
    assert data["points_earned"] == 20
    assert data["co2_saved_kg"] == 1.5

    # Check user points and levels updated
    profile_resp = client.get("/api/auth/me", headers=auth_headers)
    assert profile_resp.json()["points"] == 20
    assert profile_resp.json()["level"] == 1


def test_log_habit_level_up(client, auth_headers) -> None:
    """Logging enough habits to reach 100 points should trigger level 2."""
    dates = [
        datetime.date.today(),
        datetime.date.today() - datetime.timedelta(days=1),
        datetime.date.today() - datetime.timedelta(days=2),
        datetime.date.today() - datetime.timedelta(days=3),
    ]

    for d in dates:
        client.post(
            "/api/habits/log",
            json={"habit_name": "plant_based_day", "logged_date": str(d)},
            headers=auth_headers,
        )

    profile_resp = client.get("/api/auth/me", headers=auth_headers)
    assert profile_resp.json()["points"] == 100
    assert profile_resp.json()["level"] == 2


def test_log_duplicate_habit_error(client, auth_headers) -> None:
    """Logging the same habit twice on the same day should return 400."""
    client.post(
        "/api/habits/log",
        json={"habit_name": "walk_instead_of_drive"},
        headers=auth_headers,
    )
    response = client.post(
        "/api/habits/log",
        json={"habit_name": "walk_instead_of_drive"},
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "already logged" in response.json()["detail"]


def test_log_habit_unauthenticated(client) -> None:
    """Accessing habit log endpoint without a token must return 401."""
    response = client.post(
        "/api/habits/log", json={"habit_name": "walk_instead_of_drive"}
    )
    assert response.status_code == 401


def test_log_habit_unknown_key(client, auth_headers) -> None:
    """An unknown habit slug should return 400 with a clear message."""
    response = client.post(
        "/api/habits/log",
        json={"habit_name": "unknown_habit_key_xyz"},
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "Unknown habit key" in response.json()["detail"]


def test_log_different_habits_same_day(client, auth_headers) -> None:
    """Different habits can be logged on the same day without conflict."""
    resp1 = client.post(
        "/api/habits/log",
        json={"habit_name": "walk_instead_of_drive"},
        headers=auth_headers,
    )
    assert resp1.status_code == 200

    resp2 = client.post(
        "/api/habits/log",
        json={"habit_name": "turn_off_ac"},
        headers=auth_headers,
    )
    assert resp2.status_code == 200


def test_get_habit_history_pagination(client, auth_headers) -> None:
    """Habit history should support page/limit pagination."""
    d1 = datetime.date.today()
    d2 = datetime.date.today() - datetime.timedelta(days=1)

    client.post(
        "/api/habits/log",
        json={"habit_name": "walk_instead_of_drive", "logged_date": str(d1)},
        headers=auth_headers,
    )
    client.post(
        "/api/habits/log",
        json={"habit_name": "turn_off_ac", "logged_date": str(d2)},
        headers=auth_headers,
    )

    # Fetch page 1 limit 1
    resp_page_1 = client.get("/api/habits/history?page=1&limit=1", headers=auth_headers)
    assert resp_page_1.status_code == 200
    assert len(resp_page_1.json()) == 1
    assert resp_page_1.json()[0]["habit_name"] == "walk_instead_of_drive"

    # Fetch page 2 limit 1
    resp_page_2 = client.get("/api/habits/history?page=2&limit=1", headers=auth_headers)
    assert resp_page_2.status_code == 200
    assert len(resp_page_2.json()) == 1
    assert resp_page_2.json()[0]["habit_name"] == "turn_off_ac"


def test_habit_crud_admin(client, auth_headers) -> None:
    """Full CRUD lifecycle for dynamic habit management."""
    # 1. Create a habit
    new_habit = {
        "slug": "compost_waste",
        "name": "Composted organic food waste",
        "category": "waste",
        "points": 15,
        "co2_saved": 0.6,
    }
    response = client.post("/api/habits/", json=new_habit, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["slug"] == "compost_waste"
    assert data["points"] == 15
    habit_id = data["id"]

    # 2. Duplicate slug should fail
    response_dup = client.post("/api/habits/", json=new_habit, headers=auth_headers)
    assert response_dup.status_code == 400

    # 3. Update the habit
    update_data = {
        "points": 18,
        "co2_saved": 0.7,
    }
    response_up = client.put(
        f"/api/habits/{habit_id}", json=update_data, headers=auth_headers
    )
    assert response_up.status_code == 200
    assert response_up.json()["points"] == 18
    assert response_up.json()["co2_saved"] == 0.7

    # 4. Delete the habit
    response_del = client.delete(f"/api/habits/{habit_id}", headers=auth_headers)
    assert response_del.status_code == 204

    # 5. Get list should not contain the deleted habit
    response_list = client.get("/api/habits/list")
    assert response_list.status_code == 200
    assert "compost_waste" not in response_list.json()


def test_update_nonexistent_habit(client, auth_headers) -> None:
    """Updating a habit that doesn't exist should return 404."""
    response = client.put(
        "/api/habits/99999",
        json={"points": 10},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_delete_nonexistent_habit(client, auth_headers) -> None:
    """Deleting a habit that doesn't exist should return 404."""
    response = client.delete("/api/habits/99999", headers=auth_headers)
    assert response.status_code == 404
