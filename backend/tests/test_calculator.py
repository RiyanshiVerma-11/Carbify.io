# Test suites for emissions calculations
# auth_headers fixture is provided by conftest.py — no local helper needed.

def test_log_emissions(client, auth_headers):
    payload = {
        "electricity_kwh": 10.0,   # 10 * 0.385 = 3.85
        "gas_kwh": 5.0,            # 5 * 0.185 = 0.925
        "petrol_car_km": 20.0,     # 20 * 0.17 = 3.4
        "diet_type": "vegetarian",  # 3.8
        "waste_kg": 2.0,           # 2 * 0.45 = 0.9
        "recycling_rate": 0.5      # waste_co2 * 0.5 = 0.45
    }
    # Expected: 3.85 + 0.925 + 3.4 + 3.8 + 0.45 = 12.43
    response = client.post("/api/calculator/log", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["electricity_kwh"] == 10.0
    assert data["total_co2_kg"] == 12.43

def test_log_history(client, auth_headers):
    # Log once
    client.post("/api/calculator/log", json={"electricity_kwh": 10.0}, headers=auth_headers)
    
    # Fetch history
    history_resp = client.get("/api/calculator/history", headers=auth_headers)
    assert history_resp.status_code == 200
    assert len(history_resp.json()) == 1
    assert history_resp.json()[0]["electricity_kwh"] == 10.0

def test_get_latest_default(client, auth_headers):
    # Fetch latest before logging
    response = client.get("/api/calculator/latest", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["total_co2_kg"] == 0.0

def test_log_emissions_negative_boundary(client, auth_headers):
    # Negative electricity_kwh must fail Pydantic ge=0.0 → 422
    payload = {"electricity_kwh": -10.0}
    response = client.post("/api/calculator/log", json=payload, headers=auth_headers)
    assert response.status_code == 422

def test_log_emissions_recycling_rate_boundaries(client, auth_headers):
    # recycling_rate > 1.0 must fail Pydantic le=1.0 → 422
    response_high = client.post(
        "/api/calculator/log", json={"recycling_rate": 1.5}, headers=auth_headers
    )
    assert response_high.status_code == 422

    # recycling_rate < 0.0 must fail Pydantic ge=0.0 → 422
    response_low = client.post(
        "/api/calculator/log", json={"recycling_rate": -0.1}, headers=auth_headers
    )
    assert response_low.status_code == 422

def test_log_emissions_string_input_invalid_type(client, auth_headers):
    """
    BVA: passing a non-numeric string for a float field must return 422.
    Ensures Pydantic coercion is strict — not silently falling back.
    """
    payload = {"electricity_kwh": "abc"}
    response = client.post("/api/calculator/log", json=payload, headers=auth_headers)
    assert response.status_code == 422

def test_log_emissions_invalid_diet_type(client, auth_headers):
    """
    Schema-level validation: diet_type is a Literal enum.
    Submitting an unknown string (e.g. 'omnivore') must return 422,
    not silently fall back to a vegetarian default.
    """
    payload = {"diet_type": "omnivore"}
    response = client.post("/api/calculator/log", json=payload, headers=auth_headers)
    assert response.status_code == 422

def test_get_constants(client, auth_headers):
    """Public constants endpoint should return emission factors."""
    response = client.get("/api/calculator/constants", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "electricity_kwh" in data
    assert "diet_factors" in data
    assert "waste_factor" in data

def test_protected_endpoint_without_token(client):
    """Accessing a protected endpoint without a token must return 401."""
    response = client.get("/api/calculator/history")
    assert response.status_code == 401


def test_log_emissions_recycling_rate_exact_boundaries(client, auth_headers):
    # recycling_rate=0.0 must pass validation
    response_zero = client.post(
        "/api/calculator/log", json={"recycling_rate": 0.0}, headers=auth_headers
    )
    assert response_zero.status_code == 200
    assert response_zero.json()["recycling_rate"] == 0.0

    # recycling_rate=1.0 must pass validation
    response_one = client.post(
        "/api/calculator/log", json={"recycling_rate": 1.0}, headers=auth_headers
    )
    assert response_one.status_code == 200
    assert response_one.json()["recycling_rate"] == 1.0


def test_log_history_pagination(client, auth_headers):
    # Log twice
    client.post("/api/calculator/log", json={"electricity_kwh": 10.0, "logged_date": "2026-06-11"}, headers=auth_headers)
    client.post("/api/calculator/log", json={"electricity_kwh": 20.0, "logged_date": "2026-06-12"}, headers=auth_headers)

    # Fetch page 1 limit 1
    resp_page_1 = client.get("/api/calculator/history?page=1&limit=1", headers=auth_headers)
    assert resp_page_1.status_code == 200
    assert len(resp_page_1.json()) == 1
    assert resp_page_1.json()[0]["electricity_kwh"] == 20.0  # newest first

    # Fetch page 2 limit 1
    resp_page_2 = client.get("/api/calculator/history?page=2&limit=1", headers=auth_headers)
    assert resp_page_2.status_code == 200
    assert len(resp_page_2.json()) == 1
    assert resp_page_2.json()[0]["electricity_kwh"] == 10.0

