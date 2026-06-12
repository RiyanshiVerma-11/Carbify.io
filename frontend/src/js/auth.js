// Authentication Service for Carbifyio
// v1.1 — BASE_URL must be a relative path so requests route through Nginx proxy.

const BASE_URL = "https://carbify-io.onrender.com/api";

export const AuthService = {
    // Save token and user details to localStorage
    setSession(token, user) {
        localStorage.setItem("carbify_token", token);
        localStorage.setItem("carbify_user", JSON.stringify(user));
    },

    // Clear session details
    clearSession() {
        localStorage.removeItem("carbify_token");
        localStorage.removeItem("carbify_user");
    },

    // Check if user is authenticated
    isAuthenticated() {
        return localStorage.getItem("carbify_token") !== null;
    },

    // Get authorization headers
    getAuthHeaders() {
        const token = localStorage.getItem("carbify_token");
        return token ? { "Authorization": `Bearer ${token}` } : {};
    },

    // Get current local user details
    getLocalUser() {
        const userStr = localStorage.getItem("carbify_user");
        return userStr ? JSON.parse(userStr) : null;
    },

    // Register API Call
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

    // Login API Call (OAuth2 compliant form-data body)
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

    // Refresh profile state
    async fetchProfile() {
        if (!this.isAuthenticated()) return null;
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
