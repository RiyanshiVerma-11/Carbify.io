/**
 * @file constants.js
 * @description Centralised configuration and fallback values for the Carbifyio frontend.
 *
 * All API endpoint URLs and offline emission factors are defined here
 * to eliminate duplication across service modules.
 */

/**
 * Base URL for all backend API calls.
 *
 * Strategy:
 *   - When the frontend is served by Nginx (Docker / production), all
 *     requests use a relative `/api` path.  Nginx proxies `/api/*` to
 *     the backend container server-side, so the browser never talks
 *     directly to port 8000.
 *   - When running the frontend standalone (e.g., opening `index.html`
 *     from the filesystem or a plain live-reload server without Nginx),
 *     we fall back to the deployed Render backend so the app still works.
 *
 * @type {string}
 */
export const BASE_URL = (() => {
    // If served from a real HTTP/HTTPS origin (Nginx, Vercel, etc.)
    // use a relative path — works for any hostname including production domains.
    const { protocol, hostname } = window.location;
    if (protocol === "http:" || protocol === "https:") {
        return "/api";
    }
    // Filesystem fallback (file://) — point at the deployed backend.
    return "https://carbify-io.onrender.com/api";
})();

/**
 * Fallback emission factors for offline live-preview estimation.
 *
 * These mirror the canonical factors served by
 * `GET /api/calculator/constants` and are used when the network
 * request fails or is still in-flight.
 *
 * @type {Object}
 */
export const FALLBACK_EMISSION_FACTORS = {
    electricity_kwh: 0.385,
    gas_kwh: 0.185,
    petrol_car_km: 0.17,
    diesel_car_km: 0.16,
    electric_car_km: 0.05,
    public_transit_km: 0.03,
    flights_km: 0.12,
    diet_factors: {
        "meat_heavy": 7.2,
        "medium_meat": 5.6,
        "low_meat": 4.7,
        "vegetarian": 3.8,
        "vegan": 2.9
    },
    waste_factor: 0.45
};
