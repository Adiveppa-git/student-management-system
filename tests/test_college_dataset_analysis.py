"""Automated Test Suite for College Dataset Analysis and Model Readiness (Phase 8).

Validates:
1. POST /api/ai/college/analyze-dataset with valid cohort (returns READY_FOR_REVIEW).
2. Accurate calculation of missing-value counts and percentages per field.
3. Duplicate student-semester observation detection and readiness blocking.
4. Class imbalance detection and defensible split evaluation (minority < 15 blocks).
5. Unverified or missing outcome labels detection and readiness blocking.
6. Target leakage detection for post-examination features (blocks training).
7. Insufficient sample size (<100 samples) blocking behavior.
8. Error handling for malformed CSV, empty file, non-CSV extension, oversized uploads, and missing headers.
9. Numeric summary statistics (min, max, mean, median, std) and categorical distributions.
10. Ephemeral in-memory execution: zero MongoDB persistence and zero college model training.
11. Privacy guarantee: zero student PII exposed in analysis reports.
12. Decoupling and preservation of the 6 original MongoDB student records.
"""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database.connection import collection
from app.ml.college_data_prep import (
    MAX_CSV_FILE_SIZE_BYTES,
    analyze_student_risk_screening,
    parse_and_analyze_college_csv,
)

client = TestClient(app)
ORIGINAL_USNS = ["1DB24IS045", "1DB23IS001", "1DB25EC096", "1DB25CS009", "1DB23IS069", "1DB22CS020"]


@pytest.fixture
def valid_120_row_cohort_csv() -> str:
    """Generate a valid, de-identified engineering college dataset satisfying all 7 readiness criteria."""
    lines = [
        "student_ref,program,branch,academic_year,semester,attendance_pct,cie_marks_obtained,cie_max_marks,assignment_score_avg,previous_sgpa,cumulative_cgpa,gpa_scale_max,active_backlogs,credits_registered,credits_earned_prior,study_hours_per_week,verified_outcome,is_at_risk_label,outcome_source"
    ]
    # 80 Passing students across CSE, ISE, ECE
    for i in range(1, 81):
        branch = "CSE" if i % 3 == 0 else ("ISE" if i % 3 == 1 else "ECE")
        ref = f"ANON_STUDENT_{i:03d}"
        lines.append(
            f"{ref},B.Tech,{branch},2,4,85.5,42.0,50.0,88.0,8.25,8.10,10.0,0,22.0,44.0,14.0,PASS,false,OFFICIAL_EXAM_CELL"
        )
    # 40 At-risk students (satisfies min 15 minority cases)
    for i in range(81, 121):
        branch = "MECH" if i % 2 == 0 else "ECE"
        ref = f"ANON_STUDENT_{i:03d}"
        lines.append(
            f"{ref},B.Tech,{branch},2,4,62.0,18.0,50.0,55.0,5.10,5.35,10.0,3,22.0,38.0,6.0,FAIL_OR_DETAINED,true,OFFICIAL_EXAM_CELL"
        )
    return "\n".join(lines)


# =========================================================================
# 1. Successful Analysis & Model Readiness Review
# =========================================================================

def test_analyze_csv_valid_cohort_ready_for_review(valid_120_row_cohort_csv):
    """Verify valid 120-row dataset satisfies all 7 checks and returns READY_FOR_REVIEW."""
    files = {"file": ("authorized_engineering_cohort.csv", valid_120_row_cohort_csv.encode("utf-8"), "text/csv")}
    response = client.post("/api/ai/college/analyze-dataset", files=files)
    assert response.status_code == 200
    data = response.json()

    # Top-level metrics
    assert data["dataset_name"] == "authorized_engineering_cohort.csv"
    assert data["total_records"] == 120
    assert data["valid_records_count"] == 120
    assert data["invalid_records_count"] == 0
    assert data["validation_error_rate"] == 0.0
    assert data["duplicate_observations_count"] == 0
    assert len(data["target_leakage_warnings"]) == 0

    # Student metrics
    sm = data["student_metrics"]
    assert sm["unique_pseudonymous_students"] == 120
    assert sm["observations_per_student_avg"] == 1.0
    assert sm["pseudonymity_status"] == "VERIFIED_NO_RAW_PII"

    # Outcome & class balance
    cb = data["outcome_and_class_balance"]
    assert cb["labeled_records_count"] == 120
    assert cb["at_risk_count"] == 40
    assert cb["passing_count"] == 80
    assert cb["at_risk_ratio"] == 0.3333
    assert cb["passing_ratio"] == 0.6667
    assert cb["verified_outcome_breakdown"]["PASS"] == 80
    assert cb["verified_outcome_breakdown"]["FAIL_OR_DETAINED"] == 40
    assert "OFFICIAL_EXAM_CELL" in cb["outcome_sources"]

    # Preliminary student risk screen is separate from dataset readiness and verified labels.
    risk_analysis = data["student_risk_analysis"]
    assert risk_analysis["classification"] == "PRELIMINARY_RULE_BASED_SCREENING"
    assert risk_analysis["total_students"] == 120
    assert risk_analysis["category_counts"] == {
        "At Risk": {"count": 40, "percentage": 33.3},
        "Moderate Risk": {"count": 0, "percentage": 0.0},
        "Good": {"count": 80, "percentage": 66.7},
    }
    assert "not a validated prediction" in risk_analysis["methodology"].lower()
    assert data["readiness_assessment"]["status"] == "READY_FOR_REVIEW"

    # Readiness assessment decision
    ra = data["readiness_assessment"]
    assert ra["status"] == "READY_FOR_REVIEW"
    assert ra["is_ready_for_review"] is True
    assert ra["is_ready_for_training"] is False  # Never True without human sign-off
    assert ra["defensible_split_possible"] is True
    assert len(ra["readiness_blockers"]) == 0
    assert len(ra["checks"]) == 7
    for check_key, check in ra["checks"].items():
        assert check["passed"] is True, f"Check {check_key} failed unexpectedly!"

    # Numeric summary statistics
    ns = data["numeric_summary_statistics"]
    assert "attendance_pct" in ns
    assert ns["attendance_pct"]["count"] == 120
    assert ns["attendance_pct"]["min"] == 62.0
    assert ns["attendance_pct"]["max"] == 85.5
    assert ns["attendance_pct"]["mean"] is not None
    assert ns["attendance_pct"]["median"] is not None
    assert ns["attendance_pct"]["std"] is not None

    assert "cie_marks_obtained" in ns
    assert ns["cie_marks_obtained"]["count"] == 120
    assert ns["cie_marks_obtained"]["min"] == 18.0
    assert ns["cie_marks_obtained"]["max"] == 42.0

    # Categorical distributions
    cd = data["categorical_distributions"]
    assert "CSE" in cd["branch_distribution"]
    assert "ECE" in cd["branch_distribution"]
    assert "4" in cd["semester_distribution"]

    # Missing values summary
    mvs = data["missing_values_summary"]
    assert "attendance_pct" in mvs
    assert mvs["attendance_pct"]["missing_count"] == 0
    assert mvs["attendance_pct"]["missing_pct"] == 0.0

    # Privacy & Safety guarantees
    assert data["database_storage_action"] == "NONE_INSPECTED_ONLY"
    assert data["training_action"] == "NONE_COLLEGE_TRAINING_BLOCKED"
    assert "Zero records persisted to MongoDB" in data["privacy_guarantee"]
    assert "data-quality assessment, not a prediction" in data["disclaimer"].lower() or "not an academic risk prediction" in data["disclaimer"].lower()


# =========================================================================
# 2. Missing Values Profiling
# =========================================================================

def test_analyze_csv_missing_values_profiling():
    """Verify missing values are accurately counted and profiled per column."""
    lines = [
        "student_ref,branch,academic_year,semester,attendance_pct,cie_marks_obtained,previous_sgpa,study_hours_per_week",
        "STU_001,CSE,1,1,85.0,40.0,,",       # previous_sgpa and study_hours missing
        "STU_002,ECE,1,1,90.0,45.0,,12.0",   # previous_sgpa missing
        "STU_003,ISE,1,2,78.0,36.0,8.0,",    # study_hours missing
    ]
    csv_text = "\n".join(lines)
    files = {"file": ("missing_study_hours.csv", csv_text.encode("utf-8"), "text/csv")}

    response = client.post("/api/ai/college/analyze-dataset", files=files)
    assert response.status_code == 200
    data = response.json()

    mvs = data["missing_values_summary"]
    assert mvs["study_hours_per_week"]["missing_count"] == 2
    assert mvs["study_hours_per_week"]["present_count"] == 1
    assert mvs["study_hours_per_week"]["missing_pct"] == round((2 / 3) * 100.0, 2)

    assert mvs["previous_sgpa"]["missing_count"] == 2
    assert mvs["attendance_pct"]["missing_count"] == 0
    assert mvs["attendance_pct"]["missing_pct"] == 0.0


def test_student_risk_screening_latest_observation_and_optional_columns():
    """Use latest valid observation per student and tolerate missing optional indicators."""
    records = [
        {
            "student_ref": "ANON_001",
            "branch": "CSE",
            "academic_year": 1,
            "semester": 1,
            "attendance_pct": 60,
            "cie_marks_obtained": 10,
            "cie_max_marks": 50,
            "active_backlogs": 2,
        },
        {
            "student_ref": "ANON_001",
            "branch": "CSE",
            "academic_year": 2,
            "semester": 3,
            "attendance_pct": 90,
            "cie_marks_obtained": 40,
            "cie_max_marks": 50,
        },
        {
            "student_ref": "ANON_002",
            "branch": "ECE",
            "academic_year": 1,
            "semester": 1,
            "attendance_pct": 80,
            "cie_marks_obtained": 30,
            "cie_max_marks": 50,
        },
        {
            "student_ref": "ANON_003",
            "branch": "ISE",
            "academic_year": 1,
            "semester": 1,
            "attendance_pct": 92,
            "cie_marks_obtained": 42,
            "cie_max_marks": 50,
        },
    ]

    result = analyze_student_risk_screening(records)
    assert result["total_students"] == 3
    assert result["category_counts"] == {
        "At Risk": {"count": 0, "percentage": 0.0},
        "Moderate Risk": {"count": 1, "percentage": 33.3},
        "Good": {"count": 2, "percentage": 66.7},
    }
    latest = next(row for row in result["records"] if row["student_ref"] == "ANON_001")
    assert latest["semester"] == 3
    assert latest["risk_category"] == "Good"
    assert all("Active backlogs" not in ", ".join(row["main_risk_factors"]) for row in result["records"])


def test_student_risk_screening_empty_dataset_has_zero_counts():
    result = analyze_student_risk_screening([])
    assert result["total_students"] == 0
    assert all(item == {"count": 0, "percentage": 0.0} for item in result["category_counts"].values())
    assert result["records"] == []


def test_student_risk_screening_does_not_return_untrusted_references():
    result = analyze_student_risk_screening([{
        "student_ref": "jane.doe@example.com",
        "branch": "<img src=x onerror=alert(1)>",
        "academic_year": 1,
        "semester": 1,
        "attendance_pct": 90,
        "cie_marks_obtained": 40,
        "cie_max_marks": 50,
    }])
    assert result["records"][0]["student_ref"] == "Reference withheld (1)"
    assert result["records"][0]["branch"] == "<IMG SRC=X ONERROR=ALERT(1)>"
    assert "jane.doe@example.com" not in repr(result["records"])


def test_empty_student_risk_analysis_endpoint_response():
    csv_text = "student_ref,branch,academic_year,semester,attendance_pct,cie_marks_obtained\n"
    response = client.post(
        "/api/ai/college/analyze-dataset",
        files={"file": ("empty_cohort.csv", csv_text.encode("utf-8"), "text/csv")},
    )
    assert response.status_code == 200
    data = response.json()["student_risk_analysis"]
    assert data["total_students"] == 0
    assert data["records"] == []


def test_analyze_csv_critical_missing_values_blocks_readiness():
    """Verify that missing values in mandatory columns (e.g. cie_marks_obtained) block readiness."""
    lines = [
        "student_ref,branch,academic_year,semester,attendance_pct,cie_marks_obtained",
        "STU_001,CSE,1,1,85.0,",             # missing mandatory cie_marks_obtained
        "STU_002,ECE,1,1,90.0,45.0",
    ]
    csv_text = "\n".join(lines)
    files = {"file": ("missing_mandatory.csv", csv_text.encode("utf-8"), "text/csv")}

    response = client.post("/api/ai/college/analyze-dataset", files=files)
    assert response.status_code == 200
    data = response.json()

    ra = data["readiness_assessment"]
    assert ra["status"] == "TRAINING_BLOCKED"
    assert ra["is_ready_for_review"] is False
    assert any("mandatory" in b.lower() or "missing" in b.lower() or "validation" in b.lower() for b in ra["readiness_blockers"])


# =========================================================================
# 3. Duplicate Observations Blocking
# =========================================================================

def test_analyze_csv_duplicate_student_semester_blocked():
    """Verify duplicate observations sharing (student_ref, academic_year, semester) block readiness."""
    lines = [
        "student_ref,branch,academic_year,semester,attendance_pct,cie_marks_obtained",
        "ANON_DUP_01,CSE,2,3,80.0,38.0",
        "ANON_DUP_01,CSE,2,3,82.0,39.0",  # Duplicate key!
        "ANON_UNIQUE_02,ECE,2,3,75.0,30.0",
    ]
    csv_text = "\n".join(lines)
    files = {"file": ("duplicate_keys.csv", csv_text.encode("utf-8"), "text/csv")}

    response = client.post("/api/ai/college/analyze-dataset", files=files)
    assert response.status_code == 200
    data = response.json()

    assert data["duplicate_observations_count"] == 1
    dup = data["duplicate_details"][0]
    assert dup["student_ref"] == "ANON_DUP_01"
    assert dup["semester"] == 3
    assert dup["occurrences"] == 2

    ra = data["readiness_assessment"]
    assert ra["status"] == "TRAINING_BLOCKED"
    assert any("duplicate" in b.lower() for b in ra["readiness_blockers"])
    assert ra["checks"]["duplicates_and_missing_values"]["passed"] is False


# =========================================================================
# 4. Class Imbalance and Defensible Split Blocking
# =========================================================================

def test_analyze_csv_class_imbalance_blocks_readiness():
    """Verify that severe class imbalance (minority < 15) blocks readiness and marks split unviable."""
    lines = [
        "student_ref,branch,academic_year,semester,attendance_pct,cie_marks_obtained,verified_outcome,is_at_risk_label,outcome_source"
    ]
    # 105 Passing students
    for i in range(105):
        lines.append(f"STU_PASS_{i:03d},CSE,2,4,88.0,42.0,PASS,false,OFFICIAL_EXAM_CELL")
    # Only 5 At-Risk students (<15 minority threshold)
    for i in range(5):
        lines.append(f"STU_RISK_{i:03d},ECE,2,4,60.0,18.0,FAIL_OR_DETAINED,true,OFFICIAL_EXAM_CELL")

    csv_text = "\n".join(lines)
    files = {"file": ("imbalanced_cohort.csv", csv_text.encode("utf-8"), "text/csv")}

    response = client.post("/api/ai/college/analyze-dataset", files=files)
    assert response.status_code == 200
    data = response.json()

    cb = data["outcome_and_class_balance"]
    assert cb["at_risk_count"] == 5
    assert cb["passing_count"] == 105

    ra = data["readiness_assessment"]
    assert ra["status"] == "TRAINING_BLOCKED"
    assert ra["is_ready_for_review"] is False
    assert ra["defensible_split_possible"] is False
    assert ra["checks"]["class_imbalance_and_defensible_split"]["passed"] is False
    assert any("class imbalance prevents defensible evaluation split" in b.lower() for b in ra["readiness_blockers"])


# =========================================================================
# 5. Missing Outcome Labels and Target Leakage Blocking
# =========================================================================

def test_analyze_csv_unverified_outcome_labels_blocked():
    """Verify that absence of verified labels (<80 labeled samples) blocks ML readiness."""
    lines = [
        "student_ref,branch,academic_year,semester,attendance_pct,cie_marks_obtained"
    ]
    # 110 unlabelled records
    for i in range(110):
        lines.append(f"ANON_UNLABELED_{i:03d},CSE,2,3,80.0,38.0")

    csv_text = "\n".join(lines)
    files = {"file": ("unlabeled_cohort.csv", csv_text.encode("utf-8"), "text/csv")}

    response = client.post("/api/ai/college/analyze-dataset", files=files)
    assert response.status_code == 200
    data = response.json()

    ra = data["readiness_assessment"]
    assert ra["status"] == "TRAINING_BLOCKED"
    assert ra["checks"]["ground_truth_labels_availability"]["passed"] is False
    assert any("ground-truth" in b.lower() for b in ra["readiness_blockers"])


def test_analyze_csv_potential_target_leakage_blocked():
    """Verify post-examination features trigger target leakage blockers."""
    lines = [
        "student_ref,branch,academic_year,semester,attendance_pct,cie_marks_obtained,see_marks,promotion_status",
        "STU_001,CSE,2,3,80.0,38.0,65.0,PROMOTED",
        "STU_002,ECE,2,3,65.0,20.0,32.0,DETAINED",
    ]
    csv_text = "\n".join(lines)
    files = {"file": ("leaky_post_exam.csv", csv_text.encode("utf-8"), "text/csv")}

    response = client.post("/api/ai/college/analyze-dataset", files=files)
    assert response.status_code == 200
    data = response.json()

    assert len(data["target_leakage_warnings"]) >= 2
    flagged = [w["feature_name"] for w in data["target_leakage_warnings"]]
    assert "see_marks" in flagged
    assert "promotion_status" in flagged

    ra = data["readiness_assessment"]
    assert ra["status"] == "TRAINING_BLOCKED"
    assert ra["checks"]["potential_target_leakage"]["passed"] is False
    assert any("target leakage" in b.lower() for b in ra["readiness_blockers"])


# =========================================================================
# 6. Sample Size and Population Representation Checks
# =========================================================================

def test_analyze_csv_insufficient_sample_size_blocked():
    """Verify datasets smaller than MIN_REQUIRED_SAMPLES (100) are marked TRAINING_BLOCKED."""
    lines = [
        "student_ref,branch,academic_year,semester,attendance_pct,cie_marks_obtained",
        "STU_001,CSE,1,1,85.0,40.0",
        "STU_002,ISE,1,2,78.0,35.0",
        "STU_003,ECE,2,3,92.0,46.0",
    ]
    csv_text = "\n".join(lines)
    files = {"file": ("small_cohort.csv", csv_text.encode("utf-8"), "text/csv")}

    response = client.post("/api/ai/college/analyze-dataset", files=files)
    assert response.status_code == 200
    data = response.json()

    assert data["total_records"] == 3
    ra = data["readiness_assessment"]
    assert ra["status"] == "TRAINING_BLOCKED"
    assert ra["checks"]["sample_size_and_at_risk_counts"]["passed"] is False
    assert any("sample size" in b.lower() for b in ra["readiness_blockers"])


# =========================================================================
# 7. Error Handling (400, 413, 422) and Schema Violations
# =========================================================================

def test_analyze_csv_malformed_input_returns_400():
    """Verify non-CSV format returns 400 Bad Request."""
    files = {"file": ("dataset.json", b'{"not": "csv"}', "application/json")}
    response = client.post("/api/ai/college/analyze-dataset", files=files)
    assert response.status_code == 400
    assert "only .csv files are supported" in response.json()["detail"].lower()


def test_analyze_csv_empty_file_returns_400():
    """Verify empty CSV upload returns 400 Bad Request."""
    files = {"file": ("empty.csv", b"", "text/csv")}
    response = client.post("/api/ai/college/analyze-dataset", files=files)
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_analyze_csv_oversized_upload_returns_413():
    """Verify files larger than 5 MB return 413 Payload Too Large."""
    oversized = b"student_ref,branch,academic_year,semester,attendance_pct,cie_marks_obtained\n" + (
        b"ANON_OVERSIZED,CSE,1,1,80.0,40.0\n" * 200000
    )
    assert len(oversized) > MAX_CSV_FILE_SIZE_BYTES
    files = {"file": ("huge_dataset.csv", oversized, "text/csv")}

    response = client.post("/api/ai/college/analyze-dataset", files=files)
    assert response.status_code == 413
    assert "exceeds maximum allowable limit" in response.json()["detail"].lower()


def test_analyze_csv_missing_required_headers_returns_422():
    """Verify CSV missing required columns returns 422 Unprocessable Entity."""
    csv_text = "student_ref,branch,academic_year,semester\nSTU_001,CSE,1,1\n"
    files = {"file": ("missing_cols.csv", csv_text.encode("utf-8"), "text/csv")}

    response = client.post("/api/ai/college/analyze-dataset", files=files)
    assert response.status_code == 422
    assert "missing required column" in response.json()["detail"].lower()
    assert "attendance_pct" in response.json()["detail"]


def test_analyze_csv_invalid_schemas_and_bounds_reported_without_pii():
    """Verify out-of-range bounds errors are recorded without exposing student PII."""
    csv_text = (
        "student_ref,branch,academic_year,semester,attendance_pct,cie_marks_obtained,cie_max_marks\n"
        "STU_INVALID_ATT,CSE,2,3,130.0,40.0,50.0\n"     # Attendance > 100%
        "STU_INVALID_CIE,ECE,2,3,80.0,60.0,50.0\n"      # CIE > max marks
        "STU_INVALID_SEM,MECH,1,6,85.0,40.0,50.0\n"     # Sem 6 in Year 1!
    )
    files = {"file": ("bounds_errors.csv", csv_text.encode("utf-8"), "text/csv")}

    response = client.post("/api/ai/college/analyze-dataset", files=files)
    assert response.status_code == 200
    data = response.json()

    assert data["total_records"] == 3
    assert data["valid_records_count"] == 0
    assert data["invalid_records_count"] == 3
    assert data["validation_error_rate"] == 1.0

    failures = data["validation_failures_sample"]
    assert len(failures) == 3
    assert failures[0]["row_index"] == 0
    assert any("attendance_pct" in e for e in failures[0]["errors"])
    assert failures[1]["row_index"] == 1
    assert any("CIE marks obtained" in e for e in failures[1]["errors"])
    assert failures[2]["row_index"] == 2
    assert any("Inconsistent semester" in e for e in failures[2]["errors"])

    # Ensure no raw record fields are leaked in failures sample
    for f in failures:
        assert "raw_record" not in f
        assert "student_name" not in f
        assert "email" not in f


# =========================================================================
# 8. Decoupling, MongoDB Preservation & No Model Training
# =========================================================================

def test_analyze_preserves_mongodb_and_no_college_model_trained(valid_120_row_cohort_csv):
    """Verify analyzing a dataset leaves existing MongoDB records completely unaltered and trains no model."""
    initial_count = collection.count_documents({})

    files = {"file": ("eligible_cohort.csv", valid_120_row_cohort_csv.encode("utf-8"), "text/csv")}
    response = client.post("/api/ai/college/analyze-dataset", files=files)
    assert response.status_code == 200

    # 1. MongoDB verification: Count unchanged and all original student documents exist with exact original fields
    final_count = collection.count_documents({})
    assert final_count == initial_count, f"MongoDB collection count changed during dataset analysis! {initial_count} -> {final_count}"

    for usn in ORIGINAL_USNS:
        doc = collection.find_one({"usn": usn})
        assert doc is not None, f"Original student document for USN {usn} was lost!"
        # Verify no college analysis fields were injected into MongoDB
        assert "cie_marks_obtained" not in doc
        assert "is_at_risk_label" not in doc
        assert "verified_outcome" not in doc

    # 2. No college model artifacts were created or written to disk
    artifacts_dir = Path(__file__).resolve().parent.parent / "app" / "ml" / "artifacts"
    college_artifacts = list(artifacts_dir.glob("college_*.joblib"))
    assert len(college_artifacts) == 0, f"Found unexpected college model artifacts: {college_artifacts}"


# =========================================================================
# 9. Phase 9 Hardening: Duplicate Headers, Binary Content, Boundaries & Safety
# =========================================================================

def test_analyze_csv_duplicate_column_headers_returns_422():
    """Verify CSV with duplicate column headers (exact or case-insensitive) returns 422."""
    # Exact duplicate header
    csv_exact_dup = "student_ref,branch,academic_year,semester,attendance_pct,cie_marks_obtained,student_ref\nANON_001,CSE,1,1,85.0,40.0,ANON_001\n"
    files = {"file": ("dup_headers.csv", csv_exact_dup.encode("utf-8"), "text/csv")}
    resp = client.post("/api/ai/college/analyze-dataset", files=files)
    assert resp.status_code == 422
    assert "duplicate column header" in resp.json()["detail"].lower()
    assert "student_ref" in resp.json()["detail"]

    # Case-insensitive duplicate header (Branch vs branch)
    csv_case_dup = "student_ref,Branch,academic_year,semester,attendance_pct,cie_marks_obtained,branch\nANON_001,CSE,1,1,85.0,40.0,CSE\n"
    files2 = {"file": ("case_dup_headers.csv", csv_case_dup.encode("utf-8"), "text/csv")}
    resp2 = client.post("/api/ai/college/analyze-dataset", files=files2)
    assert resp2.status_code == 422
    assert "duplicate column header" in resp2.json()["detail"].lower()


def test_analyze_csv_binary_content_or_null_bytes_returns_400():
    """Verify binary content disguised with a .csv extension returns 400 without crashing."""
    # PNG image header disguised as .csv
    fake_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    files = {"file": ("disguised_image.csv", fake_png, "text/csv")}
    resp = client.post("/api/ai/college/analyze-dataset", files=files)
    assert resp.status_code == 400
    assert "binary or non-text content detected" in resp.json()["detail"].lower()

    # CSV with null byte injection
    corrupted_csv = b"student_ref,branch,academic_year,semester,attendance_pct,cie_marks_obtained\nSTU_001\x00,CSE,1,1,85.0,40.0\n"
    files2 = {"file": ("null_byte.csv", corrupted_csv, "text/csv")}
    resp2 = client.post("/api/ai/college/analyze-dataset", files=files2)
    assert resp2.status_code == 400
    assert "binary or non-text content detected" in resp2.json()["detail"].lower()


def test_analyze_csv_boundary_size_handling():
    """Verify exact 5 MB boundary is accepted, while 5 MB + 1 byte returns HTTP 413."""
    header = "student_ref,branch,academic_year,semester,attendance_pct,cie_marks_obtained\n"
    row = "ANON_BOUND,CSE,1,1,85.0,40.0\n"
    base_content = header + row
    base_bytes = base_content.encode("utf-8")
    # Pad with newlines up to exactly MAX_CSV_FILE_SIZE_BYTES (5 MB)
    padding_needed = MAX_CSV_FILE_SIZE_BYTES - len(base_bytes)
    assert padding_needed > 0
    exact_5mb_bytes = base_bytes + (b"\n" * padding_needed)
    assert len(exact_5mb_bytes) == MAX_CSV_FILE_SIZE_BYTES

    files_exact = {"file": ("boundary_exact_5mb.csv", exact_5mb_bytes, "text/csv")}
    resp_exact = client.post("/api/ai/college/analyze-dataset", files=files_exact)
    # Must NOT be 413 Payload Too Large
    assert resp_exact.status_code != 413
    assert resp_exact.status_code == 200

    # Exceeding by exactly 1 byte: 5,242,881 bytes
    oversized_bytes = exact_5mb_bytes + b"X"
    assert len(oversized_bytes) == MAX_CSV_FILE_SIZE_BYTES + 1
    files_over = {"file": ("boundary_oversized.csv", oversized_bytes, "text/csv")}
    resp_over = client.post("/api/ai/college/analyze-dataset", files=files_over)
    assert resp_over.status_code == 413
    assert "exceeds maximum allowable limit" in resp_over.json()["detail"].lower()


def test_analyze_csv_invalid_boolean_and_outcome_labels_handled_safely():
    """Verify invalid label values and unsupported outcomes are recorded as validation failures safely."""
    csv_text = (
        "student_ref,branch,academic_year,semester,attendance_pct,cie_marks_obtained,is_at_risk_label,verified_outcome,outcome_source\n"
        "STU_001,CSE,1,1,85.0,40.0,maybe,PASS,OFFICIAL_EXAM_CELL\n"                # Invalid boolean 'maybe'
        "STU_002,ECE,1,1,88.0,42.0,false,UNSUPPORTED_OUTCOME,OFFICIAL_EXAM_CELL\n"  # Unsupported outcome literal
        "STU_003,ISE,1,2,90.0,45.0,false,PASS,OFFICIAL_EXAM_CELL\n"                # Valid row
    )
    files = {"file": ("bad_labels.csv", csv_text.encode("utf-8"), "text/csv")}
    resp = client.post("/api/ai/college/analyze-dataset", files=files)
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_records"] == 3
    assert data["valid_records_count"] == 1
    assert data["invalid_records_count"] == 2
    assert len(data["validation_failures_sample"]) == 2
    # Ensure error details contain the specific issue without exposing sensitive internal data
    failures = data["validation_failures_sample"]
    assert any("boolean" in err.lower() for err in failures[0]["errors"])
    assert any("verified_outcome" in err.lower() or "literal" in err.lower() or "input should be" in err.lower() for err in failures[1]["errors"])


def test_analyze_csv_safe_error_responses_no_sensitive_leakage():
    """Verify error responses never expose database URIs, passwords, or Python tracebacks."""
    # 400 Bad Request
    files_bad = {"file": ("empty.csv", b"", "text/csv")}
    resp = client.post("/api/ai/college/analyze-dataset", files=files_bad)
    assert resp.status_code == 400
    detail = resp.json().get("detail", "")
    assert "Traceback" not in detail
    assert "mongodb" not in detail.lower()
    assert "password" not in detail.lower()

    # 422 Missing headers
    files_missing = {"file": ("missing.csv", b"col_a,col_b\n1,2\n", "text/csv")}
    resp_missing = client.post("/api/ai/college/analyze-dataset", files=files_missing)
    assert resp_missing.status_code == 422
    detail_missing = resp_missing.json().get("detail", "")
    assert "Traceback" not in detail_missing
    assert "mongodb" not in detail_missing.lower()
