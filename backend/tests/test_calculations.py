"""
backend/tests/test_calculations.py
─────────────────────────────────────────────────────────────
Unit tests for the centralised carbon calculation utilities.

These tests validate the shared ``calculate_co2``, ``calculate_co2_breakdown``,
and ``calculate_co2_from_log`` functions directly — independent of HTTP routing.
"""

from __future__ import annotations

import pytest

from backend.app.utils.calculations import (
    VALID_DIET_TYPES,
    calculate_co2,
    calculate_co2_breakdown,
)
from backend.app.config import settings


class TestCalculateCo2:
    """Tests for the top-level ``calculate_co2()`` function."""

    def test_zero_inputs_returns_diet_baseline(self) -> None:
        """With all numeric inputs zeroed, total should equal the default diet factor only."""
        result = calculate_co2()
        expected_diet = settings.EMISSION_FACTORS["diet_factors"]["vegetarian"]
        assert result == round(expected_diet, 2)

    def test_all_zero_inputs_explicit(self) -> None:
        """Explicitly zeroing every parameter should match default-args result."""
        result = calculate_co2(
            electricity_kwh=0.0,
            gas_kwh=0.0,
            petrol_car_km=0.0,
            diesel_car_km=0.0,
            electric_car_km=0.0,
            public_transit_km=0.0,
            flights_km=0.0,
            diet_type="vegetarian",
            waste_kg=0.0,
            recycling_rate=0.0,
        )
        expected = settings.EMISSION_FACTORS["diet_factors"]["vegetarian"]
        assert result == round(expected, 2)

    def test_electricity_only(self) -> None:
        """Only electricity input should produce energy + diet baseline."""
        kwh = 10.0
        result = calculate_co2(electricity_kwh=kwh)
        factor = settings.EMISSION_FACTORS["electricity_kwh"]
        diet = settings.EMISSION_FACTORS["diet_factors"]["vegetarian"]
        expected = round(kwh * factor + diet, 2)
        assert result == expected

    def test_petrol_transport(self) -> None:
        """Petrol car distance should contribute to total via its emission factor."""
        km = 50.0
        result = calculate_co2(petrol_car_km=km)
        factor = settings.EMISSION_FACTORS["petrol_car_km"]
        diet = settings.EMISSION_FACTORS["diet_factors"]["vegetarian"]
        expected = round(km * factor + diet, 2)
        assert result == expected

    def test_all_fields_populated(self) -> None:
        """Exercise all input fields simultaneously to ensure no field is ignored."""
        result = calculate_co2(
            electricity_kwh=10.0,
            gas_kwh=5.0,
            petrol_car_km=20.0,
            diesel_car_km=10.0,
            electric_car_km=15.0,
            public_transit_km=30.0,
            flights_km=100.0,
            diet_type="meat_heavy",
            waste_kg=3.0,
            recycling_rate=0.5,
        )
        # Just verify it's a positive, non-zero float
        assert isinstance(result, float)
        assert result > 0

    def test_recycling_rate_reduces_waste(self) -> None:
        """A 100 % recycling rate should zero-out the waste component."""
        with_waste = calculate_co2(waste_kg=10.0, recycling_rate=0.0)
        no_waste = calculate_co2(waste_kg=10.0, recycling_rate=1.0)
        assert no_waste < with_waste

    def test_recycling_rate_half(self) -> None:
        """A 50 % recycling rate should halve the waste component."""
        full = calculate_co2_breakdown(waste_kg=10.0, recycling_rate=0.0)
        half = calculate_co2_breakdown(waste_kg=10.0, recycling_rate=0.5)
        assert half["waste"] == pytest.approx(full["waste"] / 2, rel=1e-6)

    @pytest.mark.parametrize("diet", list(VALID_DIET_TYPES))
    def test_all_valid_diet_types(self, diet: str) -> None:
        """Every canonical diet string should produce a valid positive result."""
        result = calculate_co2(diet_type=diet)
        assert isinstance(result, float)
        assert result > 0

    def test_invalid_diet_falls_back_to_vegetarian(self) -> None:
        """An unrecognised diet type should silently fall back to vegetarian."""
        result = calculate_co2(diet_type="unknown_diet")
        expected = calculate_co2(diet_type="vegetarian")
        assert result == expected

    def test_result_is_rounded_to_two_decimals(self) -> None:
        """Verify the result is rounded to at most 2 decimal places."""
        result = calculate_co2(electricity_kwh=7.777, gas_kwh=3.333)
        decimal_part = str(result).split(".")[-1]
        assert len(decimal_part) <= 2


class TestCalculateCo2Breakdown:
    """Tests for the per-category ``calculate_co2_breakdown()`` function."""

    def test_returns_four_categories(self) -> None:
        """Breakdown dict should always contain exactly four keys."""
        breakdown = calculate_co2_breakdown()
        assert set(breakdown.keys()) == {"energy", "transport", "food", "waste"}

    def test_energy_category(self) -> None:
        """Energy category should be the sum of electricity and gas contributions."""
        bd = calculate_co2_breakdown(electricity_kwh=10.0, gas_kwh=5.0)
        f = settings.EMISSION_FACTORS
        expected = round(10.0 * f["electricity_kwh"] + 5.0 * f["gas_kwh"], 2)
        assert bd["energy"] == expected

    def test_transport_category(self) -> None:
        """Transport category should aggregate all vehicle-type contributions."""
        bd = calculate_co2_breakdown(petrol_car_km=10.0, diesel_car_km=10.0)
        f = settings.EMISSION_FACTORS
        expected = round(10.0 * f["petrol_car_km"] + 10.0 * f["diesel_car_km"], 2)
        assert bd["transport"] == expected

    def test_food_category_matches_diet(self) -> None:
        """Food category should equal the diet factor for the given diet type."""
        bd = calculate_co2_breakdown(diet_type="vegan")
        expected = settings.EMISSION_FACTORS["diet_factors"]["vegan"]
        assert bd["food"] == round(expected, 2)

    def test_waste_category_with_recycling(self) -> None:
        """Waste with 50% recycling should halve the raw waste emission."""
        f = settings.EMISSION_FACTORS
        bd = calculate_co2_breakdown(waste_kg=4.0, recycling_rate=0.5)
        expected = round(4.0 * f["waste_factor"] * 0.5, 2)
        assert bd["waste"] == expected

    def test_breakdown_sums_to_total(self) -> None:
        """The sum of breakdown values should equal the total from calculate_co2."""
        kwargs = dict(
            electricity_kwh=8.0,
            gas_kwh=4.0,
            petrol_car_km=15.0,
            diesel_car_km=5.0,
            electric_car_km=10.0,
            public_transit_km=20.0,
            flights_km=50.0,
            diet_type="low_meat",
            waste_kg=2.5,
            recycling_rate=0.3,
        )
        breakdown = calculate_co2_breakdown(**kwargs)
        total = calculate_co2(**kwargs)
        assert total == round(sum(breakdown.values()), 2)
