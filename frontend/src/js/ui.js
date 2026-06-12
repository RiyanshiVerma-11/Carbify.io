/**
 * @file ui.js
 * @description UI rendering helpers for Carbifyio — manages view switching,
 *              toast notifications, and dynamic DOM population for habits,
 *              challenges, leaderboard, and AI Coach tips.
 *
 * All user-supplied strings are sanitised via {@link escapeHtml} before
 * insertion into the DOM to prevent XSS.
 */

/**
 * UI rendering and layout management service.
 * @namespace UIService
 */
export const UIService = {
    /**
     * Escape HTML special characters to prevent XSS injection.
     * @param {string} text - Raw text to sanitise.
     * @returns {string} HTML-safe string.
     */
    escapeHtml(text) {
        if (text === null || text === undefined) return "";
        return String(text)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    },

    /**
     * Display a transient toast notification at the bottom-right of the viewport.
     * @param {string} message - Notification message text.
     * @param {"success"|"error"} [type="success"] - Visual style of the toast.
     */
    showToast(message, type = "success") {
        const container = document.getElementById("toast-container");
        if (!container) return;

        const toast = document.createElement("div");
        toast.className = `toast ${type === "error" ? "error" : ""}`;
        toast.setAttribute("role", "alert");

        const msgSpan = document.createElement("span");
        msgSpan.textContent = message;

        const closeBtn = document.createElement("button");
        closeBtn.className = "toast-close";
        closeBtn.innerHTML = "&times;";
        closeBtn.setAttribute("aria-label", "Close notification");
        closeBtn.onclick = () => toast.remove();

        toast.appendChild(msgSpan);
        toast.appendChild(closeBtn);
        container.appendChild(toast);

        // Auto-remove after 4 seconds
        setTimeout(() => {
            if (toast.parentElement) {
                toast.style.animation = "fadeIn 0.3s ease reverse";
                setTimeout(() => toast.remove(), 300);
            }
        }, 4000);
    },

    /**
     * Switch the visible view panel in the single-page application.
     * Updates navigation button active states and focuses the first
     * heading for screen-reader announcements.
     * @param {string} targetViewId - The `id` of the view panel to display.
     */
    switchView(targetViewId) {
        const views = document.querySelectorAll(".view-panel");
        views.forEach(view => {
            if (view.id === targetViewId) {
                view.classList.remove("hidden");
                // Focus container or header for screen reader support
                const firstHeader = view.querySelector("h2");
                if (firstHeader) firstHeader.setAttribute("tabindex", "-1");
                if (firstHeader) firstHeader.focus();
            } else {
                view.classList.add("hidden");
            }
        });

        // Set navigation buttons active states
        const navBtns = document.querySelectorAll(".nav-btn");
        navBtns.forEach(btn => {
            if (btn.getAttribute("data-target") === targetViewId) {
                btn.classList.add("active");
                btn.setAttribute("aria-current", "page");
            } else {
                btn.classList.remove("active");
                btn.removeAttribute("aria-current");
            }
        });
    },

    /**
     * Render AI Coach suggestion cards into the tips container.
     *
     * All dynamic strings (category, impact, message) are sanitised via
     * {@link escapeHtml} to prevent XSS.
     *
     * @param {Array<Object>} tips - Array of tip objects from the analytics API.
     */
    renderCoachTips(tips) {
        const container = document.getElementById("ai-coach-tips-container");
        if (!container) return;

        container.innerHTML = "";

        if (tips.length === 0) {
            container.innerHTML = `
                <div class="history-placeholder">
                    No suggestions available yet. Log your metrics in the Calculator!
                </div>`;
            return;
        }

        const iconMap = {
            "transport": "🚗",
            "energy": "💡",
            "food": "🥗",
            "waste": "♻️",
            "general": "🌱"
        };

        tips.forEach(tip => {
            const card = document.createElement("div");
            const impactLower = (tip.impact || "").toLowerCase();
            card.className = `coach-tip-card ${impactLower === "high" ? "high-impact" : ""}`;

            const icon = iconMap[tip.category] || "🌱";

            // Sanitise all dynamic strings before DOM insertion
            const safeCategory = UIService.escapeHtml(tip.category);
            const safeImpact = UIService.escapeHtml(tip.impact);
            const safeMessage = UIService.escapeHtml(tip.message);

            card.innerHTML = `
                <div class="coach-tip-icon" aria-hidden="true">${icon}</div>
                <div class="coach-tip-body">
                    <div class="coach-tip-header">
                        <span class="tip-title">${safeCategory} suggestion</span>
                        <span class="tip-impact ${impactLower}">${safeImpact} Impact</span>
                    </div>
                    <p class="tip-text">${safeMessage}</p>
                </div>
            `;
            container.appendChild(card);
        });
    },

    /**
     * Render the habit catalogue as interactive cards with "Log Habit" buttons.
     * @param {Object} habits - Habit catalogue keyed by slug.
     */
    renderHabitsList(habits) {
        const container = document.getElementById("habits-list");
        if (!container) return;

        container.innerHTML = "";

        const iconMap = {
            "walk_instead_of_drive": "🚶",
            "turn_off_ac": "❄️",
            "plant_based_day": "🥦",
            "recycle_bottles": "♻️",
            "short_shower": "🚿",
            "air_dry_clothes": "☀️",
            "unplug_idle": "🔌"
        };

        Object.keys(habits).forEach(key => {
            const h = habits[key];
            const icon = iconMap[key] || "🌱";
            const safeName = UIService.escapeHtml(h.name);
            
            const card = document.createElement("div");
            card.className = "habit-card";
            card.innerHTML = `
                <div>
                    <div class="habit-icon-circle" aria-hidden="true">${icon}</div>
                    <div class="habit-details">
                        <h4>${safeName}</h4>
                        <div class="habit-rewards">
                            <span class="reward-tag points">+${h.points} pts</span>
                            <span class="reward-tag co2">-${h.co2_saved} kg CO₂</span>
                        </div>
                    </div>
                </div>
                <button class="btn btn-primary btn-small mt-2" data-habit="${UIService.escapeHtml(key)}" aria-label="Log habit: ${safeName}">Log Habit</button>
            `;
            container.appendChild(card);
        });
    },

    /**
     * Render the habit log history as a chronological list.
     * @param {Array<Object>} history - Array of habit log entries from the API.
     */
    renderHabitHistory(history) {
        const container = document.getElementById("habits-history");
        if (!container) return;

        container.innerHTML = "";

        if (history.length === 0) {
            container.innerHTML = `<li class="history-placeholder">No habits logged today. Start logging habits to earn points!</li>`;
            return;
        }

        const habitNameMap = {
            "walk_instead_of_drive": "Walked/cycled instead of driving",
            "turn_off_ac": "Turned off AC/heating when away",
            "plant_based_day": "Ate fully plant-based today",
            "recycle_bottles": "Sorted and recycled waste",
            "short_shower": "Took a short shower (< 5 mins)",
            "air_dry_clothes": "Air-dried laundry",
            "unplug_idle": "Unplugged idle electronics"
        };

        history.forEach(item => {
            const li = document.createElement("li");
            li.className = "history-item";
            
            const dateObj = new Date(item.logged_date);
            const dateStr = dateObj.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
            const displayName = habitNameMap[item.habit_name] || UIService.escapeHtml(item.habit_name);

            li.innerHTML = `
                <div class="history-item-left">
                    <span class="history-item-name">${displayName}</span>
                    <span class="history-item-date">${dateStr}</span>
                </div>
                <div class="habit-rewards">
                    <span class="reward-tag points">+${item.points_earned} pts</span>
                    <span class="reward-tag co2">-${item.co2_saved_kg} kg CO₂</span>
                </div>
            `;
            container.appendChild(li);
        });
    },

    /**
     * Render active and available challenges into their respective containers.
     * @param {Array<Object>} challenges     - All available challenges.
     * @param {Array<Object>} userChallenges - The current user's enrolments.
     */
    renderChallenges(challenges, userChallenges) {
        const availableContainer = document.getElementById("available-challenges");
        const joinedContainer = document.getElementById("joined-challenges");
        
        if (!availableContainer || !joinedContainer) return;

        availableContainer.innerHTML = "";
        joinedContainer.innerHTML = "";

        const joinedIdsMap = {};
        userChallenges.forEach(uc => {
            joinedIdsMap[uc.challenge_id] = uc.status;
        });

        let availableCount = 0;
        let activeJoinedCount = 0;

        challenges.forEach(c => {
            const status = joinedIdsMap[c.id];
            const safeTitle = UIService.escapeHtml(c.title);
            const safeDesc = UIService.escapeHtml(c.description);
            const safeCategory = UIService.escapeHtml(c.category);
            
            if (status === "active") {
                activeJoinedCount++;
                const card = document.createElement("div");
                card.className = "challenge-card joined";
                card.innerHTML = `
                    <div>
                        <div class="challenge-header">
                            <span class="challenge-category">${safeCategory}</span>
                            <span class="challenge-duration">${c.duration_days} days</span>
                        </div>
                        <h4 class="challenge-title">${safeTitle}</h4>
                        <p class="challenge-desc">${safeDesc}</p>
                        <div class="challenge-rewards">
                            <span class="reward-tag points">+${c.points_reward} pts</span>
                            <span class="reward-tag co2">-${c.co2_saving_estimate_kg} kg CO₂</span>
                        </div>
                    </div>
                    <button class="btn btn-primary btn-small complete-challenge-btn" data-id="${c.id}" aria-label="Complete challenge: ${safeTitle}">Complete Challenge</button>
                `;
                joinedContainer.appendChild(card);
            } else if (status !== "completed") {
                availableCount++;
                const card = document.createElement("div");
                card.className = "challenge-card";
                card.innerHTML = `
                    <div>
                        <div class="challenge-header">
                            <span class="challenge-category">${safeCategory}</span>
                            <span class="challenge-duration">${c.duration_days} days</span>
                        </div>
                        <h4 class="challenge-title">${safeTitle}</h4>
                        <p class="challenge-desc">${safeDesc}</p>
                        <div class="challenge-rewards">
                            <span class="reward-tag points">+${c.points_reward} pts</span>
                            <span class="reward-tag co2">-${c.co2_saving_estimate_kg} kg CO₂</span>
                        </div>
                    </div>
                    <button class="btn btn-secondary btn-small join-challenge-btn" data-id="${c.id}" aria-label="Accept challenge: ${safeTitle}">Accept Challenge</button>
                `;
                availableContainer.appendChild(card);
            }
        });

        if (availableCount === 0) {
            availableContainer.innerHTML = `<div class="history-placeholder">All challenges accepted! Check back tomorrow.</div>`;
        }
        if (activeJoinedCount === 0) {
            joinedContainer.innerHTML = `<div class="history-placeholder">You have no active challenges. Accept one on the left!</div>`;
        }

        // Update active count on dashboard
        const dashActiveBadge = document.getElementById("dash-active-challenges");
        if (dashActiveBadge) {
            dashActiveBadge.textContent = activeJoinedCount;
        }
    },

    /**
     * Render the eco-leaderboard table rows.
     * @param {Array<Object>} leaderboard    - Sorted array of leaderboard entries.
     * @param {string}        currentUsername - The authenticated user's username.
     */
    renderLeaderboard(leaderboard, currentUsername) {
        const tbody = document.getElementById("leaderboard-rows");
        if (!tbody) return;

        tbody.innerHTML = "";

        if (leaderboard.length === 0) {
            tbody.innerHTML = `<tr><td colspan="4" class="text-center text-muted">No entries on the leaderboard yet.</td></tr>`;
            return;
        }

        leaderboard.forEach((user, index) => {
            const tr = document.createElement("tr");
            if (user.username === currentUsername) {
                tr.className = "current-user-row";
            }

            let rankEmoji = `#${index + 1}`;
            if (index === 0) rankEmoji = "🥇 1";
            else if (index === 1) rankEmoji = "🥈 2";
            else if (index === 2) rankEmoji = "🥉 3";

            const escapedUsername = UIService.escapeHtml(user.username);
            const isSelf = user.username === currentUsername;
            tr.innerHTML = `
                <td>${rankEmoji}</td>
                <td>${escapedUsername}${isSelf ? ' (You)' : ''}</td>
                <td>Level ${user.level}</td>
                <td>${user.points} pts</td>
            `;
            tbody.appendChild(tr);
        });
    }
};
