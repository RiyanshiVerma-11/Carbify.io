// Fallback emission factors for offline live-preview estimation
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
