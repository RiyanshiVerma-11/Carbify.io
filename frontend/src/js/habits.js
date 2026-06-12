/**
 * @file habits.js
 * @description Habits & Challenges service — manages habit logging,
 *              challenge enrollment/completion, and data fetching.
 */

import { AuthService } from "./auth.js";
import { BASE_URL } from "./constants.js";

/**
 * Service for managing sustainable habits and eco-challenges.
 * @namespace HabitsService
 */
export const HabitsService = {
    /**
     * Fetch the catalogue of pre-defined sustainable habits.
     * @returns {Promise<Object>} Habit catalogue keyed by slug.
     * @throws {Error} If the fetch fails.
     */
    async getAvailableHabits() {
        try {
            const response = await fetch(`${BASE_URL}/habits/list`, {
                headers: AuthService.getAuthHeaders()
            });
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.detail || "Failed to fetch habits list");
            }
            return data;
        } catch (error) {
            console.error("Fetch habits list error:", error);
            throw error;
        }
    },

    /**
     * Log a habit completion for the current day.
     * @param {string} habitKey - The slug identifier of the habit.
     * @returns {Promise<Object>} Created habit log entry.
     * @throws {Error} If logging fails (e.g. duplicate per day).
     */
    async logHabit(habitKey) {
        try {
            const response = await fetch(`${BASE_URL}/habits/log`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    ...AuthService.getAuthHeaders()
                },
                body: JSON.stringify({ habit_name: habitKey })
            });
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.detail || "Failed to log habit");
            }
            return data;
        } catch (error) {
            console.error("Log habit error:", error);
            throw error;
        }
    },

    /**
     * Get the authenticated user's habit logging history.
     * @returns {Promise<Array>} Array of habit log entries, newest first.
     * @throws {Error} If the fetch fails.
     */
    async getHistory() {
        try {
            const response = await fetch(`${BASE_URL}/habits/history`, {
                headers: AuthService.getAuthHeaders()
            });
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.detail || "Failed to fetch habit history");
            }
            return data;
        } catch (error) {
            console.error("Fetch habit history error:", error);
            throw error;
        }
    },

    /**
     * Fetch the full list of available eco-challenges.
     * @returns {Promise<Array>} Array of challenge objects.
     * @throws {Error} If the fetch fails.
     */
    async getChallenges() {
        try {
            const response = await fetch(`${BASE_URL}/challenges/list`, {
                headers: AuthService.getAuthHeaders()
            });
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.detail || "Failed to fetch challenges");
            }
            return data;
        } catch (error) {
            console.error("Fetch challenges error:", error);
            throw error;
        }
    },

    /**
     * Fetch challenges the current user has joined.
     * @returns {Promise<Array>} Array of user-challenge enrolment objects.
     * @throws {Error} If the fetch fails.
     */
    async getUserChallenges() {
        try {
            const response = await fetch(`${BASE_URL}/challenges/user`, {
                headers: AuthService.getAuthHeaders()
            });
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.detail || "Failed to fetch user challenges");
            }
            return data;
        } catch (error) {
            console.error("Fetch user challenges error:", error);
            throw error;
        }
    },

    /**
     * Enrol the current user in a challenge.
     * @param {number} challengeId - The challenge ID to join.
     * @returns {Promise<Object>} Created enrolment record.
     * @throws {Error} If joining fails (already joined/completed).
     */
    async joinChallenge(challengeId) {
        try {
            const response = await fetch(`${BASE_URL}/challenges/${challengeId}/join`, {
                method: "POST",
                headers: AuthService.getAuthHeaders()
            });
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.detail || "Failed to join challenge");
            }
            return data;
        } catch (error) {
            console.error("Join challenge error:", error);
            throw error;
        }
    },

    /**
     * Mark a challenge as completed for the current user.
     * @param {number} challengeId - The challenge ID to complete.
     * @returns {Promise<Object>} Updated enrolment record.
     * @throws {Error} If completion fails (not joined, already complete).
     */
    async completeChallenge(challengeId) {
        try {
            const response = await fetch(`${BASE_URL}/challenges/${challengeId}/complete`, {
                method: "POST",
                headers: AuthService.getAuthHeaders()
            });
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.detail || "Failed to complete challenge");
            }
            return data;
        } catch (error) {
            console.error("Complete challenge error:", error);
            throw error;
        }
    }
};
