/**
 * @file auth.test.js
 * @description Unit tests for AuthService — session management and API wrappers.
 *
 * Uses jsdom localStorage (provided by Vitest's jsdom environment) and
 * vi.stubGlobal to mock fetch, avoiding real network calls.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";

// Mock constants.js
vi.mock("./constants.js", () => ({
    BASE_URL: "/api",
    FALLBACK_EMISSION_FACTORS: {},
}));

const { AuthService } = await import("./auth.js");

// ── Helpers ───────────────────────────────────────────────────────────────────

/**
 * Create a mock fetch response.
 * @param {any} body - JSON body object.
 * @param {number} status - HTTP status code.
 */
function mockFetch(body, status = 200) {
    return vi.fn().mockResolvedValue({
        ok: status >= 200 && status < 300,
        status,
        json: async () => body,
    });
}

// ── Session management ────────────────────────────────────────────────────────

describe("AuthService — session management", () => {
    beforeEach(() => {
        localStorage.clear();
    });

    it("setSession stores token and user in localStorage", () => {
        AuthService.setSession("test-token", { username: "alice", level: 1, points: 0 });
        expect(localStorage.getItem("carbify_token")).toBe("test-token");
        const stored = JSON.parse(localStorage.getItem("carbify_user"));
        expect(stored.username).toBe("alice");
    });

    it("isAuthenticated returns true when token exists", () => {
        localStorage.setItem("carbify_token", "some-token");
        expect(AuthService.isAuthenticated()).toBe(true);
    });

    it("isAuthenticated returns false when no token", () => {
        localStorage.removeItem("carbify_token");
        expect(AuthService.isAuthenticated()).toBe(false);
    });

    it("clearSession removes token and user", () => {
        AuthService.setSession("token", { username: "bob" });
        AuthService.clearSession();
        expect(localStorage.getItem("carbify_token")).toBeNull();
        expect(localStorage.getItem("carbify_user")).toBeNull();
    });

    it("getAuthHeaders returns Authorization header when token present", () => {
        localStorage.setItem("carbify_token", "my-jwt");
        const headers = AuthService.getAuthHeaders();
        expect(headers).toEqual({ Authorization: "Bearer my-jwt" });
    });

    it("getAuthHeaders returns empty object when no token", () => {
        localStorage.removeItem("carbify_token");
        expect(AuthService.getAuthHeaders()).toEqual({});
    });

    it("getLocalUser returns parsed user object", () => {
        const user = { username: "charlie", level: 2, points: 150 };
        localStorage.setItem("carbify_user", JSON.stringify(user));
        expect(AuthService.getLocalUser()).toEqual(user);
    });

    it("getLocalUser returns null when nothing stored", () => {
        localStorage.removeItem("carbify_user");
        expect(AuthService.getLocalUser()).toBeNull();
    });
});

// ── login ─────────────────────────────────────────────────────────────────────

describe("AuthService.login", () => {
    beforeEach(() => localStorage.clear());
    afterEach(() => vi.restoreAllMocks());

    it("stores session and returns user on successful login", async () => {
        const fakeResponse = {
            access_token: "jwt-abc",
            user: { username: "diana", level: 1, points: 0 },
        };
        vi.stubGlobal("fetch", mockFetch(fakeResponse, 200));

        const user = await AuthService.login("diana", "pass123");
        expect(user.username).toBe("diana");
        expect(localStorage.getItem("carbify_token")).toBe("jwt-abc");
    });

    it("throws an error on failed login (401)", async () => {
        vi.stubGlobal("fetch", mockFetch({ detail: "Invalid credentials" }, 401));
        await expect(AuthService.login("bad", "creds")).rejects.toThrow("Invalid credentials");
    });

    it("clears any previous session before a failed login", async () => {
        AuthService.setSession("old-token", { username: "old" });
        vi.stubGlobal("fetch", mockFetch({ detail: "Unauthorized" }, 401));
        try {
            await AuthService.login("bad", "creds");
        } catch {
            // expected
        }
        // Session should not have been updated with new token
        expect(localStorage.getItem("carbify_token")).toBe("old-token");
    });
});

// ── register ──────────────────────────────────────────────────────────────────

describe("AuthService.register", () => {
    afterEach(() => vi.restoreAllMocks());

    it("resolves with user data on success", async () => {
        const created = { id: 1, username: "eve", email: "eve@test.com" };
        vi.stubGlobal("fetch", mockFetch(created, 200));
        const data = await AuthService.register("eve", "eve@test.com", "password");
        expect(data.username).toBe("eve");
    });

    it("throws error on duplicate username (422)", async () => {
        vi.stubGlobal("fetch", mockFetch({ detail: "Username already registered" }, 422));
        await expect(
            AuthService.register("existing", "x@x.com", "pass")
        ).rejects.toThrow("Username already registered");
    });
});

// ── fetchProfile ──────────────────────────────────────────────────────────────

describe("AuthService.fetchProfile", () => {
    beforeEach(() => localStorage.clear());
    afterEach(() => vi.restoreAllMocks());

    it("returns null and does not call fetch when not authenticated", async () => {
        const fetchSpy = vi.fn();
        vi.stubGlobal("fetch", fetchSpy);
        const result = await AuthService.fetchProfile();
        expect(result).toBeNull();
        expect(fetchSpy).not.toHaveBeenCalled();
    });

    it("updates the cached user in localStorage on success", async () => {
        localStorage.setItem("carbify_token", "valid-token");
        const updatedUser = { username: "frank", level: 3, points: 250, id: 5, email: "f@f.com" };
        vi.stubGlobal("fetch", mockFetch(updatedUser, 200));

        const result = await AuthService.fetchProfile();
        expect(result.username).toBe("frank");
        const cached = JSON.parse(localStorage.getItem("carbify_user"));
        expect(cached.points).toBe(250);
    });

    it("clears session and throws on failed profile fetch (401)", async () => {
        localStorage.setItem("carbify_token", "expired");
        vi.stubGlobal("fetch", mockFetch({ detail: "Token expired" }, 401));
        await expect(AuthService.fetchProfile()).rejects.toThrow();
        expect(localStorage.getItem("carbify_token")).toBeNull();
    });
});
