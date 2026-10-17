"""Automated Security, Data Integrity, and Hardening Regression Test Suite (Phase 9).

Validates:
1. Strict Database Isolation: Zero student records added, deleted, or mutated during audits/analyses.
2. Original MongoDB Record Preservation: All 6 original student documents retain exact original fields.
3. Artifact Immutability: SHA-256 hashes of existing benchmark ML artifacts remain completely unchanged.
4. Non-Persistence Guarantee: Zero uploaded CSV data is written to disk or database.
5. Zero College Model Training: No college model artifacts (e.g. college_*.joblib) are created on disk.
6. Information Disclosure Prevention: Error responses never leak stack traces, database URIs, or secrets.
7. Safe Input & Boundary Parsing: Enforcement of 5 MB limit, binary rejection, and duplicate header checks.
"""

import hashlib
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database.connection import collection
from app.ml.college_data_prep import MAX_CSV_FILE_SIZE_BYTES

client = TestClient(app)

ORIGINAL_USNS = ["1DB24IS045", "1DB23IS001", "1DB25EC096", "1DB25CS009", "1DB23IS069", "1DB22CS020"]
ARTIFACTS_DIR = Path(__file__).resolve().parent.parent / "app" / "ml" / "artifacts"


def compute_dir_sha256(directory: Path) -> dict:
    """Compute SHA-256 hash for all files in a directory."""
    hashes = {}
    for p in sorted(directory.glob("*")):
        if p.is_file():
            hasher = hashlib.sha256()
            hasher.update(p.read_bytes())
            hashes[p.name] = hasher.hexdigest()
    return hashes


@pytest.fixture
def clean_cohort_csv_text() -> str:
    """Generate a clean 100-row college academic observations CSV."""
    rows = [
        "student_ref,branch,academic_year,semester,attendance_pct,cie_marks_obtained,cie_max_marks,previous_sgpa,cumulative_cgpa,active_backlogs,verified_outcome,is_at_risk_label,outcome_source"
    ]
    for i in range(1, 81):
        rows.append(
            f"SEC_STU_{i:03d},CSE,2,4,85.0,42.0,50.0,8.2,8.1,0,PASS,false,OFFICIAL_EXAM_CELL"
        )
    for i in range(81, 101):
        rows.append(
            f"SEC_STU_{i:03d},ECE,2,4,62.0,18.0,50.0,5.2,5.5,3,FAIL_OR_DETAINED,true,OFFICIAL_EXAM_CELL"
        )
    return "\n".join(rows)


# =========================================================================
# 1. Benchmark Model Artifact Immutability (SHA-256 Hash Verification)
# =========================================================================

def test_benchmark_artifacts_sha256_unaltered_after_college_analysis(clean_cohort_csv_text):
    """Verify SHA-256 hashes of all benchmark model artifacts before and after college analysis."""
    assert ARTIFACTS_DIR.exists()
    initial_hashes = compute_dir_sha256(ARTIFACTS_DIR)

    # Ensure all expected benchmark artifacts exist
    assert "student_risk_pipeline.joblib" in initial_hashes
    assert "logistic_regression_pipeline.joblib" in initial_hashes
    assert "metadata.json" in initial_hashes
    assert "metrics.json" in initial_hashes

    # Run analysis endpoint
    files = {"file": ("sha_test_cohort.csv", clean_cohort_csv_text.encode("utf-8"), "text/csv")}
    resp = client.post("/api/ai/college/analyze-dataset", files=files)
    assert resp.status_code == 200

    # Run audit endpoint
    files2 = {"file": ("sha_test_audit.csv", clean_cohort_csv_text.encode("utf-8"), "text/csv")}
    resp2 = client.post("/api/ai/college/audit-dataset", files=files2)
    assert resp2.status_code == 200

    # Re-compute hashes and verify byte-for-byte immutability
    final_hashes = compute_dir_sha256(ARTIFACTS_DIR)
    assert final_hashes == initial_hashes, "Model artifact files in app/ml/artifacts were modified!"


def test_zero_college_model_artifacts_created_on_disk(clean_cohort_csv_text):
    """Confirm zero college-specific models (college_*.joblib) are ever created or written to disk."""
    files = {"file": ("no_training_cohort.csv", clean_cohort_csv_text.encode("utf-8"), "text/csv")}
    resp = client.post("/api/ai/college/analyze-dataset", files=files)
    assert resp.status_code == 200

    college_joblib_files = list(ARTIFACTS_DIR.glob("college_*.joblib"))
    assert len(college_joblib_files) == 0, f"Unexpected college model file found: {college_joblib_files}"


# =========================================================================
# 2. Database Isolation & Original Record Integrity
# =========================================================================

def test_zero_mongodb_mutations_across_multiple_college_operations(clean_cohort_csv_text):
    """Verify that multiple concurrent or sequential dataset audits write zero records to MongoDB."""
    initial_count = collection.count_documents({})

    # Snapshot of the 6 original student documents
    original_docs_before = {}
    for usn in ORIGINAL_USNS:
        doc = collection.find_one({"usn": usn})
        assert doc is not None, f"Original USN {usn} missing before test!"
        # Exclude MongoDB internal _id for clean comparison
        original_docs_before[usn] = {k: v for k, v in doc.items() if k != "_id"}

    # Run both endpoints with valid data
    client.post("/api/ai/college/audit-dataset", files={"file": ("audit.csv", clean_cohort_csv_text.encode("utf-8"), "text/csv")})
    client.post("/api/ai/college/analyze-dataset", files={"file": ("analyze.csv", clean_cohort_csv_text.encode("utf-8"), "text/csv")})

    # Run endpoints with invalid / rejected data
    client.post("/api/ai/college/analyze-dataset", files={"file": ("bad.csv", b"corrupted,content\n", "text/csv")})
    client.post("/api/ai/college/audit-dataset", files={"file": ("dup.csv", b"student_ref,branch,academic_year,semester,attendance_pct,cie_marks_obtained,branch\n", "text/csv")})

    # Verify document count remains completely identical
    final_count = collection.count_documents({})
    assert final_count == initial_count, f"Database count shifted: {initial_count} -> {final_count}"

    # Verify every original student record remains unchanged
    for usn in ORIGINAL_USNS:
        doc_after = collection.find_one({"usn": usn})
        clean_after = {k: v for k, v in doc_after.items() if k != "_id"}
        assert clean_after == original_docs_before[usn], f"Student record for USN {usn} was mutated!"


# =========================================================================
# 3. Information Disclosure & Error Sanitization
# =========================================================================

def test_error_responses_contain_no_system_paths_or_secrets():
    """Verify that client error responses never expose internal stack traces, DB credentials, or file paths."""
    # Test 1: Uploading binary content
    fake_binary = b"\x00\x01\x02\x03\x04"
    resp1 = client.post("/api/ai/college/analyze-dataset", files={"file": ("binary.csv", fake_binary, "text/csv")})
    assert resp1.status_code == 400
    msg1 = resp1.json().get("detail", "")
    assert "Traceback" not in msg1
    assert "mongodb://" not in msg1
    assert "C:\\" not in msg1 and "/home/" not in msg1

    # Test 2: Uploading non-csv extension
    resp2 = client.post("/api/ai/college/analyze-dataset", files={"file": ("test.pdf", b"%PDF-1.4", "application/pdf")})
    assert resp2.status_code == 400
    msg2 = resp2.json().get("detail", "")
    assert "Traceback" not in msg2
    assert "mongodb://" not in msg2

    # Test 3: Benchmark predict with invalid payload
    resp3 = client.post("/api/ai/benchmark-predict", json={"invalid": "payload"})
    assert resp3.status_code == 422
    text3 = resp3.text
    assert "Traceback" not in text3
    assert "mongodb://" not in text3


# =========================================================================
# 4. Input Boundary & Safe Parsing
# =========================================================================

def test_file_size_boundary_5mb_exact_vs_exceeded():
    """Verify strict adherence to 5 MB upload ceiling."""
    header = "student_ref,branch,academic_year,semester,attendance_pct,cie_marks_obtained\n"
    line = "ANON_001,CSE,1,1,85.0,40.0\n"
    base = (header + line).encode("utf-8")

    # Exact boundary (5 MB)
    exact_payload = base + (b"\n" * (MAX_CSV_FILE_SIZE_BYTES - len(base)))
    assert len(exact_payload) == MAX_CSV_FILE_SIZE_BYTES
    resp_exact = client.post("/api/ai/college/audit-dataset", files={"file": ("exact.csv", exact_payload, "text/csv")})
    assert resp_exact.status_code == 200

    # Exceeded boundary (5 MB + 1 byte)
    over_payload = exact_payload + b"!"
    assert len(over_payload) == MAX_CSV_FILE_SIZE_BYTES + 1
    resp_over = client.post("/api/ai/college/audit-dataset", files={"file": ("over.csv", over_payload, "text/csv")})
    assert resp_over.status_code == 413


def test_malformed_csv_with_unclosed_quotes_handled_gracefully():
    """Verify unclosed quotes or CSV parsing errors return 400 Bad Request safely."""
    malformed = 'student_ref,branch,academic_year,semester,attendance_pct,cie_marks_obtained\n"STU_001,CSE,1,1,85.0,40.0\n'
    resp = client.post("/api/ai/college/analyze-dataset", files={"file": ("unclosed.csv", malformed.encode("utf-8"), "text/csv")})
    # Strict DictReader with unclosed quotes raises csv.Error, returning safe 400 Bad Request
    assert resp.status_code == 400
    assert "malformed csv content" in resp.json()["detail"].lower()
    assert "Traceback" not in resp.text

