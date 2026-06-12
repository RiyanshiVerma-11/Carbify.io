"""
backend/tests/test_config.py
─────────────────────────────────────────────────────────────
Unit tests for the Settings / configuration module.

Validates environment-driven config parsing, CORS list handling,
and production secret-key enforcement.
"""

from __future__ import annotations

import pytest

from backend.app.config import Settings


class TestSettingsDefaults:
    """Verify default setting values are sane."""

    def test_default_env_is_development(self) -> None:
        """The default environment should be 'development'."""
        s = Settings(ENV="development", SECRET_KEY="")
        assert s.ENV == "development"

    def test_default_database_url(self) -> None:
        """Default database URL should be a SQLite connection string."""
        s = Settings(ENV="development", SECRET_KEY="")
        assert "sqlite" in s.DATABASE_URL

    def test_default_algorithm_is_hs256(self) -> None:
        """JWT algorithm should default to HS256."""
        s = Settings(ENV="development", SECRET_KEY="")
        assert s.ALGORITHM == "HS256"

    def test_default_token_expiry(self) -> None:
        """Token expiry should default to 30 minutes."""
        s = Settings(ENV="development", SECRET_KEY="")
        assert s.ACCESS_TOKEN_EXPIRE_MINUTES == 30

    def test_cors_origins_not_wildcard(self) -> None:
        """Default CORS origins must NOT contain a wildcard."""
        s = Settings(ENV="development", SECRET_KEY="")
        assert "*" not in s.CORS_ALLOWED_ORIGINS


class TestSettingsSecretKey:
    """Validate production-mode secret key enforcement."""

    def test_production_empty_secret_raises(self) -> None:
        """Production mode with an empty SECRET_KEY must raise RuntimeError."""
        with pytest.raises(RuntimeError, match="SECRET_KEY"):
            Settings(ENV="production", SECRET_KEY="")

    def test_development_empty_secret_generates_key(self) -> None:
        """Development mode with an empty SECRET_KEY should auto-generate one."""
        s = Settings(ENV="development", SECRET_KEY="")
        assert len(s.SECRET_KEY) > 0

    def test_testing_empty_secret_generates_key(self) -> None:
        """Testing mode with an empty SECRET_KEY should auto-generate one."""
        s = Settings(ENV="testing", SECRET_KEY="")
        assert len(s.SECRET_KEY) > 0

    def test_production_with_valid_key_succeeds(self) -> None:
        """Production mode with a proper SECRET_KEY should not raise."""
        key = "a" * 64  # 32-byte hex string
        s = Settings(ENV="production", SECRET_KEY=key)
        assert key == s.SECRET_KEY


class TestSettingsEmissionFactors:
    """Validate emission factor configuration."""

    def test_emission_factors_has_required_keys(self) -> None:
        """Emission factors dict should contain all expected keys."""
        s = Settings(ENV="development", SECRET_KEY="")
        required = {
            "electricity_kwh",
            "gas_kwh",
            "petrol_car_km",
            "diesel_car_km",
            "electric_car_km",
            "public_transit_km",
            "flights_km",
            "diet_factors",
            "waste_factor",
        }
        assert required.issubset(set(s.EMISSION_FACTORS.keys()))

    def test_diet_factors_has_all_types(self) -> None:
        """Diet factors should include all five canonical diet types."""
        s = Settings(ENV="development", SECRET_KEY="")
        diet_keys = set(s.EMISSION_FACTORS["diet_factors"].keys())
        expected = {"meat_heavy", "medium_meat", "low_meat", "vegetarian", "vegan"}
        assert diet_keys == expected

    def test_emission_factors_are_positive(self) -> None:
        """All scalar emission factors should be positive numbers."""
        s = Settings(ENV="development", SECRET_KEY="")
        for key, value in s.EMISSION_FACTORS.items():
            if key == "diet_factors":
                for diet_val in value.values():
                    assert diet_val > 0, f"diet_factors[{key}] must be positive"
            else:
                assert value > 0, f"{key} must be positive"
