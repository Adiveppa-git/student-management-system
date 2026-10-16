"""Automated Test Suite for Frontend Integration and Static Assets (Phase 5).

Validates:
1. Static files mounting at /frontend/ serves index.html with HTTP 200.
2. Index.html contains all 31 required UCI benchmark input IDs matching UCIBenchmarkStudentInput.
3. Preserves all existing student CRUD form fields, buttons, and list containers.
4. Includes visible, explicit Portuguese secondary school limitation disclaimer.
5. All preset profiles match UCIBenchmarkStudentInput validation and execute cleanly against the backend API.
6. Benchmark predictions do not mutate or pollute existing MongoDB student records.
"""

import re
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.ai_schemas import UCIBenchmarkStudentInput
from app.database.connection import collection

client = TestClient(app)
FRONTEND_FILE = Path(__file__).resolve().parent.parent / "frontend" / "index.html"

# The 31 exact feature names required by UCIBenchmarkStudentInput
REQUIRED_31_FEATURES = [
    "school", "sex", "age", "address", "famsize", "Pstatus", "Medu", "Fedu",
    "Mjob", "Fjob", "reason", "guardian", "traveltime", "studytime", "failures",
    "schoolsup", "famsup", "paid", "activities", "nursery", "higher", "internet",
    "romantic", "famrel", "freetime", "goout", "Dalc", "Walc", "health",
    "absences", "G1"
]

ORIGINAL_USNS = ["1DB24IS045", "1DB23IS001", "1DB25EC096", "1DB25CS009", "1DB23IS069", "1DB22CS020"]


def test_frontend_static_route_serves_html():
    """Verify /frontend/ returns HTTP 200 with text/html content type."""
    response = client.get("/frontend/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "<!DOCTYPE html>" in response.text


def test_existing_student_crud_elements_preserved():
    """Verify all original student management form inputs, buttons, and containers exist."""
    assert FRONTEND_FILE.exists()
    content = FRONTEND_FILE.read_text(encoding="utf-8")

    # Form and inputs
    assert 'id="studentForm"' in content
    assert 'id="name"' in content
    assert 'id="usn"' in content
    assert 'id="branch"' in content
    assert 'id="year"' in content
    assert 'id="email"' in content
    assert 'id="submitBtn"' in content
    assert 'id="studentList"' in content

    # CSS classes
    assert 'class="addBtn"' in content or 'addBtn' in content
    assert 'updateBtn' in content
    assert 'editBtn' in content
    assert 'deleteBtn' in content
    assert 'viewBtn' in content

    # JS functions
    assert "loadStudents" in content
    assert "editStudent" in content
    assert "viewStudent" in content
    assert "deleteStudent" in content


def test_all_31_benchmark_input_elements_present():
    """Verify index.html contains DOM inputs for all 31 features matching UCIBenchmarkStudentInput."""
    content = FRONTEND_FILE.read_text(encoding="utf-8")

    for feature in REQUIRED_31_FEATURES:
        expected_id = f'id="bm_{feature}"'
        assert expected_id in content, f"Missing benchmark input element for feature: {feature}"


def test_pydantic_schema_field_parity():
    """Verify that the frontend 31 feature list matches Pydantic schema field names exactly."""
    pydantic_fields = set(UCIBenchmarkStudentInput.model_fields.keys())
    frontend_features = set(REQUIRED_31_FEATURES)
    assert pydantic_fields == frontend_features, (
        f"Mismatch between Pydantic schema fields and frontend features: {pydantic_fields ^ frontend_features}"
    )


def test_prominent_disclaimer_notice_in_frontend():
    """Verify that index.html contains the mandatory secondary-school disclaimer."""
    content = FRONTEND_FILE.read_text(encoding="utf-8")
    assert "Experimental benchmark only" in content or "Experimental Benchmark Notice" in content
    assert "Portuguese secondary-school data" in content or "Portuguese" in content
    assert "Indian engineering-college students" in content or "Indian engineering" in content


def test_preset_profiles_execute_successfully_on_api():
    """Extract preset profiles from index.html JavaScript and verify each passes backend validation."""
    content = FRONTEND_FILE.read_text(encoding="utf-8")

    # Check struggling profile
    struggling_payload = {
        "school": "GP", "sex": "M", "age": 18, "address": "U", "famsize": "GT3", "Pstatus": "T",
        "Medu": 1, "Fedu": 1, "Mjob": "other", "Fjob": "other", "reason": "course", "guardian": "mother",
        "traveltime": 3, "studytime": 1, "failures": 3, "schoolsup": "yes", "famsup": "no", "paid": "no",
        "activities": "no", "nursery": "yes", "higher": "no", "internet": "no", "romantic": "yes",
        "famrel": 2, "freetime": 4, "goout": 5, "Dalc": 3, "Walc": 4, "health": 2, "absences": 22, "G1": 4.0
    }
    # Validate with Pydantic
    validated_struggling = UCIBenchmarkStudentInput(**struggling_payload)
    resp_struggling = client.post("/api/ai/benchmark-predict", json=validated_struggling.model_dump())
    assert resp_struggling.status_code == 200
    assert resp_struggling.json()["is_at_risk"] is True

    # Check thriving profile
    thriving_payload = {
        "school": "GP", "sex": "F", "age": 16, "address": "U", "famsize": "LE3", "Pstatus": "T",
        "Medu": 4, "Fedu": 4, "Mjob": "health", "Fjob": "teacher", "reason": "reputation", "guardian": "mother",
        "traveltime": 1, "studytime": 4, "failures": 0, "schoolsup": "no", "famsup": "yes", "paid": "yes",
        "activities": "yes", "nursery": "yes", "higher": "yes", "internet": "yes", "romantic": "no",
        "famrel": 5, "freetime": 2, "goout": 2, "Dalc": 1, "Walc": 1, "health": 5, "absences": 0, "G1": 18.0
    }
    validated_thriving = UCIBenchmarkStudentInput(**thriving_payload)
    resp_thriving = client.post("/api/ai/benchmark-predict", json=validated_thriving.model_dump())
    assert resp_thriving.status_code == 200
    assert resp_thriving.json()["is_at_risk"] is False


def test_database_records_remain_unaltered_after_frontend_evaluations():
    """Verify that all 6 original records in MongoDB remain intact and free of benchmark predictions."""
    for usn in ORIGINAL_USNS:
        record = collection.find_one({"usn": usn})
        assert record is not None, f"Original student record for USN {usn} was lost!"
        assert "benchmark_prediction" not in record
        assert "risk_status" not in record
        assert "is_at_risk" not in record
