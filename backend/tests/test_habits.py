# Test suites for green habits logging
# auth_headers fixture is provided by conftest.py — no local helper needed.

def test_list_habits(client):
    response = client.get("/api/habits/list")
    assert response.status_code == 200
    data = response.json()
    assert "walk_instead_of_drive" in data
    assert data["walk_instead_of_drive"]["points"] == 20

def test_log_habit_rewards(client, auth_headers):
    # Log a habit: walk_instead_of_drive has +20 points
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

def test_log_habit_level_up(client, auth_headers):
    # plant_based_day gives +25 points. Log it 4 times to hit 100 points
    # Need to simulate different dates to bypass single-log-per-day limit
    import datetime
    
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
    assert profile_resp.json()["level"] == 2  # 100 points leads to level 2

def test_log_duplicate_habit_error(client, auth_headers):
    # Log once
    client.post(
        "/api/habits/log",
        json={"habit_name": "walk_instead_of_drive"},
        headers=auth_headers,
    )
    # Log twice on same day -> should fail
    response = client.post(
        "/api/habits/log",
        json={"habit_name": "walk_instead_of_drive"},
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "already logged" in response.json()["detail"]

def test_log_habit_unauthenticated(client):
    """Accessing habit log endpoint without a token must return 401."""
    response = client.post("/api/habits/log", json={"habit_name": "walk_instead_of_drive"})
    assert response.status_code == 401


def test_log_habit_unknown_key(client, auth_headers):
    # Unknown habit key should return 400
    response = client.post(
        "/api/habits/log",
        json={"habit_name": "unknown_habit_key_xyz"},
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "Unknown habit key" in response.json()["detail"]


def test_get_habit_history_pagination(client, auth_headers):
    # Log two distinct habits on different days to bypass duplicate guard
    import datetime
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

