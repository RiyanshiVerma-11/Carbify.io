# Test suites for user authentication
# No local get_auth_headers() — uses auth_headers fixture from conftest.py where needed.

def test_register_user(client):
    response = client.post(
        "/api/auth/register",
        json={"username": "testuser", "email": "test@example.com", "password": "password123"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"
    assert "id" in data
    assert "hashed_password" not in data

def test_register_duplicate_username(client):
    client.post(
        "/api/auth/register",
        json={"username": "testuser", "email": "test@example.com", "password": "password123"}
    )
    response = client.post(
        "/api/auth/register",
        json={"username": "testuser", "email": "test2@example.com", "password": "password123"}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Username already registered"

def test_login_success(client):
    client.post(
        "/api/auth/register",
        json={"username": "testuser", "email": "test@example.com", "password": "password123"}
    )
    response = client.post(
        "/api/auth/login",
        data={"username": "testuser", "password": "password123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == "testuser"

def test_login_invalid_credentials(client):
    client.post(
        "/api/auth/register",
        json={"username": "testuser", "email": "test@example.com", "password": "password123"}
    )
    response = client.post(
        "/api/auth/login",
        data={"username": "testuser", "password": "wrongpassword"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"

def test_get_me(client, auth_headers):
    """Uses the shared auth_headers fixture from conftest.py."""
    response = client.get("/api/auth/me", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["username"] == "fixture_user"

def test_get_me_unauthenticated(client):
    """Accessing /me without a token must return 401."""
    response = client.get("/api/auth/me")
    assert response.status_code == 401
