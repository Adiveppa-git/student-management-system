// PART 2: AI Dashboard & Model Metrics Loader
// =========================================================================
async function loadAIDashboard() {
    const loading = document.getElementById("dashboardLoading");
    const error = document.getElementById("dashboardError");
    const content = document.getElementById("dashboardContent");

    loading.style.display = "block";
    error.style.display = "none";
    content.style.display = "none";

    try {
        // Fetch health and metrics concurrently
        const [healthRes, metricsRes] = await Promise.all([
            fetch(AI_HEALTH_API),
            fetch(AI_METRICS_API)
        ]);

        if (!healthRes.ok || !metricsRes.ok) {
            throw new Error(`AI service responded with HTTP status (Health: ${healthRes.status}, Metrics: ${metricsRes.status}). Ensure backend is running.`);
        }

        const health = await healthRes.json();
        const metrics = await metricsRes.json();

        // Populate Health info
        const healthBadge = document.getElementById("healthBadge");
        const healthText = document.getElementById("healthText");
        const healthModelType = document.getElementById("healthModelType");
        const featuresCount = document.getElementById("featuresCount");

        if (health.status === "healthy") {
            healthBadge.className = "status-badge healthy";
            healthText.textContent = "Operational";
        } else {
            healthBadge.className = "status-badge unavailable";
            healthText.textContent = "Degraded";
        }

        healthModelType.textContent = `${health.model_type || "ML Model"} (${metrics.model_name || ""})`;
        featuresCount.textContent = health.features_count || 31;

        // Populate Test Metrics
        const tm = metrics.test_metrics || {};
        document.getElementById("metricAccuracy").textContent = tm.accuracy ? `${(tm.accuracy * 100).toFixed(1)}%` : "--";
        document.getElementById("metricRecall").textContent = tm.recall ? `${(tm.recall * 100).toFixed(1)}%` : "--";
        document.getElementById("metricPrecision").textContent = tm.precision ? `${(tm.precision * 100).toFixed(1)}%` : "--";
        document.getElementById("metricF1").textContent = tm.f1_score ? `${(tm.f1_score * 100).toFixed(1)}%` : "--";
        document.getElementById("metricRocAuc").textContent = tm.roc_auc ? `${(tm.roc_auc * 100).toFixed(1)}%` : "--";

        // Confusion Matrix
        if (tm.confusion_matrix) {
            const cm = tm.confusion_matrix;
            document.getElementById("cmTN").innerHTML = `${cm.true_negatives}<br><small>(True Neg)</small>`;
            document.getElementById("cmFP").innerHTML = `${cm.false_positives}<br><small>(False Pos)</small>`;
            document.getElementById("cmFN").innerHTML = `${cm.false_negatives}<br><small>(False Neg)</small>`;
            document.getElementById("cmTP").innerHTML = `${cm.true_positives}<br><small>(True Pos)</small>`;
        }

        // Comparison Table
        const cmpr = metrics.comparison_metrics || {};
        document.getElementById("cmpRFAcc").textContent = tm.accuracy ? `${(tm.accuracy * 100).toFixed(2)}%` : "--";
        document.getElementById("cmpLRAcc").textContent = cmpr.accuracy ? `${(cmpr.accuracy * 100).toFixed(2)}%` : "--";

        document.getElementById("cmpRFRec").textContent = tm.recall ? `${(tm.recall * 100).toFixed(2)}%` : "--";
        document.getElementById("cmpLRRec").textContent = cmpr.recall ? `${(cmpr.recall * 100).toFixed(2)}%` : "--";

        document.getElementById("cmpRFPrec").textContent = tm.precision ? `${(tm.precision * 100).toFixed(2)}%` : "--";
        document.getElementById("cmpLRPrec").textContent = cmpr.precision ? `${(cmpr.precision * 100).toFixed(2)}%` : "--";

        document.getElementById("cmpRFF1").textContent = tm.f1_score ? `${(tm.f1_score * 100).toFixed(2)}%` : "--";
        document.getElementById("cmpLRF1").textContent = cmpr.f1_score ? `${(cmpr.f1_score * 100).toFixed(2)}%` : "--";

        document.getElementById("cmpRFAuc").textContent = tm.roc_auc ? `${(tm.roc_auc * 100).toFixed(2)}%` : "--";
        document.getElementById("cmpLRAuc").textContent = cmpr.roc_auc ? `${(cmpr.roc_auc * 100).toFixed(2)}%` : "--";

        loading.style.display = "none";
        content.style.display = "block";
    } catch (err) {
        loading.style.display = "none";
        const message = document.createElement("strong");
        message.textContent = `Failed to load AI Dashboard: ${err.message}`;
        const retryButton = document.createElement("button");
        retryButton.type = "button";
        retryButton.className = "dashboard-retry";
        retryButton.textContent = "Retry Connection";
        retryButton.addEventListener("click", loadAIDashboard);
        error.replaceChildren(message, document.createElement("br"), retryButton);
        error.style.display = "block";
    }
}

document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("refreshAIDashboard")?.addEventListener("click", loadAIDashboard);
});


// =========================================================================
