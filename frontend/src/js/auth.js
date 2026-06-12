/**
 * @file auth.js
 * @description Authentication service for Carbifyio — handles registration,
 *              login, session persistence (localStorage), and profile refresh.
 */

import { BASE_URL } from "./constants.js";

/**
 * Stateless authentication service backed by JWT tokens stored in localStorage.
 * @namespace AuthService
 */
export const AuthService = {
    /**
     * Persist the access token and user object to localStorage.
     * @param {string} token - JWT access token.
     * @param {Object} user  - User profile object returned by the API.
     */
    setSession(token, user) {
        localStorage.setItem("carbify_token", token);
        localStorage.setItem("carbify_user", JSON.stringify(user));
    },

    /**
     * Remove all session data from localStorage (logout).
     */
    clearSession() {
        localStorage.removeItem("carbify_token");
        localStorage.removeItem("carbify_user");
    },

    /**
     * Check whether the current browser session has a stored token.
     * @returns {boolean}
     */
    isAuthenticated() {
        return localStorage.getItem("carbify_token") !== null;
    },

    /**
     * Build the Authorization header for authenticated API calls.
     * @returns {Object} Headers object with Bearer token, or empty object.
     */
    getAuthHeaders() {
        const token = localStorage.getItem("carbify_token");
        return token ? { "Authorization": `Bearer ${token}` } : {};
    },

    /**
     * Retrieve the cached user profile from localStorage.
     * @returns {Object|null} Parsed user object, or null if absent.
     */
    getLocalUser() {
        const userStr = localStorage.getItem("carbify_user");
        return userStr ? JSON.parse(userStr) : null;
    },

    /**
     * Register a new user account via the backend API.
     * @param {string} username - Desired username (min 3 chars).
     * @param {string} email    - Valid email address.
     * @param {string} password - Password (min 6 chars).
     * @returns {Promise<Object>} Created user data.
     * @throws {Error} If registration fails (duplicate username/email, validation).
     */
    async register(username, email, password) {
        try {
            const response = await fetch(`${BASE_URL}/auth/register`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username, email, password })
            });
            
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.detail || "Registration failed");
            }
            return data;
        } catch (error) {
            console.error("Registration error:", error);
            throw error;
        }
    },

    /**
     * Authenticate with username + password and store the session.
     * @param {string} username - Account username.
     * @param {string} password - Account password.
     * @returns {Promise<Object>} User profile object.
     * @throws {Error} If authentication fails.
     */
    async login(username, password) {
        try {
            const formData = new URLSearchParams();
            formData.append("username", username);
            formData.append("password", password);

            const response = await fetch(`${BASE_URL}/auth/login`, {
                method: "POST",
                headers: { "Content-Type": "application/x-www-form-urlencoded" },
                body: formData
            });

            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.detail || "Authentication failed");
            }
            
            // Set session
            this.setSession(data.access_token, data.user);
            return data.user;
        } catch (error) {
            console.error("Login error:", error);
            throw error;
        }
    },

    /**
     * Re-fetch the current user's profile from the backend and update the
     * localStorage cache.
     * @returns {Promise<Object|null>} Updated user profile, or null if not authenticated.
     * @throws {Error} If the profile fetch fails (clears session automatically).
     */
    async fetchProfile() {
        if (!this.isAuthenticated()) {
            return null;
        }
        try {
            const response = await fetch(`${BASE_URL}/auth/me`, {
                headers: this.getAuthHeaders()
            });

            const data = await response.json();
            if (!response.ok) {
                this.clearSession();
                throw new Error(data.detail || "Failed to fetch profile");
            }
            // Update user cache
            localStorage.setItem("carbify_user", JSON.stringify(data));
            return data;
        } catch (error) {
            this.clearSession();
            throw error;
        }
    }
};
