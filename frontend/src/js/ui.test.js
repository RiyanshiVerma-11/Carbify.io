/**
 * @file ui.test.js
 * @description Unit tests for UIService — DOM rendering, XSS sanitization,
 *              and view-switching logic.
 *
 * Uses jsdom (provided by Vitest's environment) to simulate the browser DOM.
 */

import { describe, it, expect, beforeEach } from "vitest";
import { UIService } from "./ui.js";

// ── escapeHtml ────────────────────────────────────────────────────────────────

describe("UIService.escapeHtml", () => {
    it("escapes < and > to prevent script injection", () => {
        const result = UIService.escapeHtml("<script>alert('xss')</script>");
        expect(result).not.toContain("<script>");
        expect(result).toContain("&lt;script&gt;");
    });

    it("escapes & character", () => {
        expect(UIService.escapeHtml("Tom & Jerry")).toContain("&amp;");
    });

    it("escapes double quotes", () => {
        expect(UIService.escapeHtml('She said "hi"')).toContain("&quot;");
    });

    it("returns empty string for falsy input", () => {
        expect(UIService.escapeHtml(null)).toBe("");
        expect(UIService.escapeHtml(undefined)).toBe("");
        expect(UIService.escapeHtml("")).toBe("");
    });

    it("returns plain text unchanged when no special chars", () => {
        expect(UIService.escapeHtml("Hello World")).toBe("Hello World");
    });

    it("handles numeric-as-string input without throwing", () => {
        expect(() => UIService.escapeHtml("42")).not.toThrow();
    });
});

// ── showToast ─────────────────────────────────────────────────────────────────

describe("UIService.showToast", () => {
    beforeEach(() => {
        // Create a toast container in the jsdom body
        document.body.innerHTML = `<div id="toast-container"></div>`;
    });

    it("adds a toast element to the container", () => {
        UIService.showToast("Operation successful!");
        const container = document.getElementById("toast-container");
        expect(container.children.length).toBe(1);
    });

    it("toast has role=alert for accessibility", () => {
        UIService.showToast("Check ARIA");
        const toast = document.querySelector(".toast");
        expect(toast.getAttribute("role")).toBe("alert");
    });

    it("success toast does NOT have error class", () => {
        UIService.showToast("Success!", "success");
        const toast = document.querySelector(".toast");
        expect(toast.classList.contains("error")).toBe(false);
    });

    it("error toast has error class", () => {
        UIService.showToast("Something went wrong", "error");
        const toast = document.querySelector(".toast");
        expect(toast.classList.contains("error")).toBe(true);
    });

    it("toast contains a close button with aria-label", () => {
        UIService.showToast("Closeable");
        const closeBtn = document.querySelector(".toast-close");
        expect(closeBtn).toBeTruthy();
        expect(closeBtn.getAttribute("aria-label")).toBe("Close notification");
    });

    it("clicking close button removes the toast", () => {
        UIService.showToast("Remove me");
        const closeBtn = document.querySelector(".toast-close");
        closeBtn.click();
        expect(document.querySelector(".toast")).toBeNull();
    });

    it("does not throw when container is absent", () => {
        document.body.innerHTML = ""; // no toast-container
        expect(() => UIService.showToast("No container")).not.toThrow();
    });
});

// ── switchView ────────────────────────────────────────────────────────────────

describe("UIService.switchView", () => {
    beforeEach(() => {
        document.body.innerHTML = `
            <nav>
                <button class="nav-btn" data-target="dashboard-view">Dashboard</button>
                <button class="nav-btn" data-target="calculator-view">Calculator</button>
            </nav>
            <section id="dashboard-view" class="view-panel hidden"><h2>Dashboard</h2></section>
            <section id="calculator-view" class="view-panel hidden"><h2>Calculator</h2></section>
        `;
    });

    it("removes hidden class from the target view", () => {
        UIService.switchView("dashboard-view");
        expect(document.getElementById("dashboard-view").classList.contains("hidden")).toBe(false);
    });

    it("adds hidden class to all non-target views", () => {
        UIService.switchView("dashboard-view");
        expect(document.getElementById("calculator-view").classList.contains("hidden")).toBe(true);
    });

    it("sets aria-current=page on the matching nav button", () => {
        UIService.switchView("calculator-view");
        const calcBtn = document.querySelector("[data-target='calculator-view']");
        expect(calcBtn.getAttribute("aria-current")).toBe("page");
    });

    it("removes aria-current from non-active nav buttons", () => {
        UIService.switchView("calculator-view");
        const dashBtn = document.querySelector("[data-target='dashboard-view']");
        expect(dashBtn.hasAttribute("aria-current")).toBe(false);
    });
});

// ── renderLeaderboard ─────────────────────────────────────────────────────────

describe("UIService.renderLeaderboard", () => {
    beforeEach(() => {
        document.body.innerHTML = `<table><tbody id="leaderboard-rows"></tbody></table>`;
    });

    it("renders the correct number of rows", () => {
        const data = [
            { username: "alice", points: 500, level: 5 },
            { username: "bob", points: 300, level: 3 },
            { username: "carol", points: 100, level: 1 },
        ];
        UIService.renderLeaderboard(data, "bob");
        const rows = document.querySelectorAll("#leaderboard-rows tr");
        expect(rows.length).toBe(3);
    });

    it("highlights current user row with current-user-row class", () => {
        const data = [
            { username: "alice", points: 500, level: 5 },
            { username: "bob", points: 300, level: 3 },
        ];
        UIService.renderLeaderboard(data, "bob");
        const rows = document.querySelectorAll("#leaderboard-rows tr");
        expect(rows[1].classList.contains("current-user-row")).toBe(true);
    });

    it("uses medal emoji for top 3 positions", () => {
        const data = [
            { username: "a", points: 100, level: 1 },
            { username: "b", points: 90, level: 1 },
            { username: "c", points: 80, level: 1 },
        ];
        UIService.renderLeaderboard(data, "");
        const rows = document.querySelectorAll("#leaderboard-rows tr");
        expect(rows[0].textContent).toContain("🥇");
        expect(rows[1].textContent).toContain("🥈");
        expect(rows[2].textContent).toContain("🥉");
    });

    it("escapes XSS in usernames", () => {
        const data = [
            { username: "<script>alert(1)</script>", points: 999, level: 9 },
        ];
        UIService.renderLeaderboard(data, "");
        const tbody = document.getElementById("leaderboard-rows");
        expect(tbody.innerHTML).not.toContain("<script>");
    });

    it("shows empty state when leaderboard is empty", () => {
        UIService.renderLeaderboard([], "");
        const tbody = document.getElementById("leaderboard-rows");
        expect(tbody.textContent).toContain("No entries on the leaderboard yet.");
    });
});
