// UI & Rendering Helper Module for Carbifyio

export const UIService = {
    // Helper to escape HTML characters and prevent XSS
    escapeHtml(text) {
        if (!text) return "";
        const div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    },

    // Show dynamic toast notifications
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

    // Handle view switches in single page application
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

    // Render AI Coach suggestions
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

        tips.forEach(tip => {
            const card = document.createElement("div");
            card.className = `coach-tip-card ${tip.impact.toLowerCase() === "high" ? "high-impact" : ""}`;

            const iconMap = {
                "transport": "🚗",
                "energy": "💡",
                "food": "🥗",
                "waste": "♻️",
                "general": "🌱"
            };
            const icon = iconMap[tip.category] || "🌱";

            card.innerHTML = `
                <div class="coach-tip-icon" aria-hidden="true">${icon}</div>
                <div class="coach-tip-body">
                    <div class="coach-tip-header">
                        <span class="tip-title">${tip.category} suggestion</span>
                        <span class="tip-impact ${tip.impact.toLowerCase()}">${tip.impact} Impact</span>
                    </div>
                    <p class="tip-text">${tip.message}</p>
                </div>
            `;
            container.appendChild(card);
        });
    },

    // Render Habits Logger UI lists
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
            
            const card = document.createElement("div");
            card.className = "habit-card";
            card.innerHTML = `
                <div>
                    <div class="habit-icon-circle" aria-hidden="true">${icon}</div>
                    <div class="habit-details">
                        <h4>${h.name}</h4>
                        <div class="habit-rewards">
                            <span class="reward-tag points">+${h.points} pts</span>
                            <span class="reward-tag co2">-${h.co2_saved} kg CO₂</span>
                        </div>
                    </div>
                </div>
                <button class="btn btn-primary btn-small mt-2" data-habit="${key}">Log Habit</button>
            `;
            container.appendChild(card);
        });
    },

    // Render habits history logs
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
            const displayName = habitNameMap[item.habit_name] || item.habit_name;

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

    // Render active and available challenges
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
            
            if (status === "active") {
                activeJoinedCount++;
                const card = document.createElement("div");
                card.className = "challenge-card joined";
                card.innerHTML = `
                    <div>
                        <div class="challenge-header">
                            <span class="challenge-category">${c.category}</span>
                            <span class="challenge-duration">${c.duration_days} days</span>
                        </div>
                        <h4 class="challenge-title">${c.title}</h4>
                        <p class="challenge-desc">${c.description}</p>
                        <div class="challenge-rewards">
                            <span class="reward-tag points">+${c.points_reward} pts</span>
                            <span class="reward-tag co2">-${c.co2_saving_estimate_kg} kg CO₂</span>
                        </div>
                    </div>
                    <button class="btn btn-primary btn-small complete-challenge-btn" data-id="${c.id}">Complete Challenge</button>
                `;
                joinedContainer.appendChild(card);
            } else if (status === "completed") {
                // Ignore or show inside historical log if needed, let's keep joined challenges clean
            } else {
                availableCount++;
                const card = document.createElement("div");
                card.className = "challenge-card";
                card.innerHTML = `
                    <div>
                        <div class="challenge-header">
                            <span class="challenge-category">${c.category}</span>
                            <span class="challenge-duration">${c.duration_days} days</span>
                        </div>
                        <h4 class="challenge-title">${c.title}</h4>
                        <p class="challenge-desc">${c.description}</p>
                        <div class="challenge-rewards">
                            <span class="reward-tag points">+${c.points_reward} pts</span>
                            <span class="reward-tag co2">-${c.co2_saving_estimate_kg} kg CO₂</span>
                        </div>
                    </div>
                    <button class="btn btn-secondary btn-small join-challenge-btn" data-id="${c.id}">Accept Challenge</button>
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

    // Render leaderboard entries
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
