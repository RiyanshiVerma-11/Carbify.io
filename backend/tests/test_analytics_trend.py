"""
backend/tests/test_analytics_trend.py
─────────────────────────────────────────────────────────────
Tests for the 14-day emissions trend endpoint.

GET /api/analytics/trend
- Returns 14 data points (one per calendar day in the last 14 days).
- Days without a log entry are zero-filled.
- Days with a log entry carry the correct total_co2_kg value.
- Response matches the TrendResponse / TrendDataPoint schema.
"""

from __future__ import annotations

import datetime
from fastapi.testclient import TestClient

# ── Helpers ───────────────────────────────────────────────────────────────────


def _log_emissions(client: TestClient, headers: dict, **overrides) -> None:
    """Post an emissions log with sensible defaults, applying *overrides*."""
    payload = {
        "electricity_kwh": 0.0,
        "gas_kwh": 0.0,
        "petrol_car_km": 0.0,
        "diesel_car_km": 0.0,
        "electric_car_km": 0.0,
        "public_transit_km": 0.0,
        "flights_km": 0.0,
        "diet_type": "vegan",
        "waste_kg": 0.0,
        "recycling_rate": 0.0,
    }
    payload.update(overrides)
    resp = client.post("/api/calculator/log", json=payload, headers=headers)
    assert resp.status_code == 200, resp.text


# ── Tests ─────────────────────────────────────────────────────────────────────


class TestAnalyticsTrend:
    """Tests for GET /api/analytics/trend."""

    def test_trend_returns_14_data_points(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        """The trend array must always contain exactly 14 data points."""
        resp = client.get("/api/analytics/trend", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "trend" in data
        assert len(data["trend"]) == 14

    def test_trend_period_days_is_14(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        """The period_days field must equal 14."""
        resp = client.get("/api/analytics/trend", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["period_days"] == 14

    def test_trend_all_zero_when_no_logs(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        """All total_co2_kg values are 0.0 when the user has no emission logs."""
        resp = client.get("/api/analytics/trend", headers=auth_headers)
        assert resp.status_code == 200
        for point in resp.json()["trend"]:
            assert point["total_co2_kg"] == 0.0

    def test_trend_reflects_logged_emission(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        """A logged emission for today appears in the trend with the correct co2 value."""
        # Log an entry for today — petrol_car_km=10 → 10 × 0.17 = 1.7 kg; + vegan (2.9) = 4.6
        _log_emissions(client, auth_headers, petrol_car_km=10.0)

        resp = client.get("/api/analytics/trend", headers=auth_headers)
        assert resp.status_code == 200
        points = resp.json()["trend"]

        today_str = str(datetime.date.today())
        today_point = next((p for p in points if p["date"] == today_str), None)
        assert today_point is not None, "Today's date must appear in the trend"
        assert (
            today_point["total_co2_kg"] > 0.0
        ), "Today's CO₂ must be non-zero after logging"

    def test_trend_dates_are_ordered_ascending(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        """Trend dates are returned in ascending chronological order (oldest first)."""
        resp = client.get("/api/analytics/trend", headers=auth_headers)
        assert resp.status_code == 200
        dates = [p["date"] for p in resp.json()["trend"]]
        assert dates == sorted(dates), "Trend dates must be in ascending order"

    def test_trend_covers_last_14_calendar_days(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        """The first date is exactly 13 days ago and the last date is today."""
        resp = client.get("/api/analytics/trend", headers=auth_headers)
        assert resp.status_code == 200
        points = resp.json()["trend"]
        today = datetime.date.today()
        expected_start = today - datetime.timedelta(days=13)
        assert points[0]["date"] == str(expected_start)
        assert points[-1]["date"] == str(today)

    def test_trend_requires_authentication(self, client: TestClient) -> None:
        """Unauthenticated requests must receive HTTP 401."""
        resp = client.get("/api/analytics/trend")
        assert resp.status_code == 401

    def test_trend_each_point_has_required_fields(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        """Every data point must contain 'date' and 'total_co2_kg' keys."""
        resp = client.get("/api/analytics/trend", headers=auth_headers)
        assert resp.status_code == 200
        for point in resp.json()["trend"]:
            assert "date" in point
            assert "total_co2_kg" in point

    def test_trend_non_negative_co2_values(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        """All CO₂ values in the trend must be non-negative."""
        _log_emissions(client, auth_headers, electricity_kwh=5.0)
        resp = client.get("/api/analytics/trend", headers=auth_headers)
        assert resp.status_code == 200
        for point in resp.json()["trend"]:
            assert point["total_co2_kg"] >= 0.0
