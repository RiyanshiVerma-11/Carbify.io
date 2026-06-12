"""
scripts/smoke_test.py
─────────────────────────────────────────────────────────────
Manual end-to-end smoke test against the live deployed backend.

This script is NOT part of the automated pytest suite.
It is a developer utility for quickly verifying that the deployed
Render backend is healthy and all major endpoints respond correctly.

Usage (requires the `requests` package):
    python scripts/smoke_test.py [--base-url https://your-backend.onrender.com/api]

Exit codes:
    0  – All smoke checks passed.
    1  – One or more checks failed.
"""

from __future__ import annotations

import argparse
import sys
import requests


DEFAULT_BASE_URL = "https://carbify-io.onrender.com/api"
TEST_USERNAME = "smoketest_user_auto"
TEST_EMAIL = "smoketest_auto@carbify.io"
TEST_PASSWORD = "SmokeTestPass123!"


def run_smoke_tests(base_url: str) -> bool:
    """Run all smoke checks. Returns True if all pass."""
    session = requests.Session()
    passed = 0
    failed = 0

    def check(name: str, condition: bool, detail: str = "") -> None:
        nonlocal passed, failed
        if condition:
            print(f"  ✅ {name}")
            passed += 1
        else:
            print(f"  ❌ {name}{': ' + detail if detail else ''}")
            failed += 1

    print(f"\n🌱 Carbifyio Smoke Test — {base_url}\n{'─' * 50}")

    # 1. Health check
    print("\n[1] Health")
    r = session.get(f"{base_url.rstrip('/api')}/health")
    check("GET /health returns 200", r.status_code == 200)
    check("Health body has status=healthy", r.json().get("status") == "healthy")

    # 2. Register
    print("\n[2] Auth — Register")
    r = session.post(f"{base_url}/auth/register", json={
        "username": TEST_USERNAME,
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
    })
    check("POST /auth/register ≤ 422", r.status_code in (200, 422),
          f"got {r.status_code}")  # 422 = already registered

    # 3. Login
    print("\n[3] Auth — Login")
    r = session.post(f"{base_url}/auth/login", json={
        "username": TEST_USERNAME,
        "password": TEST_PASSWORD,
    })
    check("POST /auth/login returns 200", r.status_code == 200, r.text[:120])
    token = r.json().get("access_token") if r.status_code == 200 else None
    check("Response contains access_token", bool(token))

    if not token:
        print("\n⚠ Cannot continue without a token — aborting remaining checks.")
        return False

    headers = {"Authorization": f"Bearer {token}"}

    # 4. Calculator constants
    print("\n[4] Calculator")
    r = session.get(f"{base_url}/calculator/constants", headers=headers)
    check("GET /calculator/constants returns 200", r.status_code == 200)
    check("electricity_kwh factor present", "electricity_kwh" in r.json())

    # 5. Log an emission
    r = session.post(f"{base_url}/calculator/log", headers=headers, json={
        "electricity_kwh": 10, "gas_kwh": 5, "petrol_car_km": 10,
        "diesel_car_km": 0, "electric_car_km": 0, "public_transit_km": 0,
        "flights_km": 0, "diet_type": "vegetarian", "waste_kg": 2,
        "recycling_rate": 0.5,
    })
    check("POST /calculator/log returns 200", r.status_code == 200, r.text[:120])

    # 6. Analytics
    print("\n[5] Analytics")
    r = session.get(f"{base_url}/analytics", headers=headers)
    check("GET /analytics returns 200", r.status_code == 200)
    data = r.json()
    check("total_co2_kg > 0 after logging", data.get("total_co2_kg", 0) > 0)

    # 7. Trend
    r = session.get(f"{base_url}/analytics/trend", headers=headers)
    check("GET /analytics/trend returns 200", r.status_code == 200)
    trend = r.json().get("trend", [])
    check("Trend contains 14 data points", len(trend) == 14, f"got {len(trend)}")

    # 8. Habits list
    print("\n[6] Habits")
    r = session.get(f"{base_url}/habits/list", headers=headers)
    check("GET /habits/list returns 200", r.status_code == 200)
    check("At least 7 habits seeded", len(r.json()) >= 7)

    # 9. Leaderboard
    print("\n[7] Leaderboard")
    r = session.get(f"{base_url}/analytics/leaderboard", headers=headers)
    check("GET /analytics/leaderboard returns 200", r.status_code == 200)

    # Summary
    total = passed + failed
    print(f"\n{'─' * 50}")
    print(f"Results: {passed}/{total} passed, {failed} failed")
    return failed == 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Carbifyio API smoke test")
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"Backend API base URL (default: {DEFAULT_BASE_URL})",
    )
    args = parser.parse_args()
    success = run_smoke_tests(args.base_url)
    sys.exit(0 if success else 1)
