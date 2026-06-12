// Chart.js wrapper configuration for Carbifyio

let emissionsChartInstance = null;

export const ChartsService = {
    // Render or update emissions chart
    renderEmissionsChart(data) {
        const ctx = document.getElementById("emissionsChart");
        const placeholder = document.getElementById("chart-placeholder");
        
        if (!ctx) return;
        
        // Sum values to check if there is data
        const total = (data.energy || 0) + (data.transport || 0) + (data.food || 0) + (data.waste || 0);
        
        if (total === 0) {
            ctx.classList.add("hidden");
            placeholder.classList.remove("hidden");
            return;
        }
        
        ctx.classList.remove("hidden");
        placeholder.classList.add("hidden");
        
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

        // ── WCAG 1.1.1 screen-reader fallback table population ──────────────────
        const tableBody = document.getElementById("emissions-chart-table-body");
        const summaryText = document.getElementById("emissions-chart-summary");
        if (tableBody && summaryText) {
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
        }
    },

    // Destroy chart instance (e.g. on logout)
    destroyChart() {
        if (emissionsChartInstance) {
            emissionsChartInstance.destroy();
            emissionsChartInstance = null;
        }
    }
};
