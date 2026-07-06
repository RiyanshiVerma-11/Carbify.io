"""
backend/tests/test_calculator.py
─────────────────────────────────────────────────────────────
Test suites for emissions calculator routes — logging, history,
latest-entry retrieval, boundary validation, and pagination.

``auth_headers`` fixture is provided by conftest.py — no local helper needed.
"""

from __future__ import annotations


def test_log_emissions(client, auth_headers) -> None:
    """Log emissions with known values and verify total CO₂ calculation accuracy."""
    payload = {
        "electricity_kwh": 10.0,  # 10 * 0.385 = 3.85
        "gas_kwh": 5.0,  # 5 * 0.185 = 0.925
        "petrol_car_km": 20.0,  # 20 * 0.17 = 3.4
        "diet_type": "vegetarian",  # 3.8
        "waste_kg": 2.0,  # 2 * 0.45 = 0.9
        "recycling_rate": 0.5,  # waste_co2 * 0.5 = 0.45
    }
    # Expected: 3.85 + 0.925 + 3.4 + 3.8 + 0.45 = 12.43
    response = client.post("/api/calculator/log", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["electricity_kwh"] == 10.0
    assert data["total_co2_kg"] == 12.43


def test_log_emissions_all_fields(client, auth_headers) -> None:
    """Exercise every input field simultaneously to ensure nothing is silently dropped."""
    payload = {
        "electricity_kwh": 8.0,
        "gas_kwh": 4.0,
        "petrol_car_km": 15.0,
        "diesel_car_km": 10.0,
        "electric_car_km": 20.0,
        "public_transit_km": 30.0,
        "flights_km": 50.0,
        "diet_type": "meat_heavy",
        "waste_kg": 3.0,
        "recycling_rate": 0.3,
    }
    response = client.post("/api/calculator/log", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_co2_kg"] > 0
    assert data["electricity_kwh"] == 8.0
    assert data["diesel_car_km"] == 10.0
    assert data["flights_km"] == 50.0
    assert data["diet_type"] == "meat_heavy"


def test_log_emissions_upsert_same_day(client, auth_headers) -> None:
    """Logging twice on the same day should update the existing row, not create a duplicate."""
    payload_v1 = {"electricity_kwh": 5.0}
    payload_v2 = {"electricity_kwh": 25.0}

    client.post("/api/calculator/log", json=payload_v1, headers=auth_headers)
    response = client.post("/api/calculator/log", json=payload_v2, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["electricity_kwh"] == 25.0

    # History should still have only one entry for today
    history = client.get("/api/calculator/history", headers=auth_headers)
    assert len(history.json()) == 1


def test_log_history(client, auth_headers) -> None:
    """After logging once, history should contain exactly one entry."""
    client.post("/api/calculator/log", json={"electricity_kwh": 10.0}, headers=auth_headers)

    history_resp = client.get("/api/calculator/history", headers=auth_headers)
    assert history_resp.status_code == 200
    assert len(history_resp.json()) == 1
    assert history_resp.json()[0]["electricity_kwh"] == 10.0


def test_get_latest_default(client, auth_headers) -> None:
    """Before any logs exist, /latest should return zeroed-out defaults."""
    response = client.get("/api/calculator/latest", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["total_co2_kg"] == 0.0


def test_log_emissions_negative_boundary(client, auth_headers) -> None:
    """Negative electricity_kwh must fail Pydantic ge=0.0 → 422."""
    payload = {"electricity_kwh": -10.0}
    response = client.post("/api/calculator/log", json=payload, headers=auth_headers)
    assert response.status_code == 422


def test_log_emissions_recycling_rate_boundaries(client, auth_headers) -> None:
    """Recycling rate outside [0.0, 1.0] must be rejected by Pydantic."""
    response_high = client.post(
        "/api/calculator/log",
        json={"recycling_rate": 1.5},
        headers=auth_headers,
    )
    assert response_high.status_code == 422

    response_low = client.post(
        "/api/calculator/log",
        json={"recycling_rate": -0.1},
        headers=auth_headers,
    )
    assert response_low.status_code == 422


def test_log_emissions_string_input_invalid_type(client, auth_headers) -> None:
    """Passing a non-numeric string for a float field must return 422."""
    payload = {"electricity_kwh": "abc"}
    response = client.post("/api/calculator/log", json=payload, headers=auth_headers)
    assert response.status_code == 422


def test_log_emissions_invalid_diet_type(client, auth_headers) -> None:
    """Unknown diet_type (not in Literal enum) must return 422."""
    payload = {"diet_type": "omnivore"}
    response = client.post("/api/calculator/log", json=payload, headers=auth_headers)
    assert response.status_code == 422


def test_get_constants(client, auth_headers) -> None:
    """Authenticated constants endpoint should return the emission factors dict."""
    response = client.get("/api/calculator/constants", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "electricity_kwh" in data
    assert "diet_factors" in data
    assert "waste_factor" in data


def test_get_constants_unauthenticated(client) -> None:
    """Constants endpoint must require authentication (401 without token)."""
    response = client.get("/api/calculator/constants")
    assert response.status_code == 401


def test_protected_endpoint_without_token(client) -> None:
    """Accessing a protected endpoint without a token must return 401."""
    response = client.get("/api/calculator/history")
    assert response.status_code == 401


def test_log_emissions_recycling_rate_exact_boundaries(client, auth_headers) -> None:
    """Boundary values 0.0 and 1.0 for recycling_rate should be accepted."""
    response_zero = client.post(
        "/api/calculator/log",
        json={"recycling_rate": 0.0},
        headers=auth_headers,
    )
    assert response_zero.status_code == 200
    assert response_zero.json()["recycling_rate"] == 0.0

    response_one = client.post(
        "/api/calculator/log",
        json={"recycling_rate": 1.0},
        headers=auth_headers,
    )
    assert response_one.status_code == 200
    assert response_one.json()["recycling_rate"] == 1.0


def test_log_history_pagination(client, auth_headers) -> None:
    """Verify that page/limit query params correctly paginate history results."""
    client.post(
        "/api/calculator/log",
        json={"electricity_kwh": 10.0, "logged_date": "2026-06-11"},
        headers=auth_headers,
    )
    client.post(
        "/api/calculator/log",
        json={"electricity_kwh": 20.0, "logged_date": "2026-06-12"},
        headers=auth_headers,
    )

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


def test_log_with_expired_token(client) -> None:
    """Logging emissions with an expired JWT token should return 401."""
    from datetime import timedelta

    from backend.app.auth import create_access_token

    expired_token = create_access_token(
        data={"sub": "someone"},
        expires_delta=timedelta(seconds=-1),
    )
    response = client.post(
        "/api/calculator/log",
        json={"electricity_kwh": 5.0},
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401
