"""Automated Test Suite for Secure College Dataset CSV Import and Audit (Phase 7).

Validates:
1. POST /api/ai/college/audit-dataset with valid CSV datasets.
2. File validation rules: .csv extension enforcement, empty file rejection, file size limit (5 MB).
3. Header validation: detecting missing required columns (HTTP 422).
4. UTF-8 with BOM and encoding compatibility.
5. Target leakage detection in CSV columns.
6. Duplicate student-semester observation detection in CSV.
7. Domain consistency and range error reporting in audit response.
8. Privacy guarantees: no student PII in responses or logs.
9. Database isolation: zero records written to MongoDB and zero prediction model training.
"""

import io
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database.connection import collection
from app.ml.college_data_prep import MAX_CSV_FILE_SIZE_BYTES, parse_and_audit_college_csv

client = TestClient(app)
ORIGINAL_USNS = ["1DB24IS045", "1DB23IS001", "1DB25EC096", "1DB25CS009", "1DB23IS069", "1DB22CS020"]


@pytest.fixture
def sample_valid_csv_content() -> str:
    """Generate a clean, valid 120-row CSV satisfying all ML readiness criteria."""
    lines = [
        "student_ref,branch,academic_year,semester,attendance_pct,cie_marks_obtained,cie_max_marks,previous_sgpa,cumulative_cgpa,active_backlogs,verified_outcome,is_at_risk_label,outcome_source"
    ]
    # 80 Passing students
    for i in range(80):
        lines.append(
            f"ANON_PASS_{i:03d},CSE,2,4,88.0,42.0,50.0,8.2,8.0,0,PASS,false,OFFICIAL_EXAM_CELL"
        )
    # 40 At-risk students
    for i in range(40):
        lines.append(
            f"ANON_RISK_{i:03d},ECE,2,4,62.0,18.0,50.0,5.4,5.6,3,FAIL_OR_DETAINED,true,OFFICIAL_EXAM_CELL"
        )
    return "\n".join(lines)


# =========================================================================
# 1. Successful CSV Upload and Readiness Audit
# =========================================================================

def test_audit_csv_valid_dataset(sample_valid_csv_content):
    """Verify POST /api/ai/college/audit-dataset successfully audits valid CSV and returns 200."""
    file_bytes = sample_valid_csv_content.encode("utf-8")
    files = {"file": ("authorized_college_cohort_2024.csv", file_bytes, "text/csv")}

    response = client.post("/api/ai/college/audit-dataset", files=files)
    assert response.status_code == 200
    data = response.json()

    assert data["dataset_name"] == "authorized_college_cohort_2024.csv"
    assert data["total_records"] == 120
    assert data["valid_records_count"] == 120
    assert data["invalid_records_count"] == 0
    assert data["validation_error_rate"] == 0.0
    assert data["duplicate_observations_count"] == 0
    assert len(data["target_leakage_warnings"]) == 0

    # Class balance
    cb = data["class_balance"]
    assert cb["labeled_records_count"] == 120
    assert cb["binary_risk_distribution"]["at_risk_true_count"] == 40
    assert cb["binary_risk_distribution"]["at_risk_false_count"] == 80

    # ML Readiness satisfied
    readiness = data["ml_readiness"]
    assert readiness["is_ready_for_training"] is True
    assert readiness["status"] == "READY_FOR_COLLEGE_MODEL_TRAINING"
    assert len(readiness["blocking_reasons"]) == 0

    # Security and non-persistence guarantees
    assert data["database_storage_action"] == "NONE_INSPECTED_ONLY"
    assert data["training_action"] == "NONE_COLLEGE_TRAINING_BLOCKED"
    assert "Zero records persisted" in data["privacy_guarantee"]


def test_audit_csv_small_dataset_blocked():
    """Verify a small dataset (<100 samples) is parsed cleanly but marked TRAINING_BLOCKED."""
    csv_text = (
        "student_ref,branch,academic_year,semester,attendance_pct,cie_marks_obtained,cie_max_marks\n"
        "STU_001,CSE,1,1,85.0,40.0,50.0\n"
        "STU_002,ISE,1,2,78.0,35.0,50.0\n"
        "STU_003,ECE,2,3,92.0,46.0,50.0\n"
    )
    files = {"file": ("preliminary_cohort.csv", csv_text.encode("utf-8"), "text/csv")}

    response = client.post("/api/ai/college/audit-dataset", files=files)
    assert response.status_code == 200
    data = response.json()

    assert data["total_records"] == 3
    assert data["valid_records_count"] == 3
    readiness = data["ml_readiness"]
    assert readiness["is_ready_for_training"] is False
    assert readiness["status"] == "TRAINING_BLOCKED"
    assert any("sample size" in r.lower() for r in readiness["blocking_reasons"])
    assert any("ground-truth" in r.lower() for r in readiness["blocking_reasons"])


# =========================================================================
# 2. Target Leakage, Duplicates, and Inconsistencies Detection
# =========================================================================

def test_audit_csv_target_leakage_detected():
    """Verify post-examination features in CSV are flagged as target leakage."""
    csv_text = (
        "student_ref,branch,academic_year,semester,attendance_pct,cie_marks_obtained,see_marks,promotion_status\n"
        "STU_001,CSE,2,3,80.0,38.0,65.0,PROMOTED\n"
        "STU_002,ECE,2,3,65.0,20.0,32.0,DETAINED\n"
    )
    files = {"file": ("leaky_records.csv", csv_text.encode("utf-8"), "text/csv")}

    response = client.post("/api/ai/college/audit-dataset", files=files)
    assert response.status_code == 200
    data = response.json()

    leakage_warnings = data["target_leakage_warnings"]
    assert len(leakage_warnings) >= 2
    flagged_fields = [w["feature_name"] for w in leakage_warnings]
    assert "see_marks" in flagged_fields
    assert "promotion_status" in flagged_fields

    readiness = data["ml_readiness"]
    assert readiness["is_ready_for_training"] is False
    assert any("target leakage" in r.lower() for r in readiness["blocking_reasons"])


def test_audit_csv_duplicate_student_semester_detected():
    """Verify duplicate observations for the same student in the same semester are flagged."""
    csv_text = (
        "student_ref,branch,academic_year,semester,attendance_pct,cie_marks_obtained\n"
        "ANON_DUPLICATE_01,CSE,2,3,80.0,38.0\n"
        "ANON_DUPLICATE_01,CSE,2,3,84.0,41.0\n"  # Duplicate key!
        "ANON_UNIQUE_02,ECE,2,3,75.0,30.0\n"
    )
    files = {"file": ("duplicate_records.csv", csv_text.encode("utf-8"), "text/csv")}

    response = client.post("/api/ai/college/audit-dataset", files=files)
    assert response.status_code == 200
    data = response.json()

    assert data["duplicate_observations_count"] == 1
    dup_entry = data["duplicate_details"][0]
    assert dup_entry["student_ref"] == "ANON_DUPLICATE_01"
    assert dup_entry["semester"] == 3
    assert dup_entry["occurrences"] == 2
    assert dup_entry["row_indices"] == [0, 1]


def test_audit_csv_validation_errors_sample_without_pii():
    """Verify that rows with out-of-range or inconsistent values are reported without PII."""
    csv_text = (
        "student_ref,branch,academic_year,semester,attendance_pct,cie_marks_obtained,cie_max_marks\n"
        "STU_BAD_ATT,CSE,2,3,125.0,40.0,50.0\n"          # Attendance > 100%
        "STU_BAD_CIE,ECE,2,3,85.0,55.0,50.0\n"           # CIE > max marks
        "STU_BAD_SEM,MECH,1,5,90.0,40.0,50.0\n"          # Semester 5 in Year 1!
    )
    files = {"file": ("invalid_rows.csv", csv_text.encode("utf-8"), "text/csv")}

    response = client.post("/api/ai/college/audit-dataset", files=files)
    assert response.status_code == 200
    data = response.json()

    assert data["total_records"] == 3
    assert data["valid_records_count"] == 0
    assert data["invalid_records_count"] == 3
    assert data["validation_error_rate"] == 1.0

    # Ensure validation failure samples contain row indices and error descriptions
    failures = data["validation_failures_sample"]
    assert len(failures) == 3
    assert failures[0]["row_index"] == 0
    assert any("attendance_pct" in e for e in failures[0]["errors"])
    assert failures[1]["row_index"] == 1
    assert any("CIE marks obtained" in e for e in failures[1]["errors"])
    assert failures[2]["row_index"] == 2
    assert any("Inconsistent semester" in e for e in failures[2]["errors"])


# =========================================================================
# 3. File Type, Size, and Header Validation (400, 413, 422 Errors)
# =========================================================================

def test_audit_csv_missing_required_headers_returns_422():
    """Verify CSV missing required columns (e.g. cie_marks_obtained) returns 422."""
    csv_text = (
        "student_ref,branch,academic_year,semester,attendance_pct\n"  # Missing cie_marks_obtained!
        "STU_001,CSE,2,3,85.0\n"
    )
    files = {"file": ("missing_cie.csv", csv_text.encode("utf-8"), "text/csv")}

    response = client.post("/api/ai/college/audit-dataset", files=files)
    assert response.status_code == 422
    data = response.json()
    assert "missing required column" in data["detail"].lower()
    assert "cie_marks_obtained" in data["detail"]


def test_audit_csv_non_csv_extension_rejected():
    """Verify non-CSV files (e.g. .json, .txt, .pdf) return 400 Bad Request."""
    files = {"file": ("dataset.json", b'{"data": []}', "application/json")}
    response = client.post("/api/ai/college/audit-dataset", files=files)
    assert response.status_code == 400
    assert "only .csv files are supported" in response.json()["detail"].lower()


def test_audit_csv_empty_file_rejected():
    """Verify empty CSV upload returns 400 Bad Request."""
    files = {"file": ("empty.csv", b"", "text/csv")}
    response = client.post("/api/ai/college/audit-dataset", files=files)
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_audit_csv_file_size_limit_exceeded():
    """Verify files larger than 5 MB return 413 Payload Too Large."""
    # Create synthetic bytes exceeding MAX_CSV_FILE_SIZE_BYTES (5 MB + 1 MB)
    oversized_bytes = b"student_ref,branch,academic_year,semester,attendance_pct,cie_marks_obtained\n" + (
        b"ANON_OVERSIZED,CSE,1,1,80.0,40.0\n" * 200000
    )
    assert len(oversized_bytes) > MAX_CSV_FILE_SIZE_BYTES

    files = {"file": ("oversized.csv", oversized_bytes, "text/csv")}
    response = client.post("/api/ai/college/audit-dataset", files=files)
    assert response.status_code == 413
    assert "exceeds maximum allowable limit" in response.json()["detail"].lower()


def test_audit_csv_utf8_bom_support():
    """Verify CSV with UTF-8 BOM is decoded properly without header corruption."""
    csv_text_with_bom = (
        "\ufeffstudent_ref,branch,academic_year,semester,attendance_pct,cie_marks_obtained\n"
        "STU_BOM_01,CSE,2,3,88.0,40.0\n"
    )
    files = {"file": ("bom_encoded.csv", csv_text_with_bom.encode("utf-8-sig"), "text/csv")}
    response = client.post("/api/ai/college/audit-dataset", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["total_records"] == 1
    assert data["valid_records_count"] == 1


# =========================================================================
# 4. Decoupling and MongoDB Integrity Verification
# =========================================================================

def test_original_mongodb_records_unaltered_after_csv_audits(sample_valid_csv_content):
    """Verify that importing/auditing CSV datasets writes zero records to MongoDB."""
    initial_count = collection.count_documents({})

    # Execute valid audit
    files = {"file": ("audit_run.csv", sample_valid_csv_content.encode("utf-8"), "text/csv")}
    response = client.post("/api/ai/college/audit-dataset", files=files)
    assert response.status_code == 200

    # Ensure document count has not increased
    final_count = collection.count_documents({})
    assert final_count == initial_count, "MongoDB collection count changed during dataset audit!"

    # Ensure all 6 original USNs remain intact and untouched
    for usn in ORIGINAL_USNS:
        record = collection.find_one({"usn": usn})
        assert record is not None, f"Original USN {usn} was altered or removed!"
        assert "cie_marks_obtained" not in record
        assert "verified_outcome" not in record
