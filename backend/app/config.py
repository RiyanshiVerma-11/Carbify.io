"""
backend/app/config.py
─────────────────────────────────────────────────────────────
Application configuration via pydantic-settings (Pydantic v2).

Features:
  • Automatic .env file loading via `model_config`.
  • Type coercion for all fields — no silent mis-configuration.
  • Startup guard: raises RuntimeError if SECRET_KEY is absent
    in production so the server never starts in an insecure state.
  • Emission factors remain here as infrastructure-level config
    shared by both the calculator route and test assertions.
"""

from __future__ import annotations

import secrets
from functools import lru_cache
from typing import Any

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    All fields are populated from environment variables first,
    then fall back to the declared defaults.  The .env file
    at ``backend/.env`` (relative to the process cwd) is read
    automatically.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",          # tolerate unknown keys in .env
    )

    # ── Project meta ──────────────────────────────────────────────────────
    PROJECT_NAME: str = Field(default="Carbifyio API", description="Human-readable API name.")

    # ── Security ──────────────────────────────────────────────────────────
    SECRET_KEY: str = Field(
        default="",
        description="HMAC secret used to sign JWT tokens. "
                    "Must be set explicitly in production.",
    )
    ALGORITHM: str = Field(default="HS256", description="JWT signing algorithm.")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30,   # 30 minutes (mitigates stolen token window)
        ge=1,
        description="Token lifetime in minutes.",
    )
    CORS_ALLOWED_ORIGINS: list[str] = Field(
        default=[
            "*",
        ],
        description="List of origins allowed to make CORS requests.",
    )

    # ── Database ──────────────────────────────────────────────────────────
    DATABASE_URL: str = Field(
        default="sqlite:///./carbify.db",
        description="SQLAlchemy-compatible database URL.",
    )

    # ── Runtime environment ───────────────────────────────────────────────
    ENV: str = Field(
        default="development",
        description="Runtime mode: 'development', 'testing', or 'production'.",
    )

    # ── Consolidated carbon emission factors (kg CO₂ per unit) ───────────
    EMISSION_FACTORS: dict[str, Any] = Field(
        default={
            "electricity_kwh": 0.385,
            "gas_kwh": 0.185,
            "petrol_car_km": 0.17,
            "diesel_car_km": 0.16,
            "electric_car_km": 0.05,
            "public_transit_km": 0.03,
            "flights_km": 0.12,
            "diet_factors": {
                "meat_heavy": 7.2,
                "medium_meat": 5.6,
                "low_meat": 4.7,
                "vegetarian": 3.8,
                "vegan": 2.9,
            },
            "waste_factor": 0.45,
        },
        description="Backend emission factors; exposed via /api/calculator/constants.",
    )

    # ── Validators ────────────────────────────────────────────────────────

    @field_validator("CORS_ALLOWED_ORIGINS", mode="before")
    @classmethod
    def _parse_cors_origins(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @field_validator("ENV", mode="before")
    @classmethod
    def _normalise_env(cls, v: str) -> str:
        normalised = str(v).lower().strip()
        allowed = {"development", "testing", "production"}
        if normalised not in allowed:
            raise ValueError(f"ENV must be one of {allowed}, got '{v}'.")
        return normalised

    @model_validator(mode="after")
    def _validate_secret_key(self) -> "Settings":
        if not self.SECRET_KEY:
            if self.ENV == "production":
                raise RuntimeError(
                    "CRITICAL SECURITY VIOLATION: SECRET_KEY must be set "
                    "explicitly in production mode — refusing to start."
                )
            # Development / testing: auto-generate a cryptographically-safe key.
            # This key is ephemeral (regenerated on every restart) which is
            # intentional for local dev; tokens will not survive a restart.
            object.__setattr__(self, "SECRET_KEY", secrets.token_hex(32))
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return a cached singleton Settings instance.

    Using lru_cache means .env is read only once per process,
    and all call-sites share the same object — zero overhead after
    the first call.
    """
    return Settings()


# Module-level singleton for import convenience:
#   from backend.app.config import settings
settings: Settings = get_settings()

__all__ = ["Settings", "settings", "get_settings"]
