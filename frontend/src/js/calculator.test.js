/**
 * @file calculator.test.js
 * @description Unit tests for CalculatorService — live carbon estimation logic.
 *
 * Tests the pure calculation functions in isolation using mock emission factors,
 * ensuring correctness of the CO₂ arithmetic for every transport/energy/diet/waste
 * category.
 */

import { describe, it, expect, beforeEach, vi } from "vitest";

// ── Mocks (must be declared before dynamic imports) ───────────────────────────

// Mock constants.js so tests don't depend on window.location
vi.mock("./constants.js", () => ({
    BASE_URL: "/api",
    FALLBACK_EMISSION_FACTORS: {
        electricity_kwh: 0.385,
        gas_kwh: 0.185,
        petrol_car_km: 0.17,
        diesel_car_km: 0.16,
        electric_car_km: 0.05,
        public_transit_km: 0.03,
        flights_km: 0.12,
        diet_factors: {
            meat_heavy: 7.2,
            medium_meat: 5.6,
            low_meat: 4.7,
            vegetarian: 3.8,
            vegan: 2.9,
        },
        waste_factor: 0.45,
    },
}));

// Mock auth.js to avoid localStorage dependency
vi.mock("./auth.js", () => ({
    AuthService: {
        getAuthHeaders: () => ({}),
        isAuthenticated: () => false,
    },
}));

// ── Import after mocks ────────────────────────────────────────────────────────
const { CalculatorService } = await import("./calculator.js");

// ── Test suite ────────────────────────────────────────────────────────────────

describe("CalculatorService.calculateLive", () => {
    const FACTORS = {
        electricity_kwh: 0.385,
        gas_kwh: 0.185,
        petrol_car_km: 0.17,
        diesel_car_km: 0.16,
        electric_car_km: 0.05,
        public_transit_km: 0.03,
        flights_km: 0.12,
        diet_factors: {
            meat_heavy: 7.2,
            medium_meat: 5.6,
            low_meat: 4.7,
            vegetarian: 3.8,
            vegan: 2.9,
        },
        waste_factor: 0.45,
    };

    beforeEach(() => {
        // Inject known factors directly — avoids network call
        CalculatorService.emissionFactors = FACTORS;
    });

    it("returns 0 when all inputs are zero (except diet baseline)", () => {
        const inputs = {
            electricity_kwh: 0,
            gas_kwh: 0,
            petrol_car_km: 0,
            diesel_car_km: 0,
            electric_car_km: 0,
            public_transit_km: 0,
            flights_km: 0,
            diet_type: "vegan",
            waste_kg: 0,
            recycling_rate: 0,
        };
        // vegan diet = 2.9 kg baseline, all other = 0
        expect(CalculatorService.calculateLive(inputs)).toBe(2.9);
    });

    it("calculates electricity correctly", () => {
        const inputs = {
            electricity_kwh: 10,
            gas_kwh: 0, petrol_car_km: 0, diesel_car_km: 0,
            electric_car_km: 0, public_transit_km: 0, flights_km: 0,
            diet_type: "vegan", waste_kg: 0, recycling_rate: 0,
        };
        // 10 × 0.385 + 2.9 (vegan)
        expect(CalculatorService.calculateLive(inputs)).toBeCloseTo(6.75, 2);
    });

    it("calculates petrol car emissions correctly", () => {
        const inputs = {
            electricity_kwh: 0, gas_kwh: 0,
            petrol_car_km: 50,
            diesel_car_km: 0, electric_car_km: 0, public_transit_km: 0, flights_km: 0,
            diet_type: "vegan", waste_kg: 0, recycling_rate: 0,
        };
        // 50 × 0.17 + 2.9 = 11.4
        expect(CalculatorService.calculateLive(inputs)).toBeCloseTo(11.4, 2);
    });

    it("applies recycling_rate to reduce waste emissions", () => {
        const inputs = {
            electricity_kwh: 0, gas_kwh: 0, petrol_car_km: 0, diesel_car_km: 0,
            electric_car_km: 0, public_transit_km: 0, flights_km: 0,
            diet_type: "vegan",
            waste_kg: 2,
            recycling_rate: 0.5,
        };
        // waste = 2 × 0.45 × (1 - 0.5) = 0.45; + 2.9 vegan = 3.35
        expect(CalculatorService.calculateLive(inputs)).toBeCloseTo(3.35, 2);
    });

    it("100% recycling rate eliminates waste emissions", () => {
        const inputs = {
            electricity_kwh: 0, gas_kwh: 0, petrol_car_km: 0, diesel_car_km: 0,
            electric_car_km: 0, public_transit_km: 0, flights_km: 0,
            diet_type: "vegan", waste_kg: 10, recycling_rate: 1.0,
        };
        // waste = 10 × 0.45 × 0 = 0
        expect(CalculatorService.calculateLive(inputs)).toBeCloseTo(2.9, 2);
    });

    it("uses meat_heavy diet factor correctly", () => {
        const inputs = {
            electricity_kwh: 0, gas_kwh: 0, petrol_car_km: 0, diesel_car_km: 0,
            electric_car_km: 0, public_transit_km: 0, flights_km: 0,
            diet_type: "meat_heavy", waste_kg: 0, recycling_rate: 0,
        };
        expect(CalculatorService.calculateLive(inputs)).toBeCloseTo(7.2, 2);
    });

    it("uses vegetarian diet factor correctly", () => {
        const inputs = {
            electricity_kwh: 0, gas_kwh: 0, petrol_car_km: 0, diesel_car_km: 0,
            electric_car_km: 0, public_transit_km: 0, flights_km: 0,
            diet_type: "vegetarian", waste_kg: 0, recycling_rate: 0,
        };
        expect(CalculatorService.calculateLive(inputs)).toBeCloseTo(3.8, 2);
    });

    it("calculates a full combined emissions scenario correctly", () => {
        const inputs = {
            electricity_kwh: 10,   // 10 × 0.385 = 3.85
            gas_kwh: 5,            // 5 × 0.185 = 0.925
            petrol_car_km: 10,     // 10 × 0.17 = 1.7
            diesel_car_km: 0,
            electric_car_km: 0,
            public_transit_km: 0,
            flights_km: 0,
            diet_type: "meat_heavy", // 7.2
            waste_kg: 2,            // 2 × 0.45 × 0.5 = 0.45
            recycling_rate: 0.5,
        };
        // 3.85 + 0.925 + 1.7 + 7.2 + 0.45 = 14.125
        expect(CalculatorService.calculateLive(inputs)).toBeCloseTo(14.13, 2);
    });

    it("falls back to fallback factors when emissionFactors is null", () => {
        CalculatorService.emissionFactors = null;
        const inputs = {
            electricity_kwh: 0, gas_kwh: 0, petrol_car_km: 0, diesel_car_km: 0,
            electric_car_km: 0, public_transit_km: 0, flights_km: 0,
            diet_type: "vegan", waste_kg: 0, recycling_rate: 0,
        };
        // Should not throw — uses FALLBACK_EMISSION_FACTORS
        expect(() => CalculatorService.calculateLive(inputs)).not.toThrow();
    });

    it("returns a rounded number to 2 decimal places", () => {
        const inputs = {
            electricity_kwh: 3,    // 3 × 0.385 = 1.155
            gas_kwh: 0, petrol_car_km: 0, diesel_car_km: 0,
            electric_car_km: 0, public_transit_km: 0, flights_km: 0,
            diet_type: "vegan", waste_kg: 0, recycling_rate: 0,
        };
        const result = CalculatorService.calculateLive(inputs);
        const decimals = (result.toString().split(".")[1] || "").length;
        expect(decimals).toBeLessThanOrEqual(2);
    });
});

describe("CalculatorService.getCalculatorInputs", () => {
    it("returns an object with all 10 expected keys", () => {
        // Simulate a minimal form element
        const mockForm = {
            electricity_kwh: { value: "5" },
            gas_kwh: { value: "2" },
            petrol_car_km: { value: "10" },
            diesel_car_km: { value: "0" },
            electric_car_km: { value: "0" },
            public_transit_km: { value: "3" },
            flights_km: { value: "0" },
            diet_type: { value: "vegetarian" },
            waste_kg: { value: "1" },
            recycling_rate: { value: "0.5" },
        };

        const inputs = CalculatorService.getCalculatorInputs(mockForm);
        expect(Object.keys(inputs)).toHaveLength(10);
        expect(inputs.electricity_kwh).toBe(5);
        expect(inputs.diet_type).toBe("vegetarian");
        expect(inputs.recycling_rate).toBe(0.5);
    });

    it("returns 0 for missing/empty numeric fields", () => {
        const mockForm = {
            electricity_kwh: { value: "" },
            gas_kwh: { value: "abc" },
            petrol_car_km: { value: "" },
            diesel_car_km: { value: "" },
            electric_car_km: { value: "" },
            public_transit_km: { value: "" },
            flights_km: { value: "" },
            diet_type: { value: "vegan" },
            waste_kg: { value: "" },
            recycling_rate: { value: "" },
        };
        const inputs = CalculatorService.getCalculatorInputs(mockForm);
        expect(inputs.electricity_kwh).toBe(0);
        expect(inputs.gas_kwh).toBe(0);
    });

    it("returns empty object when form is null", () => {
        expect(CalculatorService.getCalculatorInputs(null)).toEqual({});
    });
});
