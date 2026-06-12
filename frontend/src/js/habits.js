// Habits & Challenges Service for Carbifyio
import { AuthService } from "./auth.js";

const BASE_URL = "/api";

export const HabitsService = {
    // Fetch pre-defined habits metrics
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

    // Log a habit completion
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

    // Get habit logging history
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

    // Fetch challenges list
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

    // Fetch user joined challenges
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

    // Join a challenge
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

    // Mark challenge as completed
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
