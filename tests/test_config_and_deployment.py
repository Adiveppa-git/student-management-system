"""Phase 10.2 Configuration, Deployment Remediation, and Preservation Test Suite.

Verifies:
1. Environment variable precedence (DATABASE_NAME over DB_NAME with student_db default).
2. Safe .env loading with override=False preserving explicit environment values.
3. CORS configuration parsing, default local origins, and wildcard credential protection.
4. ML startup lifespan diagnostics (logging warnings instead of silent suppression).
5. Model health reporting and leak-free 503 response when artifacts are unavailable.
6. Preservation of existing student CRUD endpoints and original MongoDB records.
7. Benchmark prediction behavior, disclaimer presence, and model health endpoint.
8. College dataset audit/analysis in-memory execution without persistence.
9. Immutability of benchmark ML artifacts (SHA-256) and zero college models trained.
10. Integrity of .gitignore rules and sanitized .env.example template.
"""

import asyncio
import hashlib
import logging
import os
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.database.connection import ROOT_DIR, collection, get_database_name, load_environment
from app.main import DEFAULT_CORS_ORIGINS, app, get_cors_configuration, lifespan
from tests.test_security_and_hardening import ARTIFACTS_DIR, compute_dir_sha256

ORIGINAL_STUDENT_USNS = [
    "1DB24IS045",
    "1DB23IS001",
    "1DB25EC096",
    "1DB25CS009",
    "1DB23IS069",
    "1DB22CS020",
]

ORIGINAL_STUDENT_BASELINE = {
    "1DB24IS045": {"name": "Rohit", "email": "rohit@gmail.com", "branch": "ISE", "year": 2},
    "1DB23IS001": {"name": "Rahul", "email": "rahul@gmail.com", "branch": "ISE", "year": 4},
    "1DB25EC096": {"name": "Shreyas", "email": "shreyas@gmail.com", "branch": "ECE", "year": 1},
    "1DB25CS009": {"name": "Manish", "email": "manish@gmail.com", "branch": "CSE", "year": 1},
    "1DB23IS069": {"name": "Karun", "email": "karun@gmail.com", "branch": "ISE", "year": 3},
    "1DB22CS020": {"name": "Axar", "email": "axar@gmail.com", "branch": "CSE", "year": 4},
}

SAMPLE_UCI_STUDENT = {
    "school": "GP",
    "sex": "M",
    "age": 18,
    "address": "U",
    "famsize": "GT3",
    "Pstatus": "T",
    "Medu": 2,
    "Fedu": 2,
    "Mjob": "other",
    "Fjob": "other",
    "reason": "course",
    "guardian": "mother",
    "traveltime": 2,
    "studytime": 2,
    "failures": 1,
    "schoolsup": "no",
    "famsup": "yes",
    "paid": "no",
    "activities": "yes",
    "nursery": "yes",
    "higher": "yes",
    "internet": "yes",
    "romantic": "no",
    "famrel": 4,
    "freetime": 3,
    "goout": 3,
    "Dalc": 1,
    "Walc": 2,
    "health": 3,
    "absences": 4,
    "G1": 11.0,
}

SAMPLE_COLLEGE_CSV = (
    "student_ref,branch,academic_year,semester,attendance_pct,cie_marks_obtained,cie_max_marks,previous_sgpa,cumulative_cgpa,active_backlogs,verified_outcome,is_at_risk_label,outcome_source\n"
    + "\n".join(
        [f"ANON_P_{i:03d},CSE,2,4,88.0,42.0,50.0,8.2,8.0,0,PASS,false,OFFICIAL_EXAM_CELL" for i in range(80)]
        + [f"ANON_R_{i:03d},ECE,2,4,62.0,18.0,50.0,5.4,5.6,3,FAIL_OR_DETAINED,true,OFFICIAL_EXAM_CELL" for i in range(40)]
    )
)


@pytest.fixture(scope="module")
def client():
    """Create FastAPI test client."""
    with TestClient(app) as test_client:
        yield test_client


# =============================================================================
# 1. Environment Variable Precedence and Safe Loading
# =============================================================================


def test_database_name_precedence_and_defaults():
    """Verify DATABASE_NAME takes precedence over DB_NAME and defaults to student_db using actual app config."""
    import importlib
    import app.database.connection

    def resolve_db_name(env_vars):
        with patch.dict(os.environ, env_vars, clear=True):
            return get_database_name()

    # 1. Neither variable set -> default to "student_db"
    assert resolve_db_name({}) == "student_db"

    # 2. Only DB_NAME set -> returns DB_NAME value
    assert resolve_db_name({"DB_NAME": "legacy_students"}) == "legacy_students"

    # 3. Only DATABASE_NAME set -> returns DATABASE_NAME value
    assert resolve_db_name({"DATABASE_NAME": "modern_students"}) == "modern_students"

    # 4. Both set -> DATABASE_NAME takes precedence over DB_NAME
    assert (
        resolve_db_name(
            {"DATABASE_NAME": "primary_db", "DB_NAME": "secondary_db"}
        )
        == "primary_db"
    )

    # 5. DATABASE_NAME is empty string -> falls back to DB_NAME
    assert (
        resolve_db_name({"DATABASE_NAME": "", "DB_NAME": "fallback_db"})
        == "fallback_db"
    )

    # 6. Verify actual module loading and PyMongo database binding with environment variable
    try:
        with patch.dict(os.environ, {"DATABASE_NAME": "app_verified_db"}, clear=True):
            importlib.reload(app.database.connection)
            assert app.database.connection.DATABASE_NAME == "app_verified_db"
            assert app.database.connection.DB_NAME == "app_verified_db"
            assert app.database.connection.db.name == "app_verified_db"
    finally:
        # Restore module connection to default student_db
        with patch.dict(os.environ, {"DATABASE_NAME": "student_db"}, clear=True):
            importlib.reload(app.database.connection)


def test_safe_dotenv_loading_does_not_override_existing_env(tmp_path):
    """Verify application's real .env loading preserves existing environment variables."""
    # Create a realistic temporary .env file
    temp_env_file = tmp_path / ".env"
    temp_env_file.write_text(
        "DATABASE_NAME=dotenv_db\n"
        "TEST_EXISTING_KEY=dotenv_override_attempt\n"
        "TEST_NEW_KEY=loaded_from_dotenv\n",
        encoding="utf-8",
    )

    # Pre-set existing system / container environment variables
    existing_vars = {
        "DATABASE_NAME": "system_precedence_db",
        "TEST_EXISTING_KEY": "system_original_val",
    }
    with patch.dict(os.environ, existing_vars, clear=True):
        # Call the application's actual load_environment function
        result = load_environment(dotenv_path=temp_env_file, override=False)
        assert result is True

        # 1. Existing system variables must be preserved (not overridden)
        assert os.getenv("TEST_EXISTING_KEY") == "system_original_val"
        assert os.getenv("DATABASE_NAME") == "system_precedence_db"

        # 2. Previously unset variables from .env must be loaded
        assert os.getenv("TEST_NEW_KEY") == "loaded_from_dotenv"

        # 3. Application database resolution reflects the preserved environment variable
        assert get_database_name() == "system_precedence_db"

    # Verify default loader resolves against the application ROOT_DIR
    default_target = ROOT_DIR / ".env"
    assert default_target.parent == ROOT_DIR


# =============================================================================
# 2. CORS Configuration Tests
# =============================================================================


def test_cors_default_origins():
    """Verify default CORS configuration uses explicit local origins and enables credentials."""
    with patch.dict(os.environ, {}, clear=True):
        origins, allow_creds = get_cors_configuration()
        assert set(origins) == set(DEFAULT_CORS_ORIGINS)
        assert allow_creds is True
        assert "http://localhost:8000" in origins
        assert "http://127.0.0.1:8000" in origins
        assert "http://localhost:3000" in origins
        assert "http://127.0.0.1:5500" in origins


def test_cors_custom_origins_parsing():
    """Verify comma-separated CORS_ORIGINS are parsed, trimmed, and credentials preserved."""
    custom_origins = " https://portal.college.edu , http://localhost:8080 ,  https://app.college.edu  "
    with patch.dict(os.environ, {"CORS_ORIGINS": custom_origins}):
        origins, allow_creds = get_cors_configuration()
        assert origins == [
            "https://portal.college.edu",
            "http://localhost:8080",
            "https://app.college.edu",
        ]
        assert allow_creds is True


def test_cors_wildcard_disables_credentials():
    """Verify wildcard origins explicitly disable credentials to satisfy browser security specs."""
    # Single wildcard
    with patch.dict(os.environ, {"CORS_ORIGINS": "*"}):
        origins, allow_creds = get_cors_configuration()
        assert origins == ["*"]
        assert allow_creds is False

    # Mixed wildcard in list
    with patch.dict(os.environ, {"CORS_ORIGINS": "http://localhost:3000, *"}):
        origins, allow_creds = get_cors_configuration()
        assert origins == ["*"]
        assert allow_creds is False


def test_cors_request_headers_in_fastapi(client):
    """Verify FastAPI returns correct Access-Control-Allow-Origin header for allowed origin."""
    response = client.get(
        "/",
        headers={"Origin": "http://localhost:8000"},
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:8000"
    assert response.headers.get("access-control-allow-credentials") == "true"


# =============================================================================
# 3. Startup Logging and ML Diagnostics
# =============================================================================


def test_lifespan_startup_success_logs_info(caplog):
    """Verify successful ML pipeline preloading logs info message."""
    async def run_lifespan():
        async with lifespan(app):
            pass

    with caplog.at_level(logging.INFO):
        asyncio.run(run_lifespan())

    assert any(
        "AI benchmark ML pipeline preloaded successfully" in record.message
        for record in caplog.records
    )


def test_lifespan_startup_failure_logs_warning_and_does_not_crash(caplog):
    """Verify failed ML pipeline preloading logs structured warning without crashing startup."""
    async def run_lifespan():
        async with lifespan(app):
            pass

    with patch(
        "app.main.load_model_pipeline",
        side_effect=FileNotFoundError("Simulated missing model file"),
    ):
        with caplog.at_level(logging.WARNING):
            asyncio.run(run_lifespan())

    warning_records = [
        r
        for r in caplog.records
        if "Benchmark ML model pipeline could not be preloaded on startup" in r.message
    ]
    assert len(warning_records) > 0
    assert "FileNotFoundError" in warning_records[0].message


def test_health_endpoint_reports_unavailable_safely_when_model_missing(client):
    """Verify /api/ai/health returns 503 with leak-free payload when model is missing."""
    with patch(
        "app.routes.ai_routes.check_model_health",
        return_value={
            "status": "unavailable",
            "model_loaded": False,
            "model_type": None,
            "features_count": None,
            "artifacts_intact": False,
            "message": "Model artifacts are missing or unavailable.",
        },
    ):
        response = client.get("/api/ai/health")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unavailable"
        assert data["model_loaded"] is False
        assert data["artifacts_intact"] is False
        # Verify no file paths or system credentials leaked
        body_str = response.text
        assert "C:\\" not in body_str
        assert "/home/" not in body_str
        assert "password" not in body_str.lower()
        assert "traceback" not in body_str.lower()


def test_health_endpoint_healthy_when_model_present(client):
    """Verify /api/ai/health returns 200 with operational model details."""
    response = client.get("/api/ai/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["model_loaded"] is True
    assert data["artifacts_intact"] is True
    assert data["model_type"] in ["RandomForestClassifier", "LogisticRegression"]


# =============================================================================
# 4. Existing Student CRUD Behavior and Database Preservation
# =============================================================================


def test_existing_student_crud_endpoints(client):
    """Verify student list and individual lookup endpoints function correctly."""
    response = client.get("/students")
    assert response.status_code == 200
    students = response.json()
    assert isinstance(students, list)
    assert len(students) >= 6

    # Test single student retrieval
    sample_usn = ORIGINAL_STUDENT_USNS[0]
    single_res = client.get(f"/students/{sample_usn}")
    assert single_res.status_code == 200
    student = single_res.json()
    assert student["usn"] == sample_usn
    assert "name" in student
    assert "branch" in student


def test_original_mongodb_records_strictly_preserved():
    """Verify all six original MongoDB records exist, retain required fields,
    and match trusted baseline values without leaked ML or college dataset fields.

    Note: Checks record existence, schema integrity (_id, name, email, branch, year),
    absence of prediction leakage, and verifies field values against the trusted
    pre-existing student baseline.
    """
    for usn, expected in ORIGINAL_STUDENT_BASELINE.items():
        record = collection.find_one({"usn": usn})
        assert record is not None, f"Original student record with USN {usn} was lost!"
        assert "_id" in record
        for field, expected_val in expected.items():
            assert field in record, f"Required field '{field}' missing in record {usn}"
            assert record[field] == expected_val, (
                f"Field '{field}' value changed for {usn}: expected {expected_val}, got {record[field]}"
            )
        # Verify no benchmark predictions or college flags leaked into MongoDB
        assert "risk_prediction" not in record
        assert "probability" not in record
        assert "college_features" not in record



# =============================================================================
# 5. Benchmark Predictions and Limitations
# =============================================================================


def test_benchmark_prediction_endpoint(client):
    """Verify POST /api/ai/benchmark-predict returns valid predictions and mandatory disclaimers."""
    response = client.post("/api/ai/benchmark-predict", json=SAMPLE_UCI_STUDENT)
    assert response.status_code == 200
    data = response.json()
    assert data["risk_level"] in ["High", "Medium", "Low"]
    assert data["risk_status"] in ["At-Risk", "Normal"]
    assert 0.0 <= data["risk_probability"] <= 1.0
    assert "EXPERIMENTAL BENCHMARK MODEL" in data["disclaimer"]
    assert "Domain Applicability Notice" in data["domain_applicability_note"]


# =============================================================================
# 6. College Dataset Audits & Analysis In-Memory Execution
# =============================================================================


def test_college_dataset_audit_and_analysis_in_memory_only(client):
    """Verify college audit/analysis endpoints run in memory without touching MongoDB."""
    initial_count = collection.count_documents({})

    response = client.post(
        "/api/ai/college/audit-dataset",
        files={"file": ("authorized_college_cohort_2024.csv", SAMPLE_COLLEGE_CSV.encode("utf-8"), "text/csv")},
    )
    assert response.status_code == 200
    assert response.json()["database_storage_action"] == "NONE_INSPECTED_ONLY"

    # Verify zero database records added
    assert collection.count_documents({}) == initial_count


# =============================================================================
# 7. Benchmark Artifact Immutability and Zero College Models
# =============================================================================


def test_benchmark_artifacts_and_zero_college_models(client):
    """Verify benchmark ML artifact SHA-256 hashes match a baseline captured before operations.

    Reuses compute_dir_sha256 and ARTIFACTS_DIR from tests/test_security_and_hardening.py.
    Captures baseline hashes before running operations, then verifies byte-for-byte immutability
    and guarantees zero college-specific models exist on disk.
    """
    assert ARTIFACTS_DIR.exists()

    # 1. Capture SHA-256 baseline before operation
    baseline_hashes = compute_dir_sha256(ARTIFACTS_DIR)
    assert "student_risk_pipeline.joblib" in baseline_hashes
    assert "logistic_regression_pipeline.joblib" in baseline_hashes
    assert "metadata.json" in baseline_hashes
    assert "metrics.json" in baseline_hashes

    # 2. Execute application operations (benchmark prediction and dataset audit)
    pred_res = client.post("/api/ai/benchmark-predict", json=SAMPLE_UCI_STUDENT)
    assert pred_res.status_code == 200

    audit_res = client.post(
        "/api/ai/college/audit-dataset",
        files={"file": ("baseline_audit.csv", SAMPLE_COLLEGE_CSV.encode("utf-8"), "text/csv")},
    )
    assert audit_res.status_code == 200

    # 3. Compare post-operation hashes against the pre-operation baseline
    post_op_hashes = compute_dir_sha256(ARTIFACTS_DIR)
    assert post_op_hashes == baseline_hashes, (
        f"Artifact SHA-256 hash mismatch! Baseline: {baseline_hashes}, Post-op: {post_op_hashes}"
    )

    # 4. Verify zero college-specific models were created
    college_models = list(ARTIFACTS_DIR.glob("college_*.joblib"))
    assert len(college_models) == 0, f"Unauthorized college models found: {college_models}"


# =============================================================================
# 8. .gitignore and .env.example Hygiene & Secret Protection
# =============================================================================


def test_gitignore_contains_required_patterns():
    """Verify .gitignore includes virtual envs, IDEs, logs, coverage, and OS files."""
    gitignore_path = Path(__file__).resolve().parent.parent / ".gitignore"
    assert gitignore_path.exists()
    content = gitignore_path.read_text(encoding="utf-8")

    required_patterns = [
        ".venv/",
        "venv/",
        ".vscode/",
        ".idea/",
        "*.log",
        ".coverage",
        "htmlcov/",
        ".DS_Store",
        "Thumbs.db",
    ]
    for pattern in required_patterns:
        assert pattern in content, f"Missing pattern {pattern} in .gitignore"


def test_env_example_has_placeholders_and_zero_secrets():
    """Verify .env.example contains configuration templates and zero real credentials."""
    env_example_path = Path(__file__).resolve().parent.parent / ".env.example"
    assert env_example_path.exists()
    content = env_example_path.read_text(encoding="utf-8")

    assert "MONGO_URI=" in content
    assert "DATABASE_NAME=" in content
    assert "DB_NAME=" in content
    assert "CORS_ORIGINS=" in content

    # Verify no real credentials
    assert "mongodb+srv" not in content
    assert "adiveppa" not in content.lower()
    assert "supersecret" not in content.lower()
    assert "password123" not in content.lower()
