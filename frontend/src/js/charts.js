/**
 * @file charts.js
 * @description Chart.js wrapper for rendering and updating the emissions
 *              breakdown doughnut chart and the 14-day historical trend
 *              line chart. Includes WCAG 1.1.1 compliant screen-reader
 *              fallback data tables for both charts.
 */

/** @type {Chart|null} Singleton Chart.js instance for the doughnut chart. */
let emissionsChartInstance = null;

/** @type {Chart|null} Singleton Chart.js instance for the trend line chart. */
let trendChartInstance = null;

/**
 * Chart rendering and lifecycle management service.
 * @namespace ChartsService
 */
export const ChartsService = {
    /**
     * Render or update the emissions breakdown doughnut chart.
     *
     * When total emissions are zero, the chart canvas is hidden and a
     * placeholder message is shown instead.  A screen-reader-only data
     * table is populated in parallel (WCAG 1.1.1).
     *
     * @param {Object} data - Breakdown values: { energy, transport, food, waste }.
     */
    renderEmissionsChart(data) {
        const ctx = document.getElementById("emissionsChart");
        const placeholder = document.getElementById("chart-placeholder");
        
        if (!ctx) {
            return;
        }
        
        // Sum values to check if there is data
        const total = (data.energy || 0) + (data.transport || 0) + (data.food || 0) + (data.waste || 0);
        
        if (total === 0) {
            ctx.classList.add("hidden");
            if (placeholder) {
                placeholder.classList.remove("hidden");
            }
            return;
        }
        
        ctx.classList.remove("hidden");
        if (placeholder) {
            placeholder.classList.add("hidden");
        }
        
        const chartData = {
            labels: ['Energy', 'Transport', 'Food', 'Waste'],
            datasets: [{
                data: [data.energy || 0, data.transport || 0, data.food || 0, data.waste || 0],
                backgroundColor: [
                    '#3b82f6', // Ocean Blue (Energy)
                    '#10b981', // Forest Green (Transport)
                    '#eab308', // Yellow (Food)
                    '#ef4444'  // Red (Waste)
                ],
                borderWidth: 1,
                borderColor: 'rgba(255,255,255,0.1)'
            }]
        };

        const config = {
            type: 'doughnut',
            data: chartData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: document.body.classList.contains("light-theme") ? "#0f172a" : "#f8fafc",
                            font: {
                                family: 'Outfit',
                                size: 12
                            }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return ` ${context.label}: ${context.raw} kg CO₂`;
                            }
                        }
                    }
                },
                cutout: '60%'
            }
        };

        // If instance exists, update it. Else create new
        if (emissionsChartInstance) {
            emissionsChartInstance.data.datasets[0].data = chartData.datasets[0].data;
            emissionsChartInstance.options.plugins.legend.labels.color = config.options.plugins.legend.labels.color;
            emissionsChartInstance.update();
        } else {
            emissionsChartInstance = new Chart(ctx, config);
        }

        // ── WCAG 1.1.1 screen-reader fallback table population ──────────────
        this._updateScreenReaderTable(data);
    },

    /**
     * Populate the visually-hidden screen-reader data table with current
     * emissions data (WCAG 1.1.1 non-text-content alternative).
     * @param {Object} data - Breakdown values: { energy, transport, food, waste }.
     * @private
     */
    _updateScreenReaderTable(data) {
        const tableBody = document.getElementById("emissions-chart-table-body");
        const summaryText = document.getElementById("emissions-chart-summary");
        if (!tableBody || !summaryText) {
            return;
        }

        tableBody.innerHTML = "";
        const categories = ['Energy', 'Transport', 'Food', 'Waste'];
        const values = [data.energy || 0, data.transport || 0, data.food || 0, data.waste || 0];
        const valTotal = values.reduce((a, b) => a + b, 0);

        categories.forEach((cat, index) => {
            const val = values[index];
            const pct = valTotal > 0 ? ((val / valTotal) * 100).toFixed(1) : "0.0";
            
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td>${cat}</td>
                <td>${val.toFixed(2)} kg CO₂e</td>
                <td>${pct}%</td>
            `;
            tableBody.appendChild(tr);
        });

        // Update live-announcement text
        summaryText.textContent = `Carbon footprint breakdown: ${categories.map((cat, idx) => {
            const pct = valTotal > 0 ? ((values[idx] / valTotal) * 100).toFixed(1) : "0.0";
            return `${cat}: ${values[idx].toFixed(2)} kg (${pct}%)`;
        }).join(', ')}. Total emissions logged: ${valTotal.toFixed(2)} kg CO₂e.`;
    },

    /**
     * Render or update the 14-day historical CO₂ trend line chart.
     *
     * Renders a gradient-filled area line chart using the gapless daily
     * series returned by GET /api/analytics/trend. A screen-reader-only
     * summary table is populated in parallel (WCAG 1.1.1).
     *
     * @param {Array<{date: string, total_co2_kg: number}>} trendData - Ordered daily series.
     */
    renderTrendChart(trendData) {
        const ctx = document.getElementById("trendChart");
        if (!ctx) {
            return;
        }

        const isLight = document.body.classList.contains("light-theme");
        const textColor = isLight ? "#334155" : "#94a3b8";
        const gridColor = isLight ? "rgba(0,0,0,0.08)" : "rgba(255,255,255,0.06)";
        const accentColor = "#10b981";

        const labels = trendData.map(d => {
            const date = new Date(d.date);
            return date.toLocaleDateString("en-GB", { month: "short", day: "numeric" });
        });
        const values = trendData.map(d => d.total_co2_kg);

        const config = {
            type: "line",
            data: {
                labels,
                datasets: [{
                    label: "Daily CO₂ (kg)",
                    data: values,
                    borderColor: accentColor,
                    borderWidth: 2.5,
                    pointBackgroundColor: accentColor,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    tension: 0.4,
                    fill: true,
                    backgroundColor: (context) => {
                        const chart = context.chart;
                        const { ctx: canvasCtx, chartArea } = chart;
                        if (!chartArea) {
                            return "rgba(16,185,129,0.0)";
                        }
                        const gradient = canvasCtx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
                        gradient.addColorStop(0, "rgba(16,185,129,0.25)");
                        gradient.addColorStop(1, "rgba(16,185,129,0.01)");
                        return gradient;
                    },
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: "index", intersect: false },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (tooltipItem) => ` ${tooltipItem.parsed.y.toFixed(2)} kg CO₂`,
                        }
                    }
                },
                scales: {
                    x: {
                        ticks: { color: textColor, font: { family: "Outfit", size: 11 } },
                        grid: { color: gridColor },
                    },
                    y: {
                        beginAtZero: true,
                        ticks: {
                            color: textColor,
                            font: { family: "Outfit", size: 11 },
                            callback: (val) => `${val} kg`,
                        },
                        grid: { color: gridColor },
                    }
                }
            }
        };

        if (trendChartInstance) {
            trendChartInstance.data.labels = labels;
            trendChartInstance.data.datasets[0].data = values;
            trendChartInstance.update();
        } else {
            trendChartInstance = new Chart(ctx, config);
        }

        // ── WCAG 1.1.1 screen-reader fallback for trend chart ───────────────
        this._updateTrendScreenReaderTable(trendData);
    },

    /**
     * Populate the sr-only trend data table for screen reader accessibility.
     * @param {Array<{date: string, total_co2_kg: number}>} trendData
     * @private
     */
    _updateTrendScreenReaderTable(trendData) {
        const tableBody = document.getElementById("trend-chart-table-body");
        const summaryEl = document.getElementById("trend-chart-summary");
        if (!tableBody) {
            return;
        }

        tableBody.innerHTML = "";
        const nonZero = trendData.filter(d => d.total_co2_kg > 0);
        const avg = nonZero.length > 0
            ? (nonZero.reduce((s, d) => s + d.total_co2_kg, 0) / nonZero.length).toFixed(2)
            : "0.00";

        trendData.forEach(point => {
            const tr = document.createElement("tr");
            tr.innerHTML = `<td>${point.date}</td><td>${point.total_co2_kg.toFixed(2)} kg CO₂</td>`;
            tableBody.appendChild(tr);
        });

        if (summaryEl) {
            summaryEl.textContent = `14-day CO₂ trend. Days with data: ${nonZero.length}. Average on active days: ${avg} kg CO₂.`;
        }
    },

    /**
     * Destroy the doughnut chart instance (e.g. on logout) to free canvas resources.
     */
    destroyChart() {
        if (emissionsChartInstance) {
            emissionsChartInstance.destroy();
            emissionsChartInstance = null;
        }
        if (trendChartInstance) {
            trendChartInstance.destroy();
            trendChartInstance = null;
        }
    }
};

