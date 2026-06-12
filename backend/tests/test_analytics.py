# Test suites for analytics insights and leaderboard
# auth_headers fixture is provided by conftest.py — no local helper needed.
import datetime

def test_get_analytics_empty(client, auth_headers):
    response = client.get("/api/analytics", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_co2_kg"] == 0.0
    assert data["carbon_saved_kg"] == 0.0
    assert len(data["ai_coach_tips"]) == 1
    assert "Welcome to Carbifyio" in data["ai_coach_tips"][0]["message"]

def test_get_analytics_populated(client, auth_headers):
    # Log calculations: 10 kWh electricity, medium meat diet, some waste
    # 10 * 0.385 = 3.85 (energy)
    # diet medium_meat = 5.6
    # waste 2 kg, recycling 0 -> 2 * 0.45 = 0.9 (waste)
    # Total = 3.85 + 5.6 + 0.9 = 10.35
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
    # We find the food tip by category rather than relying on index position,
    # so inactivity tips inserted first don't cause a false failure.
    food_tips = [t for t in data["ai_coach_tips"] if t["category"] == "food"]
    assert len(food_tips) >= 1

def test_get_leaderboard(client, make_auth_headers):
    headers1 = make_auth_headers("warrior1")
    headers2 = make_auth_headers("warrior2")

    # warrior1 logs a habit (walk_instead_of_drive) -> +20 points
    client.post(
        "/api/habits/log",
        json={"habit_name": "walk_instead_of_drive"},
        headers=headers1,
    )

    # Fetch leaderboard with warrior1
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
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["user_rank"] == 2
    assert data2["user_points"] == 0

def test_youden_threshold_unit(client, auth_headers):
    """
    Unit test for calculate_optimal_inactivity_threshold() in isolation.
    Seeds controlled gap data via habit logs across multiple users and verifies
    the function returns a plausible threshold (not just the default 5).
    With < 3 users the function must return the default threshold.
    """
    from backend.app.routes.analytics import calculate_optimal_inactivity_threshold
    from backend.app.database import get_db
    from backend.app import models
    import datetime

    db = next(client.app.dependency_overrides[get_db]())

    # Clear any cached threshold to ensure query executes
    db.query(models.CacheEntry).filter(models.CacheEntry.key == "youden_threshold").delete()
    db.commit()

    # Create 2 more users to ensure user_count >= 3
    user2 = models.User(username="testuser2", email="u2@test.com", hashed_password="pwd")
    user3 = models.User(username="testuser3", email="u3@test.com", hashed_password="pwd")
    db.add_all([user2, user3])
    db.commit()

    # Get the existing fixture user
    user1 = db.query(models.User).first()

    base_date = datetime.date(2023, 1, 1)

    # Seed gaps for User 1: 8 days and 9 days
    db.add(models.HabitsLog(user_id=user1.id, habit_type="energy", habit_name="test", logged_date=base_date))
    db.add(models.HabitsLog(user_id=user1.id, habit_type="energy", habit_name="test", logged_date=base_date + datetime.timedelta(days=8)))
    db.add(models.HabitsLog(user_id=user1.id, habit_type="energy", habit_name="test", logged_date=base_date + datetime.timedelta(days=17)))

    # Seed gaps for User 2: 3 days and 4 days
    db.add(models.HabitsLog(user_id=user2.id, habit_type="energy", habit_name="test", logged_date=base_date))
    db.add(models.HabitsLog(user_id=user2.id, habit_type="energy", habit_name="test", logged_date=base_date + datetime.timedelta(days=3)))
    db.add(models.HabitsLog(user_id=user2.id, habit_type="energy", habit_name="test", logged_date=base_date + datetime.timedelta(days=7)))

    # Seed gaps for User 3: 5 days and 10 days
    db.add(models.HabitsLog(user_id=user3.id, habit_type="energy", habit_name="test", logged_date=base_date))
    db.add(models.HabitsLog(user_id=user3.id, habit_type="energy", habit_name="test", logged_date=base_date + datetime.timedelta(days=5)))
    db.add(models.HabitsLog(user_id=user3.id, habit_type="energy", habit_name="test", logged_date=base_date + datetime.timedelta(days=15)))

    db.commit()

    result = calculate_optimal_inactivity_threshold(db)
    
    # We seeded gaps [8, 9, 3, 4, 5, 10].
    # True Inactives (>7): 8, 9, 10
    # True Actives (<=7): 3, 4, 5
    # Threshold 8 provides perfect separation (TPR=1.0, TNR=1.0, J=1.0).
    assert result == 8


def test_analytics_unauthenticated(client):
    """Accessing analytics without a token must return 401."""
    response = client.get("/api/analytics")
    assert response.status_code == 401
