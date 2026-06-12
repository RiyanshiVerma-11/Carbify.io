"""
backend/tests/test_analytics.py
─────────────────────────────────────────────────────────────
Test suites for analytics insights, AI Coach tips, leaderboard,
and Youden's J-statistic threshold optimiser.

``auth_headers`` fixture is provided by conftest.py — no local helper needed.
"""

from __future__ import annotations

import datetime


def test_get_analytics_empty(client, auth_headers) -> None:
    """Before logging any data, analytics should return zeroed values and a welcome tip."""
    response = client.get("/api/analytics", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_co2_kg"] == 0.0
    assert data["carbon_saved_kg"] == 0.0
    assert len(data["ai_coach_tips"]) == 1
    assert "Welcome to Carbifyio" in data["ai_coach_tips"][0]["message"]


def test_get_analytics_populated(client, auth_headers) -> None:
    """After logging emissions, analytics should reflect accurate breakdown and tips."""
    client.post(
        "/api/calculator/log",
        json={
            "electricity_kwh": 10.0,
            "diet_type": "medium_meat",
            "waste_kg": 2.0,
        },
        headers=auth_headers,
    )

    response = client.get("/api/analytics", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_co2_kg"] == 10.35
    assert data["weekly_breakdown"]["energy"] == 3.85
    assert data["weekly_breakdown"]["food"] == 5.6
    assert data["weekly_breakdown"]["waste"] == 0.9

    # Food should be the highest source, triggering a diet recommendation tip.
    food_tips = [t for t in data["ai_coach_tips"] if t["category"] == "food"]
    assert len(food_tips) >= 1


def test_get_analytics_transport_dominant(client, auth_headers) -> None:
    """When transport is the dominant emission source, a transport tip should appear."""
    client.post(
        "/api/calculator/log",
        json={
            "petrol_car_km": 100.0,
            "diet_type": "vegan",  # Low food emissions
        },
        headers=auth_headers,
    )

    response = client.get("/api/analytics", headers=auth_headers)
    data = response.json()

    transport_tips = [t for t in data["ai_coach_tips"] if t["category"] == "transport"]
    assert len(transport_tips) >= 1


def test_get_analytics_energy_dominant(client, auth_headers) -> None:
    """When energy is the dominant emission source, an energy tip should appear."""
    client.post(
        "/api/calculator/log",
        json={
            "electricity_kwh": 50.0,
            "gas_kwh": 30.0,
            "diet_type": "vegan",
        },
        headers=auth_headers,
    )

    response = client.get("/api/analytics", headers=auth_headers)
    data = response.json()

    energy_tips = [t for t in data["ai_coach_tips"] if t["category"] == "energy"]
    assert len(energy_tips) >= 1


def test_get_analytics_carbon_saved_reflects_habits(client, auth_headers) -> None:
    """carbon_saved_kg should reflect the total CO₂ saved from logged habits."""
    client.post(
        "/api/habits/log",
        json={"habit_name": "walk_instead_of_drive"},
        headers=auth_headers,
    )

    response = client.get("/api/analytics", headers=auth_headers)
    data = response.json()
    assert data["carbon_saved_kg"] == 1.5


def test_get_leaderboard(client, make_auth_headers) -> None:
    """Leaderboard should rank users by points, highest first."""
    headers1 = make_auth_headers("warrior1")
    headers2 = make_auth_headers("warrior2")

    # warrior1 logs a habit → +20 points
    client.post(
        "/api/habits/log",
        json={"habit_name": "walk_instead_of_drive"},
        headers=headers1,
    )

    response = client.get("/api/analytics/leaderboard", headers=headers1)
    assert response.status_code == 200
    data = response.json()

    assert data["user_rank"] == 1
    assert data["user_points"] == 20
    assert len(data["leaderboard"]) >= 2
    assert data["leaderboard"][0]["username"] == "warrior1"
    assert data["leaderboard"][0]["points"] == 20

    # warrior2 (0 points) should be rank 2
    response2 = client.get("/api/analytics/leaderboard", headers=headers2)
    data2 = response2.json()
    assert data2["user_rank"] == 2
    assert data2["user_points"] == 0


def test_leaderboard_structure(client, auth_headers) -> None:
    """Each leaderboard entry should contain username, points, and level."""
    response = client.get("/api/analytics/leaderboard", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "user_rank" in data
    assert "user_points" in data
    assert "leaderboard" in data
    for entry in data["leaderboard"]:
        assert "username" in entry
        assert "points" in entry
        assert "level" in entry


def test_youden_threshold_unit(client, auth_headers) -> None:
    """Youden's J-statistic should return optimal threshold=8 for seeded gap data.

    We create controlled gap data across 3 users:
    - Gaps [8, 9] for user 1
    - Gaps [3, 4] for user 2
    - Gaps [5, 10] for user 3

    True Inactives (>7): 8, 9, 10
    True Actives (<=7): 3, 4, 5
    Threshold 6 provides perfect separation (J=1.0).
    """
    from backend.app import models
    from backend.app.database import get_db
    from backend.app.routes.analytics import calculate_optimal_inactivity_threshold

    db = next(client.app.dependency_overrides[get_db]())

    # Clear any cached threshold
    db.query(models.CacheEntry).filter(models.CacheEntry.key == "youden_threshold").delete()
    db.commit()

    # Create 2 more users to ensure user_count >= 3
    user2 = models.User(username="testuser2", email="u2@test.com", hashed_password="pwd")
    user3 = models.User(username="testuser3", email="u3@test.com", hashed_password="pwd")
    db.add_all([user2, user3])
    db.commit()

    user1 = db.query(models.User).first()
    base_date = datetime.date(2023, 1, 1)

    # Seed gaps for User 1: 8 days and 9 days
    db.add(
        models.HabitsLog(
            user_id=user1.id,
            habit_type="energy",
            habit_name="test",
            logged_date=base_date,
        )
    )
    db.add(
        models.HabitsLog(
            user_id=user1.id,
            habit_type="energy",
            habit_name="test",
            logged_date=base_date + datetime.timedelta(days=8),
        )
    )
    db.add(
        models.HabitsLog(
            user_id=user1.id,
            habit_type="energy",
            habit_name="test",
            logged_date=base_date + datetime.timedelta(days=17),
        )
    )

    # Seed gaps for User 2: 3 days and 4 days
    db.add(
        models.HabitsLog(
            user_id=user2.id,
            habit_type="energy",
            habit_name="test",
            logged_date=base_date,
        )
    )
    db.add(
        models.HabitsLog(
            user_id=user2.id,
            habit_type="energy",
            habit_name="test",
            logged_date=base_date + datetime.timedelta(days=3),
        )
    )
    db.add(
        models.HabitsLog(
            user_id=user2.id,
            habit_type="energy",
            habit_name="test",
            logged_date=base_date + datetime.timedelta(days=7),
        )
    )

    # Seed gaps for User 3: 5 days and 10 days
    db.add(
        models.HabitsLog(
            user_id=user3.id,
            habit_type="energy",
            habit_name="test",
            logged_date=base_date,
        )
    )
    db.add(
        models.HabitsLog(
            user_id=user3.id,
            habit_type="energy",
            habit_name="test",
            logged_date=base_date + datetime.timedelta(days=5),
        )
    )
    db.add(
        models.HabitsLog(
            user_id=user3.id,
            habit_type="energy",
            habit_name="test",
            logged_date=base_date + datetime.timedelta(days=15),
        )
    )

    db.commit()

    result = calculate_optimal_inactivity_threshold(db)
    # The gaps are 3, 4, 5 (active) and 8, 9, 10 (inactive).
    # t=6 is the first threshold (from 2 to 10) to perfectly separate them (J=1.0).
    assert result == 6


def test_analytics_unauthenticated(client) -> None:
    """Accessing analytics without a token must return 401."""
    response = client.get("/api/analytics")
    assert response.status_code == 401


def test_leaderboard_unauthenticated(client) -> None:
    """Accessing leaderboard without a token must return 401."""
    response = client.get("/api/analytics/leaderboard")
    assert response.status_code == 401
