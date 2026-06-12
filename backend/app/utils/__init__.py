"""
backend/app/utils
─────────────────────────────────────────────────────────────
Utility package — shared calculation helpers used by multiple route modules.

Exposes
-------
calculate_co2_from_log          – Total CO₂ scalar from an EmissionsLog ORM row.
calculate_co2_breakdown_from_log – Per-category CO₂ breakdown dict.

Both functions are also importable directly from ``backend.app.utils.calculations``.
"""

from backend.app.utils.calculations import (
    calculate_co2_from_log,
    calculate_co2_breakdown_from_log,
)

__all__ = [
    "calculate_co2_from_log",
    "calculate_co2_breakdown_from_log",
]
