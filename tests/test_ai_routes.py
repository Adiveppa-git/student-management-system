"""Automated Test Suite for AI API Endpoints (Phase 4).

Validates:
1. GET /api/ai/health - Health check and model readiness.
2. GET /api/ai/model-metrics - Inspection of actual saved metrics and limitations.
3. POST /api/ai/benchmark-predict - Valid high-risk and low-risk student predictions.
4. Input validation (422 Unprocessable Entity) for malformed, out-of-range, and invalid categories.
5. Missing artifact error handling (503 Service Unavailable) without internal path leakage.
6. Preservation of existing CRUD routes and MongoDB records.
"""

from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database.connection import collection

client = TestClient(app)

ORIGINAL_USNS = ["1DB24IS045", "1DB23IS001", "1DB25EC096", "1DB25CS009", "1DB23IS069", "1DB22CS020"]


@pytest.fixture
def valid_struggling_payload() -> dict:
    """Valid UCI benchmark input representing an academically struggling student."""
    return {
        "school": "GP",
        "sex": "M",
        "age": 18,
        "address": "U",
        "famsize": "GT3",
        "Pstatus": "T",
        "Medu": 1,
        "Fedu": 1,
        "Mjob": "other",
        "Fjob": "other",
        "reason": "course",
        "guardian": "mother",
        "traveltime": 3,
        "studytime": 1,
        "failures": 3,
        "schoolsup": "yes",
        "famsup": "no",
        "paid": "no",
        "activities": "no",
        "nursery": "yes",
        "higher": "no",
        "internet": "no",
        "romantic": "yes",
        "famrel": 2,
        "freetime": 4,
        "goout": 5,
        "Dalc": 3,
        "Walc": 4,
        "health": 2,
        "absences": 22,
        "G1": 4.0,
    }


@pytest.fixture
def valid_thriving_payload() -> dict:
    """Valid UCI benchmark input representing a high-performing student."""
    return {
        "school": "GP",
        "sex": "F",
        "age": 16,
        "address": "U",
        "famsize": "LE3",
        "Pstatus": "T",
        "Medu": 4,
        "Fedu": 4,
        "Mjob": "health",
        "Fjob": "teacher",
        "reason": "reputation",
        "guardian": "mother",
        "traveltime": 1,
        "studytime": 4,
        "failures": 0,
        "schoolsup": "no",
        "famsup": "yes",
        "paid": "yes",
        "activities": "yes",
        "nursery": "yes",
        "higher": "yes",
        "internet": "yes",
        "romantic": "no",
        "famrel": 5,
        "freetime": 2,
        "goout": 2,
        "Dalc": 1,
        "Walc": 1,
        "health": 5,
        "absences": 0,
        "G1": 18.0,
    }


# =========================================================================
# 1. Health and Operational Status Tests
# =========================================================================

def test_ai_health_endpoint():
    """Verify GET /api/ai/health returns 200 with operational model status."""
    response = client.get("/api/ai/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["model_loaded"] is True
    assert data["artifacts_intact"] is True
    assert data["features_count"] == 31
    assert "RandomForest" in data["model_type"]


def test_ai_model_metrics_endpoint():
    """Verify GET /api/ai/model-metrics returns authentic evaluation metrics and limitations."""
    response = client.get("/api/ai/model-metrics")
    assert response.status_code == 200
    data = response.json()

    assert data["model_name"] == "Random Forest"
    assert "https://archive.ics.uci.edu" in data["dataset_source"]
    assert "Cortez" in data["citation"]
    assert data["license"] == "Creative Commons Attribution 4.0 International (CC BY 4.0)"
    assert data["passing_threshold"] == 10
    assert data["grade_scale"] == "0 to 20"

    # Verify actual test metrics
    test_metrics = data["test_metrics"]
    assert test_metrics["accuracy"] >= 0.85
    assert test_metrics["recall"] >= 0.80
    assert test_metrics["precision"] >= 0.75
    assert test_metrics["f1_score"] >= 0.80
    assert "confusion_matrix" in test_metrics

    # Verify explicit domain limitations
    limitations = data["evaluation_limitations"]
    assert isinstance(limitations, list)
    assert len(limitations) >= 3
    combined_limitations = " ".join(limitations).lower()
    assert "portuguese" in combined_limitations
    assert "indian engineering" in combined_limitations


# =========================================================================
# 2. Prediction Endpoints - Valid Requests
# =========================================================================

def test_benchmark_predict_struggling_student(valid_struggling_payload):
    """Verify POST /api/ai/benchmark-predict flags struggling student as At-Risk."""
    response = client.post("/api/ai/benchmark-predict", json=valid_struggling_payload)
    assert response.status_code == 200
    data = response.json()

    assert data["is_at_risk"] is True
    assert data["risk_status"] == "At-Risk"
    assert 0.50 <= data["risk_probability"] <= 1.0
    assert data["risk_level"] in ["High", "Medium"]
    assert data["evaluated_features_count"] == 31

    # Verify required disclaimers
    assert "EXPERIMENTAL BENCHMARK MODEL" in data["disclaimer"]
    assert "Cortez & Silva" in data["disclaimer"]
    assert "Domain Applicability Notice" in data["domain_applicability_note"]
    assert "Indian engineering" in data["domain_applicability_note"]


def test_benchmark_predict_thriving_student(valid_thriving_payload):
    """Verify POST /api/ai/benchmark-predict classifies strong student as Normal / Low-Risk."""
    response = client.post("/api/ai/benchmark-predict", json=valid_thriving_payload)
    assert response.status_code == 200
    data = response.json()

    assert data["is_at_risk"] is False
    assert data["risk_status"] == "Normal"
    assert data["risk_probability"] < 0.50
    assert data["risk_level"] == "Low"


# =========================================================================
# 3. Input Validation and Malformed Payloads (422 Unprocessable Entity)
# =========================================================================

def test_benchmark_predict_empty_payload():
    """Verify empty JSON returns 422 Unprocessable Entity."""
    response = client.post("/api/ai/benchmark-predict", json={})
    assert response.status_code == 422


def test_benchmark_predict_invalid_category(valid_struggling_payload):
    """Verify invalid category option returns 422."""
    bad_payload = valid_struggling_payload.copy()
    bad_payload["school"] = "INVALID_HIGH_SCHOOL"
    response = client.post("/api/ai/benchmark-predict", json=bad_payload)
    assert response.status_code == 422


def test_benchmark_predict_out_of_range_grade(valid_struggling_payload):
    """Verify grade G1 outside [0.0, 20.0] returns 422."""
    # Exceeds max 20
    bad_high = valid_struggling_payload.copy()
    bad_high["G1"] = 25.0
    res_high = client.post("/api/ai/benchmark-predict", json=bad_high)
    assert res_high.status_code == 422

    # Negative grade
    bad_neg = valid_struggling_payload.copy()
    bad_neg["G1"] = -1.0
    res_neg = client.post("/api/ai/benchmark-predict", json=bad_neg)
    assert res_neg.status_code == 422


def test_benchmark_predict_out_of_range_studytime(valid_struggling_payload):
    """Verify studytime outside [1, 4] returns 422."""
    bad_study = valid_struggling_payload.copy()
    bad_study["studytime"] = 0
    res = client.post("/api/ai/benchmark-predict", json=bad_study)
    assert res.status_code == 422


def test_benchmark_predict_negative_absences(valid_struggling_payload):
    """Verify negative absences returns 422."""
    bad_absences = valid_struggling_payload.copy()
    bad_absences["absences"] = -5
    res = client.post("/api/ai/benchmark-predict", json=bad_absences)
    assert res.status_code == 422


def test_benchmark_predict_wrong_data_types(valid_struggling_payload):
    """Verify string passed to numeric field returns 422."""
    bad_types = valid_struggling_payload.copy()
    bad_types["age"] = "not_an_integer"
    res = client.post("/api/ai/benchmark-predict", json=bad_types)
    assert res.status_code == 422


# =========================================================================
# 4. Error Handling: Missing Artifacts (503 Service Unavailable)
# =========================================================================

def test_missing_model_artifact_returns_503(valid_struggling_payload):
    """Verify 503 is returned without path leakage when model artifact is missing."""
    with patch("app.routes.ai_routes.predict_student_risk", side_effect=FileNotFoundError("Missing")):
        response = client.post("/api/ai/benchmark-predict", json=valid_struggling_payload)
        assert response.status_code == 503
        data = response.json()
        assert "unavailable" in data["detail"].lower()
        # Ensure no internal filesystem paths are exposed
        assert "users" not in data["detail"].lower()
        assert "c:" not in data["detail"].lower()
        assert "\\" not in data["detail"]


def test_metrics_missing_artifact_returns_503():
    """Verify GET /api/ai/model-metrics returns 503 when metrics are missing."""
    with patch("app.routes.ai_routes.get_metrics", side_effect=FileNotFoundError("Missing")):
        response = client.get("/api/ai/model-metrics")
        assert response.status_code == 503
        data = response.json()
        assert "unavailable" in data["detail"].lower()
        assert "c:" not in data["detail"].lower()


def test_health_check_returns_503_when_unhealthy():
    """Verify GET /api/ai/health returns 503 when model is unavailable."""
    with patch("app.routes.ai_routes.check_model_health", return_value={
        "status": "unavailable",
        "model_loaded": False,
        "model_type": None,
        "features_count": None,
        "artifacts_intact": False,
        "message": "Model artifacts are missing."
    }):
        response = client.get("/api/ai/health")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unavailable"
        assert data["model_loaded"] is False


# =========================================================================
# 5. Database and Existing Feature Preservation Verification
# =========================================================================

def test_existing_records_and_crud_unaffected():
    """Verify that original MongoDB records remain intact and untouched after AI operations."""
    for usn in ORIGINAL_USNS:
        record = collection.find_one({"usn": usn})
        assert record is not None, f"Original USN {usn} was modified or deleted!"
        # Verify no benchmark prediction was automatically injected into student records
        assert "benchmark_prediction" not in record
        assert "risk_status" not in record
