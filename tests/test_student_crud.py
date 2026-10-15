import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database.connection import collection

client = TestClient(app)

ORIGINAL_USNS = ["1DB24IS045", "1DB23IS001", "1DB25EC096", "1DB25CS009", "1DB23IS069", "1DB22CS020"]


def test_existing_records_preserved():
    """Verify all 6 pre-existing student records exist and remain intact."""
    for usn in ORIGINAL_USNS:
        record = collection.find_one({"usn": usn})
        assert record is not None, f"Original student record with USN {usn} was lost!"
        assert "name" in record
        assert "email" in record
        assert "branch" in record
        assert "year" in record


def test_get_students_list():
    """Verify GET /students returns all students formatted with backward-compatible fields."""
    response = client.get("/students")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= len(ORIGINAL_USNS)

    # Verify student shape expected by frontend
    first = data[0]
    for key in ["id", "name", "usn", "branch", "year", "email"]:
        assert key in first, f"Missing key '{key}' in student response"


def test_get_single_student_found_and_not_found():
    """Verify GET /students/{usn} retrieves record or returns 404."""
    # Existing student
    response = client.get("/students/1DB24IS045")
    assert response.status_code == 200
    data = response.json()
    assert data["usn"] == "1DB24IS045"
    assert data["name"] == "Rohit"

    # Non-existent student
    response_missing = client.get("/students/NON_EXISTENT_USN_XYZ")
    assert response_missing.status_code == 404
    assert "not found" in response_missing.json()["detail"].lower()


def test_add_student_validation_and_duplicate_check():
    """Verify POST /students validates input with Pydantic and prevents duplicate USN."""
    test_usn = "TEST_PHASE2_001"

    # Ensure cleanup before test in case of prior partial runs
    collection.delete_one({"usn": test_usn})

    # 1. Invalid input (bad email, invalid year)
    bad_payload = {
        "name": "Invalid Student",
        "usn": test_usn,
        "branch": "CSE",
        "year": 15,  # Invalid: year must be 1-8
        "email": "not-an-email"
    }
    bad_resp = client.post("/students", json=bad_payload)
    assert bad_resp.status_code == 422, "Expected 422 Unprocessable Entity for invalid data"

    # 2. Valid input
    valid_payload = {
        "name": "Phase2 Test Student",
        "usn": test_usn,
        "branch": "ISE",
        "year": 3,
        "email": "phase2test@example.com",
        "attendance_pct": 82.5,
        "internal_marks_avg": 78.0,
        "assignment_score_avg": 85.0,
        "study_hours_per_week": 14.0,
        "previous_gpa": 8.1,
        "backlog_count": 0
    }
    create_resp = client.post("/students", json=valid_payload)
    assert create_resp.status_code == 201
    res_data = create_resp.json()
    assert res_data["message"] == "Student added"
    assert res_data["usn"] == test_usn

    # 3. Duplicate USN check
    dup_resp = client.post("/students", json=valid_payload)
    assert dup_resp.status_code == 400
    assert "already exists" in dup_resp.json()["detail"].lower()


def test_edit_student():
    """Verify PUT /students/{usn} updates student details."""
    test_usn = "TEST_PHASE2_001"

    update_payload = {
        "name": "Phase2 Test Student Updated",
        "attendance_pct": 89.0,
        "branch": "AI & DS"
    }
    put_resp = client.put(f"/students/{test_usn}", json=update_payload)
    assert put_resp.status_code == 200
    data = put_resp.json()
    assert data["message"] == "Updated"
    assert data["student"]["name"] == "Phase2 Test Student Updated"
    assert data["student"]["branch"] == "AI & DS"
    assert data["student"]["attendance_pct"] == 89.0

    # Non-existent student update
    missing_resp = client.put("/students/NON_EXISTENT_USN_XYZ", json={"name": "Ghost"})
    assert missing_resp.status_code == 404


def test_delete_student_by_usn():
    """Verify DELETE /students/{usn} deletes the student (fixing the frontend delete issue)."""
    test_usn = "TEST_PHASE2_001"

    # Delete existing test student
    del_resp = client.delete(f"/students/{test_usn}")
    assert del_resp.status_code == 200
    assert del_resp.json()["message"] == "Student deleted"

    # Verify removed from database
    check = collection.find_one({"usn": test_usn})
    assert check is None

    # Deleting again returns 404
    del_again_resp = client.delete(f"/students/{test_usn}")
    assert del_again_resp.status_code == 404


def test_legacy_delete_student_by_id():
    """Verify legacy DELETE /delete-student/{id} remains functional."""
    # Insert a temporary student
    temp_result = collection.insert_one({
        "name": "Temp Legacy Delete Student",
        "usn": "TEMP_LEGACY_001",
        "branch": "MECH",
        "year": 2,
        "email": "temp@example.com"
    })
    temp_id = str(temp_result.inserted_id)

    # Delete by legacy route
    del_resp = client.delete(f"/delete-student/{temp_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["message"] == "Student deleted"

    # Verify invalid ID returns 400
    bad_id_resp = client.delete("/delete-student/invalid-mongo-id")
    assert bad_id_resp.status_code == 400


def test_final_verification_original_records_unaltered():
    """Ensure once again that all 6 original records remain exactly intact."""
    records = list(collection.find())
    found_usns = {r["usn"] for r in records}
    for original in ORIGINAL_USNS:
        assert original in found_usns, f"CRITICAL: Original USN {original} is missing!"
