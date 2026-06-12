/**
 * @file calculator.js
 * @description Carbon Calculator service — fetches emission factors from the
 *              backend, computes live client-side previews, and submits daily
 *              logs via the REST API.
 */

import { AuthService } from "./auth.js";
import { BASE_URL, FALLBACK_EMISSION_FACTORS } from "./constants.js";

/**
 * Carbon Calculator service with offline-capable live preview.
 * @namespace CalculatorService
 */
export const CalculatorService = {
    /**
     * Emission factors sourced from the backend.
     * @type {Object|null}
     */
    emissionFactors: null,

    /**
     * Fetch the canonical emission factors from the backend and cache them
     * locally.  Falls back to {@link FALLBACK_EMISSION_FACTORS} on failure.
     * @returns {Promise<void>}
     */
    async fetchConstants() {
        try {
            const response = await fetch(`${BASE_URL}/calculator/constants`, {
                headers: AuthService.getAuthHeaders()
            });
            if (response.ok) {
                const data = await response.json();
                this.emissionFactors = data;
            } else {
                console.warn("CalculatorService.fetchConstants: non-OK response, using fallback factors.");
                this._applyFallbackFactors();
            }
        } catch (error) {
            console.error("CalculatorService.fetchConstants: network error, using fallback factors.", error);
            this._applyFallbackFactors();
        }
    },

    /**
     * Apply the hardcoded offline fallback emission factors.
     * @private
     */
    _applyFallbackFactors() {
        this.emissionFactors = FALLBACK_EMISSION_FACTORS;
    },

    /**
     * Extract and parse numeric inputs from the calculator form in a DRY manner.
     * @param {HTMLFormElement} form - The calculator form element.
     * @returns {Object} Parsed input values keyed by field name.
     */
    getCalculatorInputs(form) {
        if (!form) {
            return {};
        }
        return {
            electricity_kwh: parseFloat(form.electricity_kwh.value) || 0.0,
            gas_kwh: parseFloat(form.gas_kwh.value) || 0.0,
            petrol_car_km: parseFloat(form.petrol_car_km.value) || 0.0,
            diesel_car_km: parseFloat(form.diesel_car_km.value) || 0.0,
            electric_car_km: parseFloat(form.electric_car_km.value) || 0.0,
            public_transit_km: parseFloat(form.public_transit_km.value) || 0.0,
            flights_km: parseFloat(form.flights_km.value) || 0.0,
            diet_type: form.diet_type.value,
            waste_kg: parseFloat(form.waste_kg.value) || 0.0,
            recycling_rate: parseFloat(form.recycling_rate.value) || 0.0
        };
    },

    /**
     * Compute the estimated daily carbon footprint from form inputs.
     * @param {Object} inputs - Parsed form inputs from {@link getCalculatorInputs}.
     * @returns {number} Total CO₂ in kg, rounded to 2 decimal places.
     */
    calculateLive(inputs) {
        if (!this.emissionFactors) {
            this._applyFallbackFactors();
        }

        const f = this.emissionFactors;

        // ── Energy ────────────────────────────────────────────────────────
        const electricity = (parseFloat(inputs.electricity_kwh) || 0) * f.electricity_kwh;
        const gas         = (parseFloat(inputs.gas_kwh)         || 0) * f.gas_kwh;

        // ── Transport ─────────────────────────────────────────────────────
        const petrol  = (parseFloat(inputs.petrol_car_km)     || 0) * f.petrol_car_km;
        const diesel  = (parseFloat(inputs.diesel_car_km)     || 0) * f.diesel_car_km;
        const electric= (parseFloat(inputs.electric_car_km)   || 0) * f.electric_car_km;
        const transit = (parseFloat(inputs.public_transit_km) || 0) * f.public_transit_km;
        const flights = (parseFloat(inputs.flights_km)        || 0) * f.flights_km;

        // ── Diet ──────────────────────────────────────────────────────────
        const diet = f.diet_factors[inputs.diet_type] ?? f.diet_factors["vegetarian"];

        // ── Waste ─────────────────────────────────────────────────────────
        const recyclingRate = parseFloat(inputs.recycling_rate) || 0;
        const waste = (parseFloat(inputs.waste_kg) || 0) * f.waste_factor * (1.0 - recyclingRate);

        const total = electricity + gas + petrol + diesel + electric + transit + flights + diet + waste;
        return parseFloat(total.toFixed(2));
    },

    // ── Backend API calls ─────────────────────────────────────────────────

    /**
     * Submit a completed emissions log to the backend.
     * @param {Object} inputs - The emissions log payload.
     * @returns {Promise<Object>} Saved log data.
     * @throws {Error} If the log submission fails.
     */
    async logEmissions(inputs) {
        try {
            const headers = {
                "Content-Type": "application/json",
                ...AuthService.getAuthHeaders()
            };
            const response = await fetch(`${BASE_URL}/calculator/log`, {
                method: "POST",
                headers,
                body: JSON.stringify(inputs)
            });
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.detail || "Failed to log emissions");
            }
            return data;
        } catch (error) {
            console.error("CalculatorService.logEmissions error:", error);
            throw error;
        }
    },

    /**
     * Fetch the full emissions log history for the current user.
     * @returns {Promise<Array>} Array of emissions log entries.
     * @throws {Error} If the history fetch fails.
     */
    async getHistory() {
        try {
            const response = await fetch(`${BASE_URL}/calculator/history`, {
                headers: AuthService.getAuthHeaders()
            });
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.detail || "Failed to fetch history");
            }
            return data;
        } catch (error) {
            console.error("CalculatorService.getHistory error:", error);
            throw error;
        }
    },

    /**
     * Fetch the most recent emissions log entry for the current user.
     * @returns {Promise<Object>} Latest emissions log entry.
     * @throws {Error} If the fetch fails.
     */
    async getLatest() {
        try {
            const response = await fetch(`${BASE_URL}/calculator/latest`, {
                headers: AuthService.getAuthHeaders()
            });
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.detail || "Failed to fetch latest log");
            }
            return data;
        } catch (error) {
            console.error("CalculatorService.getLatest error:", error);
            throw error;
        }
    }
};
