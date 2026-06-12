# Test suites for challenges tracking, enrollment, and reward mechanisms
# auth_headers fixture is provided by conftest.py — no local helper needed.

def test_list_challenges(client, auth_headers):
    response = client.get("/api/challenges/list", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 5
    assert data[0]["title"] == "Eco Commuter"
    assert data[0]["points_reward"] == 50

def test_join_challenge_success(client, auth_headers):
    # First, list challenges to find ID
    list_resp = client.get("/api/challenges/list", headers=auth_headers)
    challenge_id = list_resp.json()[0]["id"]
    
    # Join challenge
    join_resp = client.post(f"/api/challenges/{challenge_id}/join", headers=auth_headers)
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

def test_join_challenge_duplicate_error(client, auth_headers):
    list_resp = client.get("/api/challenges/list", headers=auth_headers)
    challenge_id = list_resp.json()[0]["id"]
    
    # Join first time
    client.post(f"/api/challenges/{challenge_id}/join", headers=auth_headers)
    # Join second time -> should raise error
    duplicate_resp = client.post(f"/api/challenges/{challenge_id}/join", headers=auth_headers)
    assert duplicate_resp.status_code == 400
    assert "already joined" in duplicate_resp.json()["detail"]

def test_complete_challenge_success(client, auth_headers):
    list_resp = client.get("/api/challenges/list", headers=auth_headers)
    challenge = list_resp.json()[0]  # Eco Commuter (+50 points)
    challenge_id = challenge["id"]
    
    # Join challenge
    client.post(f"/api/challenges/{challenge_id}/join", headers=auth_headers)
    
    # Complete challenge
    complete_resp = client.post(f"/api/challenges/{challenge_id}/complete", headers=auth_headers)
    assert complete_resp.status_code == 200
    data = complete_resp.json()
    assert data["status"] == "completed"
    assert data["completed_date"] is not None
    
    # Check user points updated
    me_resp = client.get("/api/auth/me", headers=auth_headers)
    assert me_resp.json()["points"] == 50
    assert me_resp.json()["level"] == 1

    # Join and complete another two to hit level 2 (50+30+40=120 → level 2)
    challenge2_id = list_resp.json()[1]["id"]  # Unplugged Weekend (+30) -> total 80
    challenge3_id = list_resp.json()[2]["id"]  # Plant Power (+40) -> total 120
    
    client.post(f"/api/challenges/{challenge2_id}/join", headers=auth_headers)
    client.post(f"/api/challenges/{challenge2_id}/complete", headers=auth_headers)
    
    client.post(f"/api/challenges/{challenge3_id}/join", headers=auth_headers)
    client.post(f"/api/challenges/{challenge3_id}/complete", headers=auth_headers)
    
    me_resp2 = client.get("/api/auth/me", headers=auth_headers)
    assert me_resp2.json()["points"] == 120
    assert me_resp2.json()["level"] == 2  # 120 points leads to level 2

def test_complete_challenge_not_joined_error(client, auth_headers):
    list_resp = client.get("/api/challenges/list", headers=auth_headers)
    challenge_id = list_resp.json()[0]["id"]
    
    # Complete without joining -> should return 404
    complete_resp = client.post(f"/api/challenges/{challenge_id}/complete", headers=auth_headers)
    assert complete_resp.status_code == 404
    assert "haven't joined" in complete_resp.json()["detail"]

def test_complete_challenge_duplicate_error(client, auth_headers):
    list_resp = client.get("/api/challenges/list", headers=auth_headers)
    challenge_id = list_resp.json()[0]["id"]
    
    # Join and complete
    client.post(f"/api/challenges/{challenge_id}/join", headers=auth_headers)
    client.post(f"/api/challenges/{challenge_id}/complete", headers=auth_headers)
    
    # Complete again -> should return 400
    complete_resp = client.post(f"/api/challenges/{challenge_id}/complete", headers=auth_headers)
    assert complete_resp.status_code == 400
    assert "already completed" in complete_resp.json()["detail"]

def test_challenges_unauthenticated(client):
    """Accessing challenge list without a token must return 401."""
    response = client.get("/api/challenges/list")
    assert response.status_code == 401


def test_join_non_existent_challenge(client, auth_headers):
    # Non-existent challenge ID should return 404
    response = client.post("/api/challenges/9999/join", headers=auth_headers)
    assert response.status_code == 404
    assert "Challenge not found" in response.json()["detail"]


def test_reactivate_abandoned_challenge(client, auth_headers, db):
    # Retrieve challenge ID
    list_resp = client.get("/api/challenges/list", headers=auth_headers)
    challenge_id = list_resp.json()[0]["id"]

    # Join challenge (creates active challenge)
    client.post(f"/api/challenges/{challenge_id}/join", headers=auth_headers)

    # Manually mark the challenge as abandoned in the DB
    from backend.app import models
    uc = db.query(models.UserChallenge).filter(
        models.UserChallenge.challenge_id == challenge_id
    ).first()
    uc.status = "abandoned"
    db.commit()

    # Re-join the challenge (should reactivate it)
    reactivate_resp = client.post(f"/api/challenges/{challenge_id}/join", headers=auth_headers)
    assert reactivate_resp.status_code == 200
    assert reactivate_resp.json()["status"] == "active"


def test_list_challenges_pagination(client, auth_headers):
    # Retrieve page 1 with limit 2
    resp_page_1 = client.get("/api/challenges/list?page=1&limit=2", headers=auth_headers)
    assert resp_page_1.status_code == 200
    data_page_1 = resp_page_1.json()
    assert len(data_page_1) == 2

    # Retrieve page 2 with limit 2
    resp_page_2 = client.get("/api/challenges/list?page=2&limit=2", headers=auth_headers)
    assert resp_page_2.status_code == 200
    data_page_2 = resp_page_2.json()
    assert len(data_page_2) == 2

    # Verify elements are different
    titles_page_1 = {c["title"] for c in data_page_1}
    titles_page_2 = {c["title"] for c in data_page_2}
    assert len(titles_page_1.intersection(titles_page_2)) == 0

