"""
backend/tests/test_challenges.py
─────────────────────────────────────────────────────────────
Test suites for eco-challenges — enrolment, completion, reward
mechanisms, abandon/re-activate flow, and pagination.

``auth_headers`` fixture is provided by conftest.py — no local helper needed.
"""

from __future__ import annotations


def test_list_challenges(client, auth_headers) -> None:
    """Challenge catalogue should contain at least 5 seeded challenges."""
    response = client.get("/api/challenges/list", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 5
    assert data[0]["title"] == "Eco Commuter"
    assert data[0]["points_reward"] == 50


def test_list_challenges_structure(client, auth_headers) -> None:
    """Each challenge should have required fields: title, description, points_reward, category."""
    response = client.get("/api/challenges/list", headers=auth_headers)
    for challenge in response.json():
        assert "title" in challenge
        assert "description" in challenge
        assert "points_reward" in challenge
        assert "category" in challenge
        assert "duration_days" in challenge


def test_join_challenge_success(client, auth_headers) -> None:
    """Successfully joining a challenge should return an active enrolment."""
    list_resp = client.get("/api/challenges/list", headers=auth_headers)
    challenge_id = list_resp.json()[0]["id"]

    join_resp = client.post(
        f"/api/challenges/{challenge_id}/join", headers=auth_headers
    )
    assert join_resp.status_code == 200
    data = join_resp.json()
    assert data["challenge_id"] == challenge_id
    assert data["status"] == "active"

    # Fetch user challenges list
    user_challenges_resp = client.get("/api/challenges/user", headers=auth_headers)
    assert user_challenges_resp.status_code == 200
    user_challenges_data = user_challenges_resp.json()
    assert len(user_challenges_data) == 1
    assert user_challenges_data[0]["challenge_id"] == challenge_id


def test_join_challenge_duplicate_error(client, auth_headers) -> None:
    """Joining an already-active challenge should return 400."""
    list_resp = client.get("/api/challenges/list", headers=auth_headers)
    challenge_id = list_resp.json()[0]["id"]

    client.post(f"/api/challenges/{challenge_id}/join", headers=auth_headers)
    duplicate_resp = client.post(
        f"/api/challenges/{challenge_id}/join", headers=auth_headers
    )
    assert duplicate_resp.status_code == 400
    assert "already joined" in duplicate_resp.json()["detail"]


def test_complete_challenge_success(client, auth_headers) -> None:
    """Completing a challenge should award points and update the user level."""
    list_resp = client.get("/api/challenges/list", headers=auth_headers)
    challenge = list_resp.json()[0]  # Eco Commuter (+50 points)
    challenge_id = challenge["id"]

    client.post(f"/api/challenges/{challenge_id}/join", headers=auth_headers)
    complete_resp = client.post(
        f"/api/challenges/{challenge_id}/complete", headers=auth_headers
    )
    assert complete_resp.status_code == 200
    data = complete_resp.json()
    assert data["status"] == "completed"
    assert data["completed_date"] is not None

    # Check user points updated
    me_resp = client.get("/api/auth/me", headers=auth_headers)
    assert me_resp.json()["points"] == 50
    assert me_resp.json()["level"] == 1

    # Join and complete more challenges to trigger level 2 (50+30+40=120)
    challenge2_id = list_resp.json()[1]["id"]
    challenge3_id = list_resp.json()[2]["id"]

    client.post(f"/api/challenges/{challenge2_id}/join", headers=auth_headers)
    client.post(f"/api/challenges/{challenge2_id}/complete", headers=auth_headers)

    client.post(f"/api/challenges/{challenge3_id}/join", headers=auth_headers)
    client.post(f"/api/challenges/{challenge3_id}/complete", headers=auth_headers)

    me_resp2 = client.get("/api/auth/me", headers=auth_headers)
    assert me_resp2.json()["points"] == 120
    assert me_resp2.json()["level"] == 2


def test_complete_challenge_not_joined_error(client, auth_headers) -> None:
    """Completing a challenge without joining first should return 404."""
    list_resp = client.get("/api/challenges/list", headers=auth_headers)
    challenge_id = list_resp.json()[0]["id"]

    complete_resp = client.post(
        f"/api/challenges/{challenge_id}/complete", headers=auth_headers
    )
    assert complete_resp.status_code == 404
    assert "haven't joined" in complete_resp.json()["detail"]


def test_complete_challenge_duplicate_error(client, auth_headers) -> None:
    """Completing an already-completed challenge should return 400."""
    list_resp = client.get("/api/challenges/list", headers=auth_headers)
    challenge_id = list_resp.json()[0]["id"]

    client.post(f"/api/challenges/{challenge_id}/join", headers=auth_headers)
    client.post(f"/api/challenges/{challenge_id}/complete", headers=auth_headers)

    complete_resp = client.post(
        f"/api/challenges/{challenge_id}/complete", headers=auth_headers
    )
    assert complete_resp.status_code == 400
    assert "already completed" in complete_resp.json()["detail"]


def test_rejoin_completed_challenge_error(client, auth_headers) -> None:
    """Trying to re-join a completed challenge should return 400."""
    list_resp = client.get("/api/challenges/list", headers=auth_headers)
    challenge_id = list_resp.json()[0]["id"]

    client.post(f"/api/challenges/{challenge_id}/join", headers=auth_headers)
    client.post(f"/api/challenges/{challenge_id}/complete", headers=auth_headers)

    rejoin_resp = client.post(
        f"/api/challenges/{challenge_id}/join", headers=auth_headers
    )
    assert rejoin_resp.status_code == 400
    assert "already completed" in rejoin_resp.json()["detail"]


def test_challenges_unauthenticated(client) -> None:
    """Accessing challenge list without a token must return 401."""
    response = client.get("/api/challenges/list")
    assert response.status_code == 401


def test_join_non_existent_challenge(client, auth_headers) -> None:
    """Joining a non-existent challenge ID should return 404."""
    response = client.post("/api/challenges/9999/join", headers=auth_headers)
    assert response.status_code == 404
    assert "Challenge not found" in response.json()["detail"]


def test_reactivate_abandoned_challenge(client, auth_headers, db) -> None:
    """An abandoned challenge should be re-activatable via the join endpoint."""
    list_resp = client.get("/api/challenges/list", headers=auth_headers)
    challenge_id = list_resp.json()[0]["id"]

    client.post(f"/api/challenges/{challenge_id}/join", headers=auth_headers)

    # Manually mark the challenge as abandoned in the DB
    from backend.app import models

    uc = (
        db.query(models.UserChallenge)
        .filter(models.UserChallenge.challenge_id == challenge_id)
        .first()
    )
    uc.status = "abandoned"
    db.commit()

    # Re-join the challenge (should reactivate it)
    reactivate_resp = client.post(
        f"/api/challenges/{challenge_id}/join", headers=auth_headers
    )
    assert reactivate_resp.status_code == 200
    assert reactivate_resp.json()["status"] == "active"


def test_list_challenges_pagination(client, auth_headers) -> None:
    """Challenge list should support page/limit pagination with no overlapping results."""
    resp_page_1 = client.get(
        "/api/challenges/list?page=1&limit=2", headers=auth_headers
    )
    assert resp_page_1.status_code == 200
    data_page_1 = resp_page_1.json()
    assert len(data_page_1) == 2

    resp_page_2 = client.get(
        "/api/challenges/list?page=2&limit=2", headers=auth_headers
    )
    assert resp_page_2.status_code == 200
    data_page_2 = resp_page_2.json()
    assert len(data_page_2) == 2

    # Verify elements are different
    titles_page_1 = {c["title"] for c in data_page_1}
    titles_page_2 = {c["title"] for c in data_page_2}
    assert len(titles_page_1.intersection(titles_page_2)) == 0


def test_user_challenges_unauthenticated(client) -> None:
    """Accessing user challenges without a token must return 401."""
    response = client.get("/api/challenges/user")
    assert response.status_code == 401
