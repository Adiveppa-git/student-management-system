// Navigation Tab Management
function switchTab(tabName) {
    const tabs = ["dashboard", "benchmark", "analysis"];
    if (!tabs.includes(tabName)) return;

    document.getElementById("view-students")?.classList.remove("active");
    document.getElementById("registration-link")?.classList.remove("active");

    tabs.forEach(t => {
        const btn = document.getElementById(`tab-${t}`);
        const view = document.getElementById(`view-${t}`);
        if (!btn || !view) return;
        if (t === tabName) {
            btn.classList.add("active");
            btn.setAttribute("aria-selected", "true");
            view.classList.add("active");
        } else {
            btn.classList.remove("active");
            btn.setAttribute("aria-selected", "false");
            view.classList.remove("active");
        }
    });

    if (tabName === "dashboard") {
        loadAIDashboard();
    }

    if (history.replaceState) {
        history.replaceState(null, null, `#${tabName}`);
    }
}

document.querySelectorAll("[data-tab]").forEach(button => {
    button.addEventListener("click", () => switchTab(button.dataset.tab));
});

// Initial Tab Routing from URL Hash
window.addEventListener("DOMContentLoaded", () => {
    const hash = window.location.hash.replace("#", "");
    if (["dashboard", "benchmark", "analysis"].includes(hash)) {
        switchTab(hash);
    }
});


// =========================================================================
