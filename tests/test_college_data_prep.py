"""Automated Test Suite for Engineering College Data Preparation & ML Readiness (Phase 6).

Validates:
1. Valid and invalid college academic observation schemas.
2. Numeric range and bounds validation (attendance, CIE, CGPA, backlogs).
3. Domain consistency enforcement (semester vs academic year, semester 1 prior GPA/backlog rules).
4. Ground-truth label and outcome audit source requirements.
5. Duplicate observation detection via composite key.
6. Target leakage detection for future-information and post-examination features.
7. Class balance analysis on labeled records.
8. Comprehensive dataset quality audit and ML training readiness evaluation (blocking vs ready).
9. Decoupling and preservation of existing MongoDB student records and CRUD endpoints.
"""

import pytest
from app.database.connection import collection
from app.models.college_schemas import CollegeAcademicObservation
from app.ml.college_data_prep import (
    analyze_college_dataset,
    check_class_balance,
    detect_duplicate_observations,
    detect_target_leakage_risks,
    validate_college_observation,
)

ORIGINAL_USNS = ["1DB24IS045", "1DB23IS001", "1DB25EC096", "1DB25CS009", "1DB23IS069", "1DB22CS020"]


@pytest.fixture
def sample_valid_synthetic_record() -> dict:
    """Synthetic engineering student record for semester 3 (Year 2)."""
    return {
        "student_ref": "SYNTH_STUDENT_001",
        "program": "B.Tech",
        "branch": "CSE",
        "academic_year": 2,
        "semester": 3,
        "attendance_pct": 82.5,
        "cie_marks_obtained": 41.0,
        "cie_max_marks": 50.0,
        "assignment_score_avg": 88.0,
        "previous_sgpa": 8.2,
        "cumulative_cgpa": 8.05,
        "gpa_scale_max": 10.0,
        "active_backlogs": 0,
        "credits_registered": 22.0,
        "credits_earned_prior": 40.0,
        "study_hours_per_week": 14.0,
    }


# =========================================================================
# 1. Schema Validation and Field Parsing
# =========================================================================

def test_valid_college_academic_observation(sample_valid_synthetic_record):
    """Verify that a well-formed college academic record passes validation."""
    obs, errors = validate_college_observation(sample_valid_synthetic_record)
    assert errors == []
    assert obs is not None
    assert obs.student_ref == "SYNTH_STUDENT_001"
    assert obs.academic_year == 2
    assert obs.semester == 3
    assert obs.normalized_cie_pct == 82.0
    assert obs.observation_key == ("SYNTH_STUDENT_001", 2, 3)


def test_pseudonymous_student_ref_normalization():
    """Verify student_ref is stripped and converted to uppercase."""
    record = {
        "student_ref": "   anon_stu_99   ",
        "branch": "ise",
        "academic_year": 1,
        "semester": 1,
        "attendance_pct": 90.0,
        "cie_marks_obtained": 45.0,
        "cie_max_marks": 50.0,
    }
    obs, errors = validate_college_observation(record)
    assert errors == []
    assert obs.student_ref == "ANON_STU_99"
    assert obs.branch == "ISE"


# =========================================================================
# 2. Numeric Range and Bounds Validation
# =========================================================================

def test_attendance_range_bounds(sample_valid_synthetic_record):
    """Verify attendance must be within [0.0, 100.0]."""
    # Exceeds 100%
    bad_high = sample_valid_synthetic_record.copy()
    bad_high["attendance_pct"] = 105.0
    _, errors = validate_college_observation(bad_high)
    assert any("attendance_pct" in e for e in errors)

    # Negative attendance
    bad_neg = sample_valid_synthetic_record.copy()
    bad_neg["attendance_pct"] = -5.0
    _, errors = validate_college_observation(bad_neg)
    assert any("attendance_pct" in e for e in errors)


def test_cie_marks_obtained_cannot_exceed_max_marks(sample_valid_synthetic_record):
    """Verify that CIE marks obtained > CIE max marks is rejected."""
    bad_cie = sample_valid_synthetic_record.copy()
    bad_cie["cie_marks_obtained"] = 55.0  # Max is 50.0
    _, errors = validate_college_observation(bad_cie)
    assert any("cannot exceed maximum CIE marks" in e for e in errors)


def test_cgpa_range_bounds(sample_valid_synthetic_record):
    """Verify 10-point GPA scale bounds (cannot exceed 10.0 or be negative)."""
    bad_gpa = sample_valid_synthetic_record.copy()
    bad_gpa["previous_sgpa"] = 11.5
    _, errors = validate_college_observation(bad_gpa)
    assert any("previous_sgpa" in e for e in errors)


def test_backlog_count_bounds(sample_valid_synthetic_record):
    """Verify backlog count cannot be negative."""
    bad_backlog = sample_valid_synthetic_record.copy()
    bad_backlog["active_backlogs"] = -1
    _, errors = validate_college_observation(bad_backlog)
    assert any("active_backlogs" in e for e in errors)


# =========================================================================
# 3. Domain Consistency Rules
# =========================================================================

def test_semester_vs_academic_year_inconsistency(sample_valid_synthetic_record):
    """Verify semester 5 cannot belong to academic year 1."""
    inconsistent = sample_valid_synthetic_record.copy()
    inconsistent["academic_year"] = 1
    inconsistent["semester"] = 5
    _, errors = validate_college_observation(inconsistent)
    assert any("Inconsistent semester" in e for e in errors)


def test_semester_1_cannot_have_prior_sgpa_or_backlogs():
    """Verify semester 1 students cannot have a prior college SGPA or prior backlogs."""
    sem1_bad_gpa = {
        "student_ref": "SYNTH_FIRST_YEAR",
        "branch": "CSE",
        "academic_year": 1,
        "semester": 1,
        "attendance_pct": 85.0,
        "cie_marks_obtained": 38.0,
        "cie_max_marks": 50.0,
        "previous_sgpa": 7.5,  # Invalid for semester 1!
    }
    _, errors_gpa = validate_college_observation(sem1_bad_gpa)
    assert any("First semester students cannot have a prior college SGPA" in e for e in errors_gpa)

    sem1_bad_backlogs = {
        "student_ref": "SYNTH_FIRST_YEAR",
        "branch": "CSE",
        "academic_year": 1,
        "semester": 1,
        "attendance_pct": 85.0,
        "cie_marks_obtained": 38.0,
        "cie_max_marks": 50.0,
        "active_backlogs": 2,  # Invalid for semester 1!
    }
    _, errors_bl = validate_college_observation(sem1_bad_backlogs)
    assert any("First semester students cannot have prior college backlogs" in e for e in errors_bl)


def test_verified_outcome_requires_audit_source():
    """Verify that specifying verified_outcome without outcome_source raises an error."""
    unverified_label = {
        "student_ref": "SYNTH_LABELED_001",
        "branch": "ECE",
        "academic_year": 2,
        "semester": 4,
        "attendance_pct": 78.0,
        "cie_marks_obtained": 32.0,
        "cie_max_marks": 50.0,
        "verified_outcome": "PASS",
        # outcome_source intentionally omitted
    }
    _, errors = validate_college_observation(unverified_label)
    assert any("outcome_source must be documented" in e for e in errors)


# =========================================================================
# 4. Duplicate Detection
# =========================================================================

def test_duplicate_observation_detection(sample_valid_synthetic_record):
    """Verify that multiple records sharing (student_ref, year, semester) are detected."""
    rec1 = sample_valid_synthetic_record.copy()
    rec2 = sample_valid_synthetic_record.copy()
    rec2["attendance_pct"] = 85.0  # slightly perturbed duplicate

    obs1, _ = validate_college_observation(rec1)
    obs2, _ = validate_college_observation(rec2)

    duplicates = detect_duplicate_observations([obs1, obs2])
    assert len(duplicates) == 1
    assert duplicates[0]["student_ref"] == "SYNTH_STUDENT_001"
    assert duplicates[0]["academic_year"] == 2
    assert duplicates[0]["semester"] == 3
    assert duplicates[0]["occurrences"] == 2
    assert duplicates[0]["row_indices"] == [0, 1]


# =========================================================================
# 5. Target Leakage Inspection
# =========================================================================

def test_target_leakage_detection():
    """Verify that post-examination and end-term features are flagged as leakage."""
    suspicious_columns = [
        "attendance_pct",
        "cie_marks_obtained",
        "see_marks",              # Leakage!
        "end_sem_marks",          # Leakage!
        "current_sem_sgpa",       # Leakage!
        "promotion_status",       # Leakage!
        "previous_sgpa"           # Legitimate historical feature
    ]
    flagged = detect_target_leakage_risks(suspicious_columns)
    flagged_names = [f["feature_name"] for f in flagged]

    assert "see_marks" in flagged_names
    assert "end_sem_marks" in flagged_names
    assert "current_sem_sgpa" in flagged_names
    assert "promotion_status" in flagged_names
    assert "attendance_pct" not in flagged_names
    assert "cie_marks_obtained" not in flagged_names
    assert "previous_sgpa" not in flagged_names


# =========================================================================
# 6. Class Balance Analysis
# =========================================================================

def test_class_balance_calculation():
    """Verify class balance computation on synthetic labeled records."""
    records = []
    # 3 Passing students
    for i in range(3):
        records.append(CollegeAcademicObservation(
            student_ref=f"PASS_STU_{i}",
            branch="CSE",
            academic_year=2,
            semester=3,
            attendance_pct=85.0,
            cie_marks_obtained=42.0,
            cie_max_marks=50.0,
            verified_outcome="PASS",
            is_at_risk_label=False,
            outcome_source="OFFICIAL_EXAM_CELL"
        ))
    # 2 At-risk students
    for i in range(2):
        records.append(CollegeAcademicObservation(
            student_ref=f"FAIL_STU_{i}",
            branch="CSE",
            academic_year=2,
            semester=3,
            attendance_pct=60.0,
            cie_marks_obtained=18.0,
            cie_max_marks=50.0,
            verified_outcome="FAIL_OR_DETAINED",
            is_at_risk_label=True,
            outcome_source="OFFICIAL_EXAM_CELL"
        ))

    balance = check_class_balance(records)
    assert balance["total_records"] == 5
    assert balance["labeled_records_count"] == 5
    assert balance["binary_risk_distribution"]["at_risk_true_count"] == 2
    assert balance["binary_risk_distribution"]["at_risk_false_count"] == 3
    assert balance["binary_risk_distribution"]["at_risk_ratio"] == 0.40
    assert balance["verified_outcome_breakdown"]["PASS"] == 3
    assert balance["verified_outcome_breakdown"]["FAIL_OR_DETAINED"] == 2


# =========================================================================
# 7. Dataset Quality Audit & ML Training Readiness (Blocked vs Ready)
# =========================================================================

def test_dataset_analysis_blocked_on_small_synthetic_sample(sample_valid_synthetic_record):
    """Verify that an insufficient dataset (<100 samples, unlabeled) is marked as TRAINING_BLOCKED."""
    small_batch = [sample_valid_synthetic_record.copy() for _ in range(5)]
    # Make refs unique so they are not duplicates
    for idx, r in enumerate(small_batch):
        r["student_ref"] = f"SYNTH_{idx}"

    report = analyze_college_dataset(small_batch, dataset_name="Small Synthetic Test Batch")
    assert report["total_records"] == 5
    assert report["valid_records_count"] == 5
    assert report["ml_readiness"]["is_ready_for_training"] is False
    assert report["ml_readiness"]["status"] == "TRAINING_BLOCKED"
    assert len(report["ml_readiness"]["blocking_reasons"]) >= 2
    # Check that reasons cite sample size and missing ground truth
    combined_reasons = " ".join(report["ml_readiness"]["blocking_reasons"]).lower()
    assert "insufficient sample size" in combined_reasons
    assert "ground-truth" in combined_reasons


def test_dataset_analysis_ready_when_criteria_satisfied():
    """Verify that a synthetic dataset satisfying all 6 criteria is marked as READY_FOR_COLLEGE_MODEL_TRAINING."""
    large_batch = []
    # Create 120 valid records: 80 passing, 40 at-risk (satisfies min 100 samples, min 80 labeled, min 15 minority)
    for i in range(80):
        large_batch.append({
            "student_ref": f"SYNTH_PASS_{i}",
            "branch": "CSE",
            "academic_year": 2,
            "semester": 4,
            "attendance_pct": 88.0,
            "cie_marks_obtained": 40.0,
            "cie_max_marks": 50.0,
            "previous_sgpa": 8.0,
            "cumulative_cgpa": 7.9,
            "active_backlogs": 0,
            "verified_outcome": "PASS",
            "is_at_risk_label": False,
            "outcome_source": "OFFICIAL_EXAM_CELL"
        })
    for i in range(40):
        large_batch.append({
            "student_ref": f"SYNTH_RISK_{i}",
            "branch": "ECE",
            "academic_year": 2,
            "semester": 4,
            "attendance_pct": 65.0,
            "cie_marks_obtained": 20.0,
            "cie_max_marks": 50.0,
            "previous_sgpa": 5.2,
            "cumulative_cgpa": 5.4,
            "active_backlogs": 3,
            "verified_outcome": "FAIL_OR_DETAINED",
            "is_at_risk_label": True,
            "outcome_source": "OFFICIAL_EXAM_CELL"
        })

    report = analyze_college_dataset(large_batch, dataset_name="Eligible Synthetic Training Batch")
    assert report["total_records"] == 120
    assert report["valid_records_count"] == 120
    assert report["invalid_records_count"] == 0
    assert report["duplicate_observations_count"] == 0
    assert len(report["target_leakage_warnings"]) == 0
    assert report["ml_readiness"]["is_ready_for_training"] is True
    assert report["ml_readiness"]["status"] == "READY_FOR_COLLEGE_MODEL_TRAINING"
    assert len(report["ml_readiness"]["blocking_reasons"]) == 0


# =========================================================================
# 8. Decoupling and MongoDB Integrity Preservation
# =========================================================================

def test_original_mongodb_records_unaltered_by_phase_6():
    """Verify that none of the 6 original MongoDB records were modified, migrated, or injected with Phase 6 fields."""
    for usn in ORIGINAL_USNS:
        record = collection.find_one({"usn": usn})
        assert record is not None, f"Original USN {usn} was lost!"
        assert "verified_outcome" not in record
        assert "is_at_risk_label" not in record
        assert "cie_marks_obtained" not in record
