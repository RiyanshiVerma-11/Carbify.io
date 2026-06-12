// Main App Router & Orchestrator for Carbifyio SPA
import { AuthService } from "./auth.js";
import { CalculatorService } from "./calculator.js";
import { HabitsService } from "./habits.js";
import { ChartsService } from "./charts.js";
import { UIService } from "./ui.js";

const BASE_URL = "/api";

document.addEventListener("DOMContentLoaded", () => {
    // Initial State Check
    initializeTheme();
    checkAuthStatus();
    setupEventBindings();
    
    // Dynamically fetch calculation factors on loading
    CalculatorService.fetchConstants();
});

// 1. Theme Configuration
function initializeTheme() {
    const savedTheme = localStorage.getItem("carbify_theme") || "dark";
    const body = document.body;
    const themeIcon = document.getElementById("theme-icon");

    if (savedTheme === "light") {
        body.classList.remove("dark-theme");
        body.classList.add("light-theme");
        if (themeIcon) themeIcon.textContent = "🌙";
    } else {
        body.classList.remove("light-theme");
        body.classList.add("dark-theme");
        if (themeIcon) themeIcon.textContent = "☀️";
    }
}

function toggleTheme() {
    const body = document.body;
    const themeIcon = document.getElementById("theme-icon");
    let targetTheme = "dark";

    if (body.classList.contains("dark-theme")) {
        body.classList.remove("dark-theme");
        body.classList.add("light-theme");
        if (themeIcon) themeIcon.textContent = "🌙";
        targetTheme = "light";
    } else {
        body.classList.remove("light-theme");
        body.classList.add("dark-theme");
        if (themeIcon) themeIcon.textContent = "☀️";
    }

    localStorage.setItem("carbify_theme", targetTheme);
    
    // If chart exists, re-draw it to update label colors
    const activeView = document.querySelector(".view-panel:not(.hidden)");
    if (activeView && activeView.id === "dashboard-view" && AuthService.isAuthenticated()) {
        loadDashboardData();
    }
}

// 2. Authentication Status Router
async function checkAuthStatus() {
    const navList = document.getElementById("nav-list");
    const authBtn = document.getElementById("auth-action-btn");
    
    if (AuthService.isAuthenticated()) {
        // Show Navigation options
        if (navList) navList.classList.remove("hidden");
        if (authBtn) {
            authBtn.textContent = "Sign Out";
            authBtn.className = "btn btn-secondary";
        }
        
        try {
            // Validate session and cache
            const profile = await AuthService.fetchProfile();
            updateHeaderStats(profile);
            UIService.switchView("dashboard-view");
            loadDashboardData();
        } catch (error) {
            UIService.showToast("Session expired. Please log in again.", "error");
            forceSignOut();
        }
    } else {
        // Hide Navigation details
        if (navList) navList.classList.add("hidden");
        if (authBtn) {
            authBtn.textContent = "Login / Register";
            authBtn.className = "btn btn-primary";
        }
        UIService.switchView("auth-view");
        ChartsService.destroyChart();
    }
}

function updateHeaderStats(user) {
    if (!user) return;
    const dashUser = document.getElementById("dash-username");
    const dashLevel = document.getElementById("dash-level");
    const dashPoints = document.getElementById("dash-points");
    
    if (dashUser) dashUser.textContent = user.username;
    if (dashLevel) dashLevel.textContent = user.level;
    if (dashPoints) dashPoints.textContent = user.points;
}

function forceSignOut() {
    AuthService.clearSession();
    ChartsService.destroyChart();
    checkAuthStatus();
}

// 3. Event Listeners Setup
function setupEventBindings() {
    // Theme Switcher Click
    const themeToggle = document.getElementById("theme-toggle");
    if (themeToggle) {
        themeToggle.addEventListener("click", toggleTheme);
    }

    // Auth Action (Logout / Login Redirect)
    const authBtn = document.getElementById("auth-action-btn");
    if (authBtn) {
        authBtn.addEventListener("click", () => {
            if (AuthService.isAuthenticated()) {
                forceSignOut();
                UIService.showToast("Signed out successfully.");
            } else {
                UIService.switchView("auth-view");
            }
        });
    }

    // Navigation Switches
    const navButtons = document.querySelectorAll(".nav-btn");
    navButtons.forEach(btn => {
        btn.addEventListener("click", (e) => {
            const target = e.target.getAttribute("data-target");
            UIService.switchView(target);
            loadViewData(target);
        });
    });

    // Login/Register tabs switches
    const tabLogin = document.getElementById("tab-login");
    const tabRegister = document.getElementById("tab-register");
    const loginForm = document.getElementById("login-form-container");
    const regForm = document.getElementById("register-form-container");

    if (tabLogin && tabRegister) {
        tabLogin.addEventListener("click", () => {
            tabLogin.classList.add("active");
            tabLogin.setAttribute("aria-selected", "true");
            tabRegister.classList.remove("active");
            tabRegister.setAttribute("aria-selected", "false");
            loginForm.classList.remove("hidden");
            regForm.classList.add("hidden");
        });

        tabRegister.addEventListener("click", () => {
            tabRegister.classList.add("active");
            tabRegister.setAttribute("aria-selected", "true");
            tabLogin.classList.remove("active");
            tabLogin.setAttribute("aria-selected", "false");
            regForm.classList.remove("hidden");
            loginForm.classList.add("hidden");
        });
    }

    // Submit Forms
    const formLogin = document.getElementById("login-form");
    if (formLogin) {
        formLogin.addEventListener("submit", async (e) => {
            e.preventDefault();
            const username = formLogin.username.value.trim();
            const password = formLogin.password.value;

            try {
                const user = await AuthService.login(username, password);
                UIService.showToast(`Welcome back, ${user.username}!`);
                formLogin.reset();
                checkAuthStatus();
            } catch (err) {
                UIService.showToast(err.message, "error");
            }
        });
    }

    const formReg = document.getElementById("register-form");
    if (formReg) {
        formReg.addEventListener("submit", async (e) => {
            e.preventDefault();
            const username = formReg.username.value.trim();
            const email = formReg.email.value.trim();
            const password = formReg.password.value;

            try {
                await AuthService.register(username, email, password);
                UIService.showToast("Registration successful! Please sign in.");
                formReg.reset();
                tabLogin.click();
            } catch (err) {
                UIService.showToast(err.message, "error");
            }
        });
    }

    // Calculator Live updates
    const calcForm = document.getElementById("calculator-form");
    if (calcForm) {
        const inputs = calcForm.querySelectorAll("input, select");
        inputs.forEach(input => {
            input.addEventListener("input", updateLiveCarbonPreview);
        });

        // Recycling percentage label helper
        const recyclingInput = document.getElementById("calc-recycling");
        if (recyclingInput) {
            recyclingInput.addEventListener("input", (e) => {
                const val = Math.round(parseFloat(e.target.value) * 100);
                document.getElementById("recycling-percentage").textContent = val;
                recyclingInput.setAttribute("aria-valuenow", val);
            });
        }

        calcForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const payload = CalculatorService.getCalculatorInputs(calcForm);

            try {
                await CalculatorService.logEmissions(payload);
                UIService.showToast("Emissions logged successfully!");
                calcForm.reset();
                document.getElementById("recycling-percentage").textContent = "0";
                // Go to dashboard
                document.getElementById("nav-dashboard").click();
            } catch (err) {
                UIService.showToast(err.message, "error");
            }
        });
    }

    // Habits logger clicks
    const habitsList = document.getElementById("habits-list");
    if (habitsList) {
        habitsList.addEventListener("click", async (e) => {
            if (e.target.tagName === "BUTTON") {
                const habitKey = e.target.getAttribute("data-habit");
                try {
                    const result = await HabitsService.logHabit(habitKey);
                    UIService.showToast(`Logged successfully! +${result.points_earned} Eco-points, -${result.co2_saved_kg}kg CO₂!`);
                    
                    // Refresh Profile cached values & stats
                    const profile = await AuthService.fetchProfile();
                    updateHeaderStats(profile);
                    loadHabitsData();
                } catch (err) {
                    UIService.showToast(err.message, "error");
                }
            }
        });
    }

    // Challenges list clicks (Accept & Complete buttons)
    const challengesGrid = document.getElementById("available-challenges");
    const joinedGrid = document.getElementById("joined-challenges");

    if (challengesGrid) {
        challengesGrid.addEventListener("click", async (e) => {
            if (e.target.classList.contains("join-challenge-btn")) {
                const id = e.target.getAttribute("data-id");
                try {
                    await HabitsService.joinChallenge(id);
                    UIService.showToast("Challenge accepted! Good luck.");
                    loadChallengesData();
                } catch (err) {
                    UIService.showToast(err.message, "error");
                }
            }
        });
    }

    if (joinedGrid) {
        joinedGrid.addEventListener("click", async (e) => {
            if (e.target.classList.contains("complete-challenge-btn")) {
                const id = e.target.getAttribute("data-id");
                try {
                    await HabitsService.completeChallenge(id);
                    UIService.showToast("Outstanding! Challenge completed! Points awarded.");
                    const profile = await AuthService.fetchProfile();
                    updateHeaderStats(profile);
                    loadChallengesData();
                } catch (err) {
                    UIService.showToast(err.message, "error");
                }
            }
        });
    }
}

// 4. View Loader Bindings
function loadViewData(viewId) {
    if (!AuthService.isAuthenticated()) return;
    
    switch (viewId) {
        case "dashboard-view":
            loadDashboardData();
            break;
        case "calculator-view":
            loadCalculatorData();
            break;
        case "habits-view":
            loadHabitsData();
            break;
        case "challenges-view":
            loadChallengesData();
            break;
        case "leaderboard-view":
            loadLeaderboardData();
            break;
    }
}

// Dashboard statistics
async function loadDashboardData() {
    try {
        const response = await fetch(`${BASE_URL}/analytics`, {
            headers: AuthService.getAuthHeaders()
        });
        const analytics = await response.json();
        
        if (response.ok) {
            // Update Dashboard values
            document.getElementById("dash-total-co2").textContent = analytics.total_co2_kg;
            document.getElementById("dash-saved-co2").textContent = analytics.carbon_saved_kg;
            
            const comment = document.getElementById("dash-co2-comment");
            if (comment) {
                if (analytics.total_co2_kg === 0) {
                    comment.textContent = "Log calculations to assess status.";
                } else if (analytics.total_co2_kg < 8.0) {
                    comment.textContent = "Super low footprint! Excellent job!";
                } else if (analytics.total_co2_kg < 15.0) {
                    comment.textContent = "Average footprint. Try logging daily habits to reduce.";
                } else {
                    comment.textContent = "High emissions footprint. Follow Coach suggestions!";
                }
            }
            
            // Draw chart
            ChartsService.renderEmissionsChart(analytics.weekly_breakdown);
            
            // Render tips
            UIService.renderCoachTips(analytics.ai_coach_tips);
        }
    } catch (err) {
        console.error("Dashboard data load error:", err);
    }
}

// Pre-fill calculator with latest data
async function loadCalculatorData() {
    try {
        const latest = await CalculatorService.getLatest();
        const form = document.getElementById("calculator-form");
        if (form && latest) {
            form.electricity_kwh.value = latest.electricity_kwh;
            form.gas_kwh.value = latest.gas_kwh;
            form.petrol_car_km.value = latest.petrol_car_km;
            form.diesel_car_km.value = latest.diesel_car_km;
            form.electric_car_km.value = latest.electric_car_km;
            form.public_transit_km.value = latest.public_transit_km;
            form.flights_km.value = latest.flights_km;
            form.diet_type.value = latest.diet_type;
            form.waste_kg.value = latest.waste_kg;
            form.recycling_rate.value = latest.recycling_rate;
            
            const recyclingVal = Math.round(latest.recycling_rate * 100);
            document.getElementById("recycling-percentage").textContent = recyclingVal;
            const recyclingInput = document.getElementById("calc-recycling");
            if (recyclingInput) {
                recyclingInput.setAttribute("aria-valuenow", recyclingVal);
            }
            updateLiveCarbonPreview();
        }
    } catch (err) {
        console.error("Calculator pre-fill error:", err);
    }
}

// Dynamic local calculation preview
function updateLiveCarbonPreview() {
    const form = document.getElementById("calculator-form");
    if (!form) return;
    
    const inputs = CalculatorService.getCalculatorInputs(form);
    
    const estimate = CalculatorService.calculateLive(inputs);
    const label = document.getElementById("live-carbon-preview");
    if (label) label.textContent = estimate;
}

// Habits Loader
async function loadHabitsData() {
    try {
        const habits = await HabitsService.getAvailableHabits();
        UIService.renderHabitsList(habits);
        
        const history = await HabitsService.getHistory();
        UIService.renderHabitHistory(history);
    } catch (err) {
        console.error("Habits data error:", err);
    }
}

// Challenges Loader
async function loadChallengesData() {
    try {
        const challenges = await HabitsService.getChallenges();
        const userChallenges = await HabitsService.getUserChallenges();
        UIService.renderChallenges(challenges, userChallenges);
    } catch (err) {
        console.error("Challenges data error:", err);
    }
}

// Leaderboard Loader
async function loadLeaderboardData() {
    try {
        const response = await fetch(`${BASE_URL}/analytics/leaderboard`, {
            headers: AuthService.getAuthHeaders()
        });
        const leaderboardData = await response.json();
        
        if (response.ok) {
            const user = AuthService.getLocalUser();
            const currentUsername = user ? user.username : "";
            
            document.getElementById("lead-user-rank").textContent = leaderboardData.user_rank;
            document.getElementById("lead-user-points").textContent = leaderboardData.user_points;
            
            UIService.renderLeaderboard(leaderboardData.leaderboard, currentUsername);
        }
    } catch (err) {
        console.error("Leaderboard data error:", err);
    }
}
