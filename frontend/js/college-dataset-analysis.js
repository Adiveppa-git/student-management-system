// PART 4: College Dataset Analysis & Model Readiness (Phase 8)
// =========================================================================

let selectedCollegeFile = null;
let isDemoCohort = false;
let studentRiskRecords = [];

function filterStudentRiskRecords(records, filters) {
    const search = filters.search.trim().toLocaleLowerCase();
    return records.filter(record =>
        (!filters.category || record.risk_category === filters.category)
        && (!filters.branch || record.branch === filters.branch)
        && (!filters.semester || String(record.semester) === filters.semester)
        && (!search || record.student_ref.toLocaleLowerCase().includes(search))
    );
}

function escapeCsvField(value, isText = false) {
    let field = value == null ? "" : String(value);
    if (isText && /^[\t\r\n ]*[=+\-@]/.test(field)) {
        field = `'${field}`;
    }
    return `"${field.replace(/"/g, '""')}"`;
}

function buildStudentRiskCsv(records) {
    if (!Array.isArray(records) || records.length === 0) return null;

    const headers = [
        "Student Reference",
        "Branch",
        "Academic Year",
        "Semester",
        "Attendance Percentage",
        "CIE Marks Obtained",
        "CIE Maximum Marks",
        "Risk Category",
        "Main Risk Factors",
        "Intervention Recommendations",
    ];
    const rows = records.map(record => {
        const recommendations = Array.isArray(record.intervention_recommendations)
            ? record.intervention_recommendations
                .filter(item =>
                    item
                    && typeof item.recommendation === "string"
                    && typeof item.reason === "string"
                )
                .map(item => `${item.recommendation} Reason: ${item.reason}`)
                .join("\n")
            : "";
        const fields = [
            [record.student_ref, true],
            [record.branch, true],
            [record.academic_year, false],
            [record.semester, false],
            [record.attendance_pct, false],
            [record.cie_marks_obtained, false],
            [record.cie_max_marks, false],
            [record.risk_category, true],
            [Array.isArray(record.main_risk_factors) ? record.main_risk_factors.join("; ") : "", true],
            [recommendations, true],
        ];
        return fields.map(([value, isText]) => escapeCsvField(value, isText)).join(",");
    });

    return [headers.map(header => escapeCsvField(header)).join(","), ...rows].join("\r\n");
}

function appendTextCell(row, value, className = "") {
    const cell = document.createElement("td");
    if (className) cell.className = className;
    cell.textContent = value ?? "";
    row.appendChild(cell);
    return cell;
}

function appendCodeCell(row, value) {
    const cell = appendTextCell(row, "");
    const code = document.createElement("code");
    code.textContent = value ?? "";
    cell.appendChild(code);
}

function appendBadge(container, value, className) {
    const badge = document.createElement("span");
    badge.className = className;
    badge.textContent = value ?? "";
    container.appendChild(badge);
}

function appendRiskRecommendations(row, recommendations) {
    const cell = appendTextCell(row, "");
    const items = Array.isArray(recommendations)
        ? recommendations.filter(item =>
            item
            && typeof item.recommendation === "string"
            && item.recommendation.trim()
            && typeof item.reason === "string"
            && item.reason.trim()
        )
        : [];

    if (items.length === 0) {
        cell.textContent = "No intervention indicated by the screening rules.";
        return;
    }

    const list = document.createElement("ul");
    for (const item of items) {
        const listItem = document.createElement("li");
        listItem.textContent = `${item.recommendation} Reason: ${item.reason}`;
        list.appendChild(listItem);
    }
    cell.appendChild(list);
}

function appendEmptyNote(container, message) {
    const note = document.createElement("span");
    note.className = "analysis-empty-note";
    note.textContent = message;
    container.appendChild(note);
}

function handleFileSelected(event) {
    const file = event.target.files[0];
    if (file) {
        isDemoCohort = false;
        setCollegeFile(file);
    }
}

function setCollegeFile(file) {
    selectedCollegeFile = file;
    const nameEl = document.getElementById("selectedFileName");
    nameEl.textContent = `Selected: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
    nameEl.style.color = "var(--primary)";
    document.getElementById("analyzeDatasetBtn").disabled = false;
    document.getElementById("analysisError").style.display = "none";
}

function clearAnalysisView() {
    selectedCollegeFile = null;
    isDemoCohort = false;
    const input = document.getElementById("collegeCsvInput");
    if (input) input.value = "";
    document.getElementById("selectedFileName").textContent = "No file currently selected (max 5 MB)";
    document.getElementById("selectedFileName").style.color = "var(--text-muted)";
    document.getElementById("analyzeDatasetBtn").disabled = true;
    document.getElementById("analysisError").style.display = "none";
    document.getElementById("analysisResults").style.display = "none";
    resetStudentRiskAnalysis();
}

function resetStudentRiskAnalysis() {
    studentRiskRecords = [];
    document.getElementById("studentRiskContent").hidden = true;
    document.getElementById("studentRiskInitialEmpty").hidden = false;
    document.getElementById("studentRiskMethodology").textContent =
        "Preliminary, rule-based screening only — not a validated prediction. At Risk: attendance below 75%, " +
        "CIE below 40%, or recorded active backlogs. Moderate Risk: attendance 75–85% or CIE 40–60%. " +
        "Dataset readiness is assessed separately below.";
    document.getElementById("studentRiskTableBody").replaceChildren();
    document.getElementById("studentRiskNoRows").hidden = true;
    document.getElementById("exportStudentRiskCsv").disabled = true;
    document.getElementById("studentRiskExportStatus").textContent = "";
    document.getElementById("studentRiskCategoryFilter").value = "";
    document.getElementById("studentRiskSearch").value = "";
    document.getElementById("studentRiskBranchFilter").replaceChildren(
        new Option("All branches", "")
    );
    document.getElementById("studentRiskSemesterFilter").replaceChildren(
        new Option("All semesters", "")
    );
}

function renderStudentRiskAnalysis(analysis = {}) {
    studentRiskRecords = Array.isArray(analysis.records) ? analysis.records : [];
    document.getElementById("studentRiskInitialEmpty").hidden = true;
    document.getElementById("studentRiskContent").hidden = false;
    if (analysis.methodology) {
        document.getElementById("studentRiskMethodology").textContent = analysis.methodology;
    }

    const categoryCounts = analysis.category_counts || {};
    const categoryFields = [
        ["At Risk", "AtRisk"],
        ["Moderate Risk", "Moderate"],
        ["Good", "Good"],
    ];
    for (const [category, suffix] of categoryFields) {
        const summary = categoryCounts[category] || {};
        document.getElementById(`studentRisk${suffix}Count`).textContent = summary.count ?? 0;
        document.getElementById(`studentRisk${suffix}Percent`).textContent =
            `${Number(summary.percentage ?? 0).toFixed(1)}%`;
    }
    document.getElementById("studentRiskTotalCount").textContent = analysis.total_students ?? studentRiskRecords.length;

    const branches = [...new Set(studentRiskRecords.map(record => record.branch).filter(Boolean))].sort();
    const semesters = [...new Set(studentRiskRecords.map(record => String(record.semester)).filter(Boolean))]
        .sort((left, right) => Number(left) - Number(right));
    const branchFilter = document.getElementById("studentRiskBranchFilter");
    const semesterFilter = document.getElementById("studentRiskSemesterFilter");
    branchFilter.replaceChildren(new Option("All branches", ""));
    semesterFilter.replaceChildren(new Option("All semesters", ""));
    branches.forEach(branch => branchFilter.add(new Option(branch, branch)));
    semesters.forEach(semester => semesterFilter.add(new Option(semester, semester)));
    applyStudentRiskFilters();
}

function applyStudentRiskFilters() {
    const filteredRecords = getFilteredStudentRiskRecords();
    const tableBody = document.getElementById("studentRiskTableBody");
    tableBody.replaceChildren();

    for (const record of filteredRecords) {
        const row = document.createElement("tr");
        appendTextCell(row, record.student_ref);
        appendTextCell(row, record.branch);
        appendTextCell(row, record.academic_year);
        appendTextCell(row, record.semester);
        appendTextCell(row, `${Number(record.attendance_pct).toFixed(1)}%`);
        const cieObtained = Number(record.cie_marks_obtained);
        const cieMaximum = Number(record.cie_max_marks);
        appendTextCell(
            row,
            Number.isFinite(cieObtained) && Number.isFinite(cieMaximum)
                ? `${cieObtained} / ${cieMaximum}`
                : "—"
        );

        const categoryCell = appendTextCell(row, "");
        const categoryClass = {
            "At Risk": "risk-category-at-risk",
            "Moderate Risk": "risk-category-moderate",
            "Good": "risk-category-good",
        }[record.risk_category] || "risk-category-good";
        appendBadge(categoryCell, record.risk_category, `risk-category-badge ${categoryClass}`);
        appendTextCell(row, Array.isArray(record.main_risk_factors)
            ? record.main_risk_factors.join(", ")
            : "");
        appendRiskRecommendations(row, record.intervention_recommendations);
        tableBody.appendChild(row);
    }

    document.getElementById("studentRiskNoRows").hidden = filteredRecords.length > 0;
    const exportButton = document.getElementById("exportStudentRiskCsv");
    exportButton.disabled = filteredRecords.length === 0;
    document.getElementById("studentRiskExportStatus").textContent =
        filteredRecords.length === 0
            ? "No student records match the selected filters; no CSV report is available."
            : `${filteredRecords.length} filtered student record${filteredRecords.length === 1 ? "" : "s"} ready to export.`;
}

function getFilteredStudentRiskRecords() {
    const filters = {
        category: document.getElementById("studentRiskCategoryFilter").value,
        branch: document.getElementById("studentRiskBranchFilter").value,
        semester: document.getElementById("studentRiskSemesterFilter").value,
        search: document.getElementById("studentRiskSearch").value,
    };
    return filterStudentRiskRecords(studentRiskRecords, filters);
}

function exportFilteredStudentRiskRecords() {
    const records = getFilteredStudentRiskRecords();
    const csv = buildStudentRiskCsv(records);
    const statusElement = document.getElementById("studentRiskExportStatus");
    if (!csv) {
        statusElement.textContent = "No student records match the selected filters; no CSV report was generated.";
        return;
    }

    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const downloadUrl = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = downloadUrl;
    link.download = "student-risk-report.csv";
    link.click();
    setTimeout(() => URL.revokeObjectURL(downloadUrl), 1000);
    statusElement.textContent =
        `Exported ${records.length} filtered student record${records.length === 1 ? "" : "s"} to CSV.`;
}

function loadDemoCohort(type) {
    isDemoCohort = true;
    let csvText = "";
    let filename = "";

    if (type === 'valid') {
        filename = "eligible_engineering_cohort_2024.csv";
        const lines = [
            "student_ref,branch,academic_year,semester,attendance_pct,cie_marks_obtained,cie_max_marks,previous_sgpa,cumulative_cgpa,active_backlogs,verified_outcome,is_at_risk_label,outcome_source"
        ];
        // 80 Passing students across CSE, ISE, ECE
        for (let i = 1; i <= 80; i++) {
            const b = i % 3 === 0 ? "CSE" : (i % 3 === 1 ? "ISE" : "ECE");
            const pad = String(i).padStart(3, '0');
            lines.push(`ANON_ENG_${pad},${b},2,4,86.5,41.0,50.0,8.2,8.1,0,PASS,false,OFFICIAL_EXAM_CELL`);
        }
        // 40 At-risk students
        for (let i = 81; i <= 120; i++) {
            const b = i % 2 === 0 ? "MECH" : "ECE";
            const pad = String(i).padStart(3, '0');
            lines.push(`ANON_ENG_${pad},${b},2,4,61.0,17.5,50.0,5.2,5.5,3,FAIL_OR_DETAINED,true,OFFICIAL_EXAM_CELL`);
        }
        csvText = lines.join("\n");
    } else if (type === 'small') {
        filename = "small_sample_cohort.csv";
        csvText = [
            "student_ref,branch,academic_year,semester,attendance_pct,cie_marks_obtained,cie_max_marks",
            "ANON_001,CSE,1,1,85.0,40.0,50.0",
            "ANON_002,ISE,1,2,78.0,35.0,50.0",
            "ANON_003,ECE,2,3,92.0,46.0,50.0",
            "ANON_004,MECH,2,3,60.0,22.0,50.0"
        ].join("\n");
    } else if (type === 'leaky') {
        filename = "post_exam_leaky_cohort.csv";
        csvText = [
            "student_ref,branch,academic_year,semester,attendance_pct,cie_marks_obtained,see_marks,promotion_status",
            "ANON_LEAK_01,CSE,2,3,80.0,38.0,65.0,PROMOTED",
            "ANON_LEAK_02,ECE,2,3,65.0,20.0,32.0,DETAINED",
            "ANON_LEAK_03,ISE,2,3,88.0,44.0,78.0,PROMOTED"
        ].join("\n");
    }

    const file = new File([csvText], filename, { type: "text/csv" });
    setCollegeFile(file);
    submitCollegeAnalysis();
}

async function submitCollegeAnalysis() {
    if (!selectedCollegeFile) return;

    const analyzeBtn = document.getElementById("analyzeDatasetBtn");
    const loading = document.getElementById("analysisLoading");
    const errorBox = document.getElementById("analysisError");
    const resultsBox = document.getElementById("analysisResults");

    resetStudentRiskAnalysis();
    analyzeBtn.disabled = true;
    const originalText = analyzeBtn.textContent;
    const spinner = document.createElement("span");
    spinner.className = "spinner";
    analyzeBtn.replaceChildren(spinner, document.createTextNode(" Profiling Dataset..."));
    loading.style.display = "block";
    errorBox.style.display = "none";
    resultsBox.style.display = "none";

    try {
        const formData = new FormData();
        formData.append("file", selectedCollegeFile);

        const response = await fetch(AI_ANALYZE_API, {
            method: "POST",
            body: formData
        });

        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            let errorMsg = errData.detail || "Analysis request failed";
            if (response.status === 413) {
                errorMsg = `File Size Exceeded (HTTP 413): ${errData.detail || 'Maximum allowable size is 5 MB.'}`;
            } else if (response.status === 422) {
                errorMsg = `Header Schema Error (HTTP 422): ${errData.detail || 'Missing required column headers or duplicate column headers detected.'}`;
            } else if (response.status === 400) {
                errorMsg = `Invalid File Format (HTTP 400): ${errData.detail || 'Could not parse CSV content.'}`;
            }
            throw new Error(errorMsg);
        }

        const data = await response.json().catch(() => null);
        if (!data || typeof data !== "object") {
            throw new Error("Malformed API response received from server.");
        }
        renderAnalysisReport(data);
        renderStudentRiskAnalysis(data.student_risk_analysis);

        loading.style.display = "none";
        resultsBox.style.display = "block";
        resultsBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    } catch (err) {
        loading.style.display = "none";
        const errorLabel = document.createElement("strong");
        errorLabel.textContent = "Analysis Failed:";
        errorBox.replaceChildren(errorLabel, document.createTextNode(` ${err.message}`));
        errorBox.style.display = "block";
        resultsBox.style.display = "none";
    } finally {
        analyzeBtn.disabled = false;
        analyzeBtn.textContent = originalText;
    }
}

function renderAnalysisReport(data) {
    const readiness = (data && data.readiness_assessment) || {};
    const status = readiness.status || "TRAINING_BLOCKED";
    const isReady = readiness.is_ready_for_review;

    // 0. Update Provenance Banner (distinguishes demo from real institutional data)
    const provenanceBanner = document.getElementById("datasetProvenanceBanner");
    const provenanceIcon = document.getElementById("provenanceIcon");
    const provenanceText = document.getElementById("provenanceText");
    if (provenanceBanner) {
        if (isDemoCohort) {
            provenanceBanner.style.background = "#fff8e6";
            provenanceBanner.style.border = "1px solid #ffd166";
            provenanceBanner.style.color = "#996500";
            if (provenanceIcon) provenanceIcon.textContent = "🧪";
            if (provenanceText) {
                const label = document.createElement("strong");
                label.textContent = "Synthetic Demonstration Cohort:";
                const warning = document.createElement("strong");
                warning.textContent = "Do NOT interpret these results as real institutional engineering student data.";
                provenanceText.replaceChildren(
                    label,
                    document.createTextNode(" This analysis was run on a synthetic demo profile for testing and validation. "),
                    warning,
                );
            }
        } else {
            provenanceBanner.style.background = "#eff6ff";
            provenanceBanner.style.border = "1px solid #bfdbfe";
            provenanceBanner.style.color = "#1e40af";
            if (provenanceIcon) provenanceIcon.textContent = "🏛️";
            if (provenanceText) {
                const label = document.createElement("strong");
                label.textContent = "Uploaded Local Institutional Data:";
                provenanceText.replaceChildren(
                    label,
                    document.createTextNode(" Evaluated ephemerally in-memory. Zero records persisted to MongoDB. Zero student PII accepted or stored."),
                );
            }
        }
    }

    // 0b. Update Readiness Significance Text
    const explanationEl = document.getElementById("readinessExplanationText");
    if (explanationEl) {
        const explanation = document.createElement("strong");
        const qualifier = document.createElement("em");
        if (isReady) {
            explanation.textContent = "READY_FOR_REVIEW";
            qualifier.textContent = "It does NOT prove institutional representativeness, algorithmic fairness, or production model deployment readiness.";
            explanationEl.replaceChildren(
                explanation,
                document.createTextNode(" indicates that the uploaded dataset satisfies structural formatting and statistical criteria (sample size ≥ 100, verified labels ≥ 80, minority ≥ 15, zero target leakage, zero duplicates, error rate ≤ 5%) for prospective offline human review. "),
                qualifier,
            );
        } else {
            explanation.textContent = "TRAINING_BLOCKED";
            explanationEl.replaceChildren(
                explanation,
                document.createTextNode(" indicates that the dataset violates one or more data-quality or experimental safety criteria. Model training remains strictly blocked until all specified blockers are resolved."),
            );
        }
    }

    // 1. Overall Status Card
    const badge = document.getElementById("readinessBadge");
    const statusText = document.getElementById("readinessStatusText");
    statusText.textContent = status;
    badge.className = `status-badge ${isReady ? 'ready' : 'blocked'}`;

    const splitBadge = document.getElementById("defensibleSplitBadge");
    if (readiness.defensible_split_possible) {
        splitBadge.className = "badge-pill pass";
        splitBadge.textContent = "Defensible Split Viable";
    } else {
        splitBadge.className = "badge-pill fail";
        splitBadge.textContent = "Split Not Feasible";
    }

    document.getElementById("analyzedDatasetName").textContent = (data && data.dataset_name) || "dataset.csv";

    // 2. Blockers and Warnings
    const blockersBox = document.getElementById("blockersBox");
    const blockersList = document.getElementById("blockersList");
    blockersList.replaceChildren();
    if (readiness.readiness_blockers && readiness.readiness_blockers.length > 0) {
        readiness.readiness_blockers.forEach(b => {
            const li = document.createElement("li");
            li.textContent = b;
            blockersList.appendChild(li);
        });
        blockersBox.style.display = "block";
    } else {
        blockersBox.style.display = "none";
    }

    const warningsBox = document.getElementById("warningsBox");
    const warningsList = document.getElementById("warningsList");
    warningsList.replaceChildren();
    if (readiness.warnings && readiness.warnings.length > 0) {
        readiness.warnings.forEach(w => {
            const li = document.createElement("li");
            li.textContent = w;
            warningsList.appendChild(li);
        });
        warningsBox.style.display = "block";
    } else {
        warningsBox.style.display = "none";
    }

    const leakageBox = document.getElementById("leakageAlertBox");
    const leakageDetails = document.getElementById("leakageDetails");
    if (data.target_leakage_warnings && data.target_leakage_warnings.length > 0) {
        leakageDetails.replaceChildren();
        data.target_leakage_warnings.forEach(warning => {
            const detail = document.createElement("div");
            const feature = document.createElement("code");
            feature.textContent = warning.feature_name ?? "";
            detail.append(
                document.createTextNode("• "),
                feature,
                document.createTextNode(`: ${warning.explanation ?? ""} (Mitigation: ${warning.mitigation ?? ""})`),
            );
            leakageDetails.appendChild(detail);
        });
        leakageBox.style.display = "block";
    } else {
        leakageBox.style.display = "none";
    }

    // 3. Key Metrics Grid
    document.getElementById("resTotalRecords").textContent = data.total_records || 0;
    document.getElementById("resValidRecords").textContent = data.valid_records_count || 0;
    const errPct = (data.validation_error_rate * 100).toFixed(1);
    document.getElementById("resErrorRate").textContent = `${errPct}% error rate (${data.invalid_records_count || 0} invalid)`;

    const studentMetrics = data.student_metrics || {};
    document.getElementById("resUniqueStudents").textContent = studentMetrics.unique_pseudonymous_students || 0;
    document.getElementById("resObsPerStudent").textContent = `${studentMetrics.observations_per_student_avg || 0} obs/student`;

    const outcomeBalance = data.outcome_and_class_balance || {};
    document.getElementById("resLabeledRecords").textContent = outcomeBalance.labeled_records_count || 0;
    const labelRatePct = (outcomeBalance.labeling_rate * 100).toFixed(1);
    document.getElementById("resLabelingRate").textContent = `${labelRatePct}% labeling rate`;

    document.getElementById("resAtRiskCount").textContent = outcomeBalance.at_risk_count || 0;
    const riskRatioPct = (outcomeBalance.at_risk_ratio * 100).toFixed(1);
    document.getElementById("resAtRiskRatio").textContent = `${riskRatioPct}% at-risk ratio`;

    document.getElementById("resDuplicatesCount").textContent = data.duplicate_observations_count || 0;

    // 4. 7-Point ML Readiness Checklist Table
    const checklistBody = document.getElementById("readinessChecklistBody");
    checklistBody.replaceChildren();
    const checks = readiness.checks || {};
    for (const [key, check] of Object.entries(checks)) {
        const tr = document.createElement("tr");
        const statusClass = check.passed ? "badge-pill pass" : (check.severity === "BLOCKER" ? "badge-pill fail" : "badge-pill warn");
        const nameCell = appendTextCell(tr, "");
        const checkName = document.createElement("strong");
        checkName.textContent = check.check_name ?? "";
        nameCell.appendChild(checkName);

        const statusCell = appendTextCell(tr, "");
        appendBadge(statusCell, check.passed ? "PASS" : "FAIL", statusClass);

        const severityCell = appendTextCell(tr, "");
        appendBadge(severityCell, check.severity, check.severity === "BLOCKER" ? "badge-pill fail" : "badge-pill info");

        appendTextCell(tr, check.details, "readiness-detail");
        checklistBody.appendChild(tr);
    }

    // 5. Cohort Distributions Badges
    const branchBox = document.getElementById("branchDistBadges");
    branchBox.replaceChildren();
    const branchDist = (data.categorical_distributions && data.categorical_distributions.branch_distribution) || {};
    for (const [branch, count] of Object.entries(branchDist)) {
        appendBadge(branchBox, `${branch}: ${count}`, "badge-pill info");
    }
    if (Object.keys(branchDist).length === 0) appendEmptyNote(branchBox, "No valid branches");

    const yearBox = document.getElementById("yearDistBadges");
    yearBox.replaceChildren();
    const yearDist = (data.categorical_distributions && data.categorical_distributions.academic_year_distribution) || {};
    for (const [yr, count] of Object.entries(yearDist)) {
        appendBadge(yearBox, `Year ${yr}: ${count}`, "badge-pill info");
    }

    const semBox = document.getElementById("semesterDistBadges");
    semBox.replaceChildren();
    const semDist = (data.categorical_distributions && data.categorical_distributions.semester_distribution) || {};
    for (const [sem, count] of Object.entries(semDist)) {
        appendBadge(semBox, `Sem ${sem}: ${count}`, "badge-pill info");
    }

    // 6. Outcomes & Class Balance Meter
    document.getElementById("lblPassingCount").textContent = outcomeBalance.passing_count || 0;
    document.getElementById("lblRiskCount").textContent = outcomeBalance.at_risk_count || 0;
    document.getElementById("lblImbalanceRatio").textContent = outcomeBalance.imbalance_ratio || "N/A";

    const balanceBar = document.getElementById("classBalanceBar");
    const riskPct = outcomeBalance.at_risk_ratio ? (outcomeBalance.at_risk_ratio * 100).toFixed(1) : 0;
    balanceBar.style.width = `${riskPct}%`;

    const outcomeBox = document.getElementById("outcomeBreakdownBadges");
    outcomeBox.replaceChildren();
    const breakdown = outcomeBalance.verified_outcome_breakdown || {};
    for (const [outcome, count] of Object.entries(breakdown)) {
        const cls = outcome === "PASS" ? "pass" : "fail";
        appendBadge(outcomeBox, `${outcome}: ${count}`, `badge-pill ${cls}`);
    }
    if (Object.keys(breakdown).length === 0) appendEmptyNote(outcomeBox, "Unlabeled observations");

    const authorities = outcomeBalance.outcome_sources || [];
    document.getElementById("outcomeAuthorities").textContent = authorities.length > 0 ? authorities.join(", ") : "None documented";

    // 7. Numeric Summary Statistics Table
    const numericBody = document.getElementById("numericStatsBody");
    numericBody.replaceChildren();
    const numStats = data.numeric_summary_statistics || {};
    for (const [feat, s] of Object.entries(numStats)) {
        if (s.count === 0) continue;
        const tr = document.createElement("tr");
        appendCodeCell(tr, feat);
        appendTextCell(tr, s.count);
        appendTextCell(tr, s.min !== null ? s.min : "--");
        appendTextCell(tr, s.max !== null ? s.max : "--");
        appendTextCell(tr, s.mean !== null ? s.mean : "--");
        appendTextCell(tr, s.median !== null ? s.median : "--");
        appendTextCell(tr, s.std !== null ? s.std : "--");
        numericBody.appendChild(tr);
    }
    if (numericBody.children.length === 0) {
        const row = document.createElement("tr");
        const emptyCell = appendTextCell(row, "No numeric features with observations.", "table-empty-state");
        emptyCell.colSpan = 7;
        numericBody.appendChild(row);
    }

    // 8. Missing Values Summary Table
    const missingBody = document.getElementById("missingValuesBody");
    missingBody.replaceChildren();
    const missingSummary = data.missing_values_summary || {};
    for (const [field, m] of Object.entries(missingSummary)) {
        const tr = document.createElement("tr");
        const isComplete = m.missing_count === 0;
        appendCodeCell(tr, field);
        appendTextCell(tr, m.present_count);
        appendTextCell(tr, m.missing_count);
        appendTextCell(tr, `${m.missing_pct}%`);
        const statusCell = appendTextCell(tr, "");
        if (isComplete) {
            appendBadge(statusCell, "100% Complete", "badge-pill pass");
        } else if (m.missing_pct > 30.0) {
            appendBadge(statusCell, `High Missing (${m.missing_pct}%)`, "badge-pill fail");
        } else {
            appendBadge(statusCell, `Partial (${m.missing_pct}%)`, "badge-pill warn");
        }
        missingBody.appendChild(tr);
    }

    // 9. Recommendations
    const recList = document.getElementById("recommendationsList");
    recList.replaceChildren();
    const recs = readiness.recommendations || [];
    recs.forEach(r => {
        const li = document.createElement("li");
        li.textContent = r;
        recList.appendChild(li);
    });

    // 10. Privacy Guarantee
    if (data.privacy_guarantee) {
        document.getElementById("privacyGuaranteeText").textContent = data.privacy_guarantee;
    }
}

document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("collegeCsvInput")?.addEventListener("change", handleFileSelected);
    document.getElementById("browseCollegeCsv")?.addEventListener("click", () => {
        document.getElementById("collegeCsvInput").click();
    });
    document.getElementById("analyzeDatasetBtn")?.addEventListener("click", submitCollegeAnalysis);
    document.getElementById("clearAnalysisView")?.addEventListener("click", clearAnalysisView);
    document.getElementById("exportStudentRiskCsv")?.addEventListener("click", exportFilteredStudentRiskRecords);
    [
        "studentRiskCategoryFilter",
        "studentRiskBranchFilter",
        "studentRiskSemesterFilter",
    ].forEach(id => {
        document.getElementById(id)?.addEventListener("change", applyStudentRiskFilters);
    });
    document.getElementById("studentRiskSearch")?.addEventListener("input", applyStudentRiskFilters);
    document.querySelectorAll("[data-demo-cohort]").forEach(button => {
        button.addEventListener("click", () => loadDemoCohort(button.dataset.demoCohort));
    });
});
