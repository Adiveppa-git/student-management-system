// PART 3: UCI Benchmark Prediction Form & Preset Profiles
// =========================================================================

const DAILY_STUDYTIME_TO_WEEKLY = {
    less_than_1: 2,
    "1_to_2": 3,
    "2_to_3": 4,
    "3_to_4": 4,
    more_than_4: 4
};

const PRESET_PROFILES = {
    struggling: {
        subject: "Mathematics", maxMarks: 20,
        school: "GP", sex: "M", age: 18, address: "U", famsize: "GT3", Pstatus: "T",
        Medu: 1, Fedu: 1, Mjob: "other", Fjob: "other", reason: "course", guardian: "mother",
        traveltime: 3, studytime: "less_than_1", failures: 3, schoolsup: "yes", famsup: "no", paid: "no",
        activities: "no", nursery: "yes", higher: "no", internet: "no", romantic: "yes",
        famrel: 2, freetime: 4, goout: 5, Dalc: 3, Walc: 4, health: 2, absences: 22, G1: 4, totalMarks: 20
    },
    thriving: {
        subject: "Physics", maxMarks: 20,
        school: "GP", sex: "F", age: 16, address: "U", famsize: "LE3", Pstatus: "T",
        Medu: 4, Fedu: 4, Mjob: "health", Fjob: "teacher", reason: "reputation", guardian: "mother",
        traveltime: 1, studytime: "more_than_4", failures: 0, schoolsup: "no", famsup: "yes", paid: "yes",
        activities: "yes", nursery: "yes", higher: "yes", internet: "yes", romantic: "no",
        famrel: 5, freetime: 2, goout: 2, Dalc: 1, Walc: 1, health: 5, absences: 0, G1: 18, totalMarks: 20
    },
    average: {
        subject: "Chemistry", maxMarks: 20,
        school: "GP", sex: "M", age: 17, address: "U", famsize: "GT3", Pstatus: "T",
        Medu: 2, Fedu: 2, Mjob: "services", Fjob: "services", reason: "home", guardian: "father",
        traveltime: 1, studytime: "1_to_2", failures: 0, schoolsup: "no", famsup: "yes", paid: "no",
        activities: "yes", nursery: "yes", higher: "yes", internet: "yes", romantic: "no",
        famrel: 4, freetime: 3, goout: 3, Dalc: 1, Walc: 2, health: 4, absences: 4, G1: 11, totalMarks: 20
    }
};

function fillPreset(profileKey) {
    const data = PRESET_PROFILES[profileKey];
    if (!data) return;

    for (const [key, value] of Object.entries(data)) {
        const el = document.getElementById(`bm_${key}`);
        if (el) el.value = value;
    }
    updateMarksMaximum();
    // Clear previous prediction results
    document.getElementById("benchmarkResult").style.display = "none";
    document.getElementById("predictError").style.display = "none";
}

function clearBenchmarkForm() {
    document.getElementById("benchmarkForm").reset();
    const marksInput = document.getElementById("bm_G1");
    marksInput.removeAttribute("max");
    marksInput.setCustomValidity("");
    document.getElementById("predictError").textContent = "";
    document.getElementById("benchmarkResult").style.display = "none";
    document.getElementById("predictError").style.display = "none";
}

function updateMarksMaximum() {
    const marksInput = document.getElementById("bm_G1");
    const maxMarksInput = document.getElementById("bm_maxMarks");
    const maxMarks = maxMarksInput.value;

    if (maxMarks && maxMarksInput.validity.valid) {
        marksInput.max = maxMarks;
        marksInput.setCustomValidity(
            marksInput.value && Number(marksInput.value) > Number(maxMarks)
                ? `Obtained Marks cannot exceed Maximum Marks (${maxMarks}).`
                : ""
        );
    } else {
        marksInput.removeAttribute("max");
        marksInput.setCustomValidity("");
    }
}

async function submitBenchmarkPrediction(e) {
    e.preventDefault();

    const submitBtn = document.getElementById("predictSubmitBtn");
    const form = document.getElementById("benchmarkForm");
    const errorBox = document.getElementById("predictError");
    const resultBox = document.getElementById("benchmarkResult");

    errorBox.style.display = "none";
    updateMarksMaximum();
    const subjectInput = document.getElementById("bm_subject");
    const maxMarksInput = document.getElementById("bm_maxMarks");
    const marksInput = document.getElementById("bm_G1");
    const showValidationError = (message, input) => {
        errorBox.textContent = message;
        errorBox.style.display = "block";
        input?.focus();
    };

    if (!subjectInput.validity.valid) {
        showValidationError("Select a subject before predicting.", subjectInput);
        return;
    }
    if (!maxMarksInput.validity.valid) {
        showValidationError("Enter Maximum Marks as a positive whole number.", maxMarksInput);
        return;
    }
    if (!marksInput.value || !marksInput.validity.valid) {
        const message = marksInput.validity.rangeOverflow
            ? "Obtained Marks cannot be greater than Maximum Marks."
            : "Enter valid Obtained Marks (zero or greater).";
        showValidationError(message, marksInput);
        return;
    }
    if (!form.checkValidity()) {
        const firstInvalidInput = form.querySelector(":invalid");
        showValidationError("Complete all required fields with valid values before predicting.", firstInvalidInput);
        return;
    }

    const marksObtained = parseFloat(marksInput.value);
    const maxMarks = parseFloat(maxMarksInput.value);
    const subject = subjectInput.value;

    // Gather and parse all 31 inputs matching UCIBenchmarkStudentInput
    const payload = {
        school: document.getElementById("bm_school").value,
        sex: document.getElementById("bm_sex").value,
        age: parseInt(document.getElementById("bm_age").value),
        address: document.getElementById("bm_address").value,
        famsize: document.getElementById("bm_famsize").value,
        Pstatus: document.getElementById("bm_Pstatus").value,
        Medu: parseInt(document.getElementById("bm_Medu").value),
        Fedu: parseInt(document.getElementById("bm_Fedu").value),
        Mjob: document.getElementById("bm_Mjob").value,
        Fjob: document.getElementById("bm_Fjob").value,
        reason: document.getElementById("bm_reason").value,
        guardian: document.getElementById("bm_guardian").value,
        traveltime: parseInt(document.getElementById("bm_traveltime").value),
        studytime: DAILY_STUDYTIME_TO_WEEKLY[document.getElementById("bm_studytime").value],
        failures: parseInt(document.getElementById("bm_failures").value),
        schoolsup: document.getElementById("bm_schoolsup").value,
        famsup: document.getElementById("bm_famsup").value,
        paid: document.getElementById("bm_paid").value,
        activities: document.getElementById("bm_activities").value,
        nursery: document.getElementById("bm_nursery").value,
        higher: document.getElementById("bm_higher").value,
        internet: document.getElementById("bm_internet").value,
        romantic: document.getElementById("bm_romantic").value,
        famrel: parseInt(document.getElementById("bm_famrel").value),
        freetime: parseInt(document.getElementById("bm_freetime").value),
        goout: parseInt(document.getElementById("bm_goout").value),
        Dalc: parseInt(document.getElementById("bm_Dalc").value),
        Walc: parseInt(document.getElementById("bm_Walc").value),
        health: parseInt(document.getElementById("bm_health").value),
        absences: parseInt(document.getElementById("bm_absences").value),
        G1: (marksObtained / maxMarks) * 20
    };

    // Prevent duplicate submissions and show loading indicator
    resultBox.style.display = "none";
    submitBtn.disabled = true;
    const originalText = submitBtn.innerHTML;
    submitBtn.innerHTML = `<span class="spinner"></span> Evaluating with Random Forest Pipeline...`;

    try {
        const response = await fetch(AI_PREDICT_API, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            if (response.status === 422) {
                // Validation error
                const details = Array.isArray(errData.detail)
                    ? errData.detail.map(d => `${d.loc ? d.loc.join('.') : ''}: ${d.msg}`).join("<br>")
                    : (errData.detail || "Validation error");
                throw new Error(`Invalid Input (HTTP 422):<br>${details}`);
            } else if (response.status === 503) {
                throw new Error(`Model Unavailable (HTTP 503): ${errData.detail || "Model artifacts missing on server."}`);
            } else {
                throw new Error(`Server Error (HTTP ${response.status}): ${errData.detail || "Prediction failed"}`);
            }
        }

        const data = await response.json();

        // Render result box
        document.getElementById("resultSubject").textContent = subject;
        const isAtRisk = data.is_at_risk;
        resultBox.className = `result-box ${isAtRisk ? 'at-risk' : 'normal'}`;

        const pill = document.getElementById("resultRiskPill");
        pill.className = `risk-pill ${isAtRisk ? 'at-risk' : 'normal'}`;
        document.getElementById("resultIcon").textContent = isAtRisk ? "⚠️" : "✅";
        document.getElementById("resultStatusText").textContent = data.risk_status;

        document.getElementById("resultModelName").textContent = data.model_name || "Random Forest";
        document.getElementById("resultRiskLevel").textContent = data.risk_level;

        const probPercent = (data.risk_probability * 100).toFixed(1);
        document.getElementById("resultRiskProb").textContent = `${probPercent}%`;

        const progressBar = document.getElementById("resultProgressBar");
        progressBar.style.width = `${probPercent}%`;
        progressBar.className = `progress-bar ${data.risk_level === 'High' ? 'high-risk' : (data.risk_level === 'Medium' ? 'medium-risk' : 'low-risk')}`;

        document.getElementById("resultConfidence").textContent = `${(data.confidence * 100).toFixed(1)}%`;
        document.getElementById("resultDisclaimer").textContent = data.disclaimer;
        document.getElementById("resultDomainNote").textContent = data.domain_applicability_note;

        resultBox.style.display = "block";
        resultBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    } catch (err) {
        errorBox.innerHTML = `<strong>Error:</strong> ${err.message}`;
        errorBox.style.display = "block";
        resultBox.style.display = "none";
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalText;
    }
}

document.addEventListener("DOMContentLoaded", () => {
    const benchmarkForm = document.getElementById("benchmarkForm");
    benchmarkForm?.addEventListener("submit", submitBenchmarkPrediction);
    document.getElementById("clearBenchmarkForm")?.addEventListener("click", clearBenchmarkForm);
    document.getElementById("bm_G1")?.addEventListener("input", updateMarksMaximum);
    document.getElementById("bm_maxMarks")?.addEventListener("input", updateMarksMaximum);
    benchmarkForm?.addEventListener("input", () => {
        updateMarksMaximum();
        if (benchmarkForm.checkValidity()) {
            const errorBox = document.getElementById("predictError");
            errorBox.textContent = "";
            errorBox.style.display = "none";
        }
    });
    document.querySelectorAll("[data-preset]").forEach(button => {
        button.addEventListener("click", () => fillPreset(button.dataset.preset));
    });
});


// =========================================================================
