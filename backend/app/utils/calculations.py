"""
Centralized carbon emissions calculation utilities.

This module is the single source of truth for all CO2 computation logic.
Both the calculator and analytics routes import from here — zero duplication.

Public API
----------
calculate_co2(...)            -> float   (total kg CO2)
calculate_co2_breakdown(...)  -> dict    (per-category kg CO2)
VALID_DIET_TYPES              -> frozenset  (canonical diet strings)
"""
from __future__ import annotations

from backend.app.config import settings

# Canonical set of valid diet type strings — shared by schemas.py (Literal) and
# any runtime guard that needs programmatic membership testing.
VALID_DIET_TYPES: frozenset[str] = frozenset(
    {"meat_heavy", "medium_meat", "low_meat", "vegetarian", "vegan"}
)

_FALLBACK_DIET = "vegetarian"


def _diet_co2(diet_type: str) -> float:
    """
    Return the daily CO2 value for a given diet type.

    If an unrecognised string is passed (should not happen after Pydantic
    validation, but defensive coding) the vegetarian factor is used instead
    of silently returning 0.
    """
    return settings.EMISSION_FACTORS["diet_factors"].get(
        diet_type,
        settings.EMISSION_FACTORS["diet_factors"][_FALLBACK_DIET],
    )


def calculate_co2(
    electricity_kwh: float = 0.0,
    gas_kwh: float = 0.0,
    petrol_car_km: float = 0.0,
    diesel_car_km: float = 0.0,
    electric_car_km: float = 0.0,
    public_transit_km: float = 0.0,
    flights_km: float = 0.0,
    diet_type: str = _FALLBACK_DIET,
    waste_kg: float = 0.0,
    recycling_rate: float = 0.0,
) -> float:
    """
    Calculate total daily CO2 emissions in kilograms.

    Args:
        electricity_kwh:   Electricity consumed in kWh.
        gas_kwh:           Natural gas consumed in kWh.
        petrol_car_km:     Distance driven in a petrol car (km).
        diesel_car_km:     Distance driven in a diesel car (km).
        electric_car_km:   Distance driven in an electric car (km).
        public_transit_km: Distance travelled on public transit (km).
        flights_km:        Distance travelled by air (km).
        diet_type:         One of: meat_heavy, medium_meat, low_meat,
                           vegetarian, vegan.
        waste_kg:          Waste produced in kg.
        recycling_rate:    Fraction of waste recycled (0.0–1.0).

    Returns:
        Total CO2 equivalent in kg, rounded to 2 decimal places.
    """
    breakdown = calculate_co2_breakdown(
        electricity_kwh=electricity_kwh,
        gas_kwh=gas_kwh,
        petrol_car_km=petrol_car_km,
        diesel_car_km=diesel_car_km,
        electric_car_km=electric_car_km,
        public_transit_km=public_transit_km,
        flights_km=flights_km,
        diet_type=diet_type,
        waste_kg=waste_kg,
        recycling_rate=recycling_rate,
    )
    return round(sum(breakdown.values()), 2)


def calculate_co2_breakdown(
    electricity_kwh: float = 0.0,
    gas_kwh: float = 0.0,
    petrol_car_km: float = 0.0,
    diesel_car_km: float = 0.0,
    electric_car_km: float = 0.0,
    public_transit_km: float = 0.0,
    flights_km: float = 0.0,
    diet_type: str = _FALLBACK_DIET,
    waste_kg: float = 0.0,
    recycling_rate: float = 0.0,
) -> dict[str, float]:
    """
    Calculate CO2 broken down by category.

    Internally delegates to the same emission-factor math used by
    ``calculate_co2`` — no duplicated multiplier constants.

    Returns:
        dict with keys: energy, transport, food, waste (all floats in kg).
    """
    f = settings.EMISSION_FACTORS

    energy_co2 = round(
        electricity_kwh * f["electricity_kwh"]
        + gas_kwh * f["gas_kwh"],
        2,
    )

    transport_co2 = round(
        petrol_car_km * f["petrol_car_km"]
        + diesel_car_km * f["diesel_car_km"]
        + electric_car_km * f["electric_car_km"]
        + public_transit_km * f["public_transit_km"]
        + flights_km * f["flights_km"],
        2,
    )

    food_co2 = round(_diet_co2(diet_type), 2)

    waste_co2 = round(waste_kg * f["waste_factor"] * (1.0 - recycling_rate), 2)

    return {
        "energy": energy_co2,
        "transport": transport_co2,
        "food": food_co2,
        "waste": waste_co2,
    }
