"""backend/app/constants.py
─────────────────────────────────────────────────────────────
Centralised application constants, seed data, and magic numbers.

All static data definitions (habit catalogue, challenge catalogue)
and configuration values that do not belong in ``config.py``
(which focuses on environment-driven settings) are collected here
to enforce a single source of truth.
"""

from __future__ import annotations

# ── Gamification thresholds ───────────────────────────────────────────────

DEFAULT_INACTIVITY_THRESHOLD_DAYS: int = 5
"""Fallback inactivity alert threshold when insufficient data exists
to run Youden's J-statistic optimisation."""

LEADERBOARD_CACHE_TTL_SECONDS: int = 60
"""Time-to-live (seconds) for the database-backed leaderboard cache."""

YOUDEN_CACHE_TTL_SECONDS: int = 43200
"""Time-to-live (seconds) for the Youden threshold cache (12 hours)."""


# ── Default habit seed data ───────────────────────────────────────────────

DEFAULT_HABITS: list[dict[str, str | int | float]] = [
    {
        "slug": "walk_instead_of_drive",
        "name": "Walked/cycled instead of driving",
        "category": "transport",
        "points": 20,
        "co2_saved": 1.5,
    },
    {
        "slug": "turn_off_ac",
        "name": "Turned off AC/heating when away",
        "category": "energy",
        "points": 15,
        "co2_saved": 0.5,
    },
    {
        "slug": "plant_based_day",
        "name": "Ate fully plant-based/vegan meals today",
        "category": "food",
        "points": 25,
        "co2_saved": 2.0,
    },
    {
        "slug": "recycle_bottles",
        "name": "Sorted and recycled plastic/glass waste",
        "category": "waste",
        "points": 10,
        "co2_saved": 0.3,
    },
    {
        "slug": "short_shower",
        "name": "Took a short shower (< 5 minutes)",
        "category": "energy",
        "points": 10,
        "co2_saved": 0.4,
    },
    {
        "slug": "air_dry_clothes",
        "name": "Air-dried laundry instead of using the dryer",
        "category": "energy",
        "points": 15,
        "co2_saved": 0.8,
    },
    {
        "slug": "unplug_idle",
        "name": "Unplugged idle electronic appliances",
        "category": "energy",
        "points": 10,
        "co2_saved": 0.2,
    },
]
"""Catalogue of daily sustainable habits seeded on first startup."""


# ── Default challenge seed data ───────────────────────────────────────────

DEFAULT_CHALLENGES: list[dict[str, str | int | float]] = [
    {
        "title": "Eco Commuter",
        "description": "Commute using public transit, bike, or walking for 5 consecutive days.",
        "points_reward": 50,
        "co2_saving_estimate_kg": 10.0,
        "category": "transport",
        "duration_days": 7,
    },
    {
        "title": "Unplugged Weekend",
        "description": "Power down non-essential electronics and appliances for 48 hours.",
        "points_reward": 30,
        "co2_saving_estimate_kg": 3.5,
        "category": "energy",
        "duration_days": 2,
    },
    {
        "title": "Plant Power",
        "description": "Eat only plant-based/vegan meals for 3 consecutive days.",
        "points_reward": 40,
        "co2_saving_estimate_kg": 8.0,
        "category": "food",
        "duration_days": 3,
    },
    {
        "title": "Zero-Waste Champ",
        "description": "Avoid all single-use plastics and recycle 100% of recyclable waste for 5 days.",
        "points_reward": 40,
        "co2_saving_estimate_kg": 5.0,
        "category": "waste",
        "duration_days": 5,
    },
    {
        "title": "Eco Shower",
        "description": "Limit all showers to under 5 minutes for a full week.",
        "points_reward": 25,
        "co2_saving_estimate_kg": 2.5,
        "category": "energy",
        "duration_days": 7,
    },
]
"""Catalogue of gamified eco-challenges seeded on first startup."""


__all__ = [
    "DEFAULT_CHALLENGES",
    "DEFAULT_HABITS",
    "DEFAULT_INACTIVITY_THRESHOLD_DAYS",
    "LEADERBOARD_CACHE_TTL_SECONDS",
    "YOUDEN_CACHE_TTL_SECONDS",
]
