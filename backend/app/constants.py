"""
backend/app/constants.py
─────────────────────────────────────────────────────────────
Centralised, immutable application constants.

Keeping domain data out of both config (infrastructure) and
route files (HTTP layer) improves cohesion and makes the
catalogue the single source of truth for habit metadata.
"""

from __future__ import annotations

from typing import Final

# ---------------------------------------------------------------------------
# Habit catalogue
# ---------------------------------------------------------------------------
# Each key is the canonical slug used in API payloads.
# Values are frozen at import-time; treat them as read-only.

HABIT_METRICS: Final[dict[str, dict]] = {
    "walk_instead_of_drive": {
        "name": "Walked/cycled instead of driving",
        "category": "transport",
        "points": 20,
        "co2_saved": 1.5,
    },
    "turn_off_ac": {
        "name": "Turned off AC/heating when away",
        "category": "energy",
        "points": 15,
        "co2_saved": 0.5,
    },
    "plant_based_day": {
        "name": "Ate fully plant-based/vegan meals today",
        "category": "food",
        "points": 25,
        "co2_saved": 2.0,
    },
    "recycle_bottles": {
        "name": "Sorted and recycled plastic/glass waste",
        "category": "waste",
        "points": 10,
        "co2_saved": 0.3,
    },
    "short_shower": {
        "name": "Took a short shower (< 5 minutes)",
        "category": "energy",
        "points": 10,
        "co2_saved": 0.4,
    },
    "air_dry_clothes": {
        "name": "Air-dried laundry instead of using the dryer",
        "category": "energy",
        "points": 15,
        "co2_saved": 0.8,
    },
    "unplug_idle": {
        "name": "Unplugged idle electronic appliances",
        "category": "energy",
        "points": 10,
        "co2_saved": 0.2,
    },
}

__all__ = ["HABIT_METRICS"]
