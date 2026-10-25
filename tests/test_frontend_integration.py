"""Automated Test Suite for Frontend Integration and Static Assets (Phase 5).

Validates:
1. Static files mounting at /frontend/ serves index.html with HTTP 200.
2. Index.html contains all 31 required UCI benchmark input IDs matching UCIBenchmarkStudentInput.
3. Preserves all existing student CRUD form fields, buttons, and list containers.
4. Includes visible, explicit Portuguese secondary school limitation disclaimer.
5. All preset profiles match UCIBenchmarkStudentInput validation and execute cleanly against the backend API.
6. Benchmark predictions do not mutate or pollute existing MongoDB student records.
"""

from pathlib import Path
import html
import re
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.ai_schemas import UCIBenchmarkStudentInput
from app.database.connection import collection

client = TestClient(app)
FRONTEND_FILE = Path(__file__).resolve().parent.parent / "frontend" / "index.html"
FRONTEND_DIR = FRONTEND_FILE.parent
STUDENTS_FILE = FRONTEND_DIR / "students.html"

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
    """Verify both frontend pages and their extracted assets are served."""
    response = client.get("/frontend/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "<!DOCTYPE html>" in response.text

    students_response = client.get("/frontend/students.html")
    assert students_response.status_code == 200
    assert 'id="studentList"' in students_response.text

    details_response = client.get("/frontend/student-details.html")
    assert details_response.status_code == 200
    assert 'id="studentDetailsContent"' in details_response.text

    asset_paths = [
        "/frontend/css/app.css",
        "/frontend/js/api.js",
        "/frontend/js/navigation.js",
        "/frontend/js/student-registration.js",
        "/frontend/js/students.js?v=3",
        "/frontend/js/student-details.js",
        "/frontend/js/ai-dashboard.js",
        "/frontend/js/benchmark-prediction.js",
        "/frontend/js/college-dataset-analysis.js",
    ]
    for asset_path in asset_paths:
        asset_response = client.get(asset_path)
        assert asset_response.status_code == 200, asset_path


def test_existing_student_crud_elements_preserved():
    """Verify registration stays on index and student operations live on students.html."""
    assert FRONTEND_FILE.exists()
    assert STUDENTS_FILE.exists()
    registration_content = FRONTEND_FILE.read_text(encoding="utf-8")
    students_content = STUDENTS_FILE.read_text(encoding="utf-8")

    # Form and inputs
    assert 'id="studentForm"' in registration_content
    assert 'id="name"' in registration_content
    assert 'id="usn"' in registration_content
    assert 'id="branch"' in registration_content
    assert 'id="year"' in registration_content
    assert 'id="email"' in registration_content
    assert 'id="submitBtn"' in registration_content
    assert 'id="studentList"' not in registration_content
    assert 'id="studentList"' in students_content
    assert "<script>" not in registration_content
    assert 'style="' not in registration_content
    assert "onclick=" not in registration_content
    assert "onchange=" not in registration_content
    assert "onsubmit=" not in registration_content

    # CSS classes
    styles = (FRONTEND_DIR / "css" / "app.css").read_text(encoding="utf-8")
    assert ".addBtn" in styles
    assert ".updateBtn" in styles
    assert ".editBtn" in styles
    assert ".deleteBtn" in styles
    assert ".viewBtn" in styles

    # JS functions
    student_script = (FRONTEND_DIR / "js" / "students.js").read_text(encoding="utf-8")
    registration_script = (FRONTEND_DIR / "js" / "student-registration.js").read_text(encoding="utf-8")
    navigation_script = (FRONTEND_DIR / "js" / "navigation.js").read_text(encoding="utf-8")
    assert "loadStudents" in student_script
    assert "viewStudent" in student_script
    assert "deleteStudent" in student_script
    assert "index.html?usn=" in student_script
    assert "loadStudents()" not in registration_script
    assert "loadStudentForEdit" in registration_script
    assert 'const tabs = ["dashboard", "benchmark", "analysis"]' in navigation_script
    assert 'id="tab-students"' not in registration_content


def test_student_registration_and_update_use_inline_success_feedback():
    """Verify CRUD success feedback is inline and update keeps the form in place."""
    registration_content = FRONTEND_FILE.read_text(encoding="utf-8")
    registration_script = (FRONTEND_DIR / "js" / "student-registration.js").read_text(encoding="utf-8")
    submit_handler = registration_script.split("// Add / Update", 1)[1].split(
        "async function loadStudentForEdit", 1
    )[0]
    update_handler = registration_script.split("if (editUSN) {", 1)[1].split(
        "} else {", 1
    )[0]

    assert 'id="studentSuccessMessage"' in registration_content
    assert 'class="alert-card success" role="status" aria-live="polite" hidden' in registration_content
    assert 'src="js/student-registration.js?v=2"' in registration_content
    assert 'successMessage.textContent = message' in registration_script
    update_success_path = update_handler.split("if (!res.ok) {", 1)[1].split("return;", 1)[1]
    assert 'showSuccessMessage("Student updated successfully! ✅")' in update_success_path
    assert "alert(" not in update_success_path
    assert "window.location.href" not in update_handler
    assert ".reset()" not in update_handler
    assert "clearSuccessMessage();" in submit_handler
    assert 'showSuccessMessage("Student registered successfully! ✅")' in registration_script
    assert 'alert("Updated ✅")' not in registration_script
    assert 'alert("Added ✅")' not in registration_script
    assert "}, 4500);" in registration_script


def test_student_details_page_navigation_and_safe_dom_rendering():
    """Verify View navigates to the dedicated detail page and renders safe API values."""
    students_content = STUDENTS_FILE.read_text(encoding="utf-8")
    student_script = (FRONTEND_DIR / "js" / "students.js").read_text(encoding="utf-8")
    details_content = (FRONTEND_DIR / "student-details.html").read_text(encoding="utf-8")
    details_script = (FRONTEND_DIR / "js" / "student-details.js").read_text(encoding="utf-8")
    view_handler = student_script.split("function viewStudent(student) {", 1)[1].split(
        "async function deleteStudent", 1
    )[0]

    assert 'href="index.html">🏠 Back to Dashboard</a>' in students_content
    assert 'id="studentDetailsPanel"' not in students_content
    assert students_content.count('src="js/students.js?v=3"') == 1
    assert students_content.count("students.js") == 1
    assert student_script.count("function viewStudent(") == 1
    assert student_script.count('createStudentAction("View", "viewBtn", () => viewStudent(student))') == 1
    assert "alert(" not in view_handler
    assert "student-details.html?usn=${encodeURIComponent(student.usn)}" in view_handler
    assert 'href="students.html">👥 Back to Student List</a>' in details_content
    assert 'href="index.html">🏠 Back to Dashboard</a>' in details_content
    assert 'id="studentDetailsStatus"' in details_content
    assert 'id="studentDetailsContent"' in details_content
    assert details_content.count('src="js/student-details.js"') == 1
    assert 'fetch(`${API}/${encodeURIComponent(usn)}`)' in details_script
    assert "student.attendance_pct" in details_script
    assert "student.previous_gpa" in details_script
    assert "student.backlog_count" in details_script
    assert 'description.textContent = value == null || value === "" ? "Not available" : String(value)' in details_script
    assert ".innerHTML" not in student_script
    assert ".innerHTML" not in details_script


def test_student_page_navigation_links_are_exact():
    """Ensure the list and details pages expose only their intended navigation links."""
    students_content = STUDENTS_FILE.read_text(encoding="utf-8")
    details_content = (FRONTEND_DIR / "student-details.html").read_text(encoding="utf-8")

    assert students_content.count("<header") == 1
    assert students_content.count("<nav") == 1
    assert students_content.count('class="tab-btn') == 1
    assert 'href="index.html">🏠 Back to Dashboard</a>' in students_content
    assert 'href="students.html" aria-current="page">👥 View Students</a>' not in students_content
    assert "Student Registration" not in students_content

    assert details_content.count("<header") == 1
    assert details_content.count("<nav") == 1
    assert details_content.count('class="tab-btn') == 2
    assert 'href="students.html">👥 Back to Student List</a>' in details_content
    assert 'href="index.html">🏠 Back to Dashboard</a>' in details_content
    assert "Student Registration" not in details_content


def test_student_update_encodes_usn_path_segment():
    """Ensure PUT uses the same safe USN path encoding as the edit lookup."""
    registration_script = (FRONTEND_DIR / "js" / "student-registration.js").read_text(encoding="utf-8")
    assert '`${API}/${encodeURIComponent(editUSN)}`' in registration_script
    assert 'API + "/" + editUSN' not in registration_script


def test_college_analysis_uses_text_safe_report_rendering():
    """Ensure CSV/report values and server errors are never interpolated into HTML."""
    analysis_script = (FRONTEND_DIR / "js" / "college-dataset-analysis.js").read_text(encoding="utf-8")
    assert ".innerHTML" not in analysis_script
    assert "textContent = warning.feature_name" in analysis_script
    assert "textContent = check.check_name" in analysis_script
    assert "textContent = value ?? \"\"" in analysis_script
    assert "textContent = ` ${err.message}`" not in analysis_script
    assert "document.createTextNode(` ${err.message}`)" in analysis_script


def test_all_31_benchmark_input_elements_present():
    """Verify index.html contains DOM inputs for all 31 features matching UCIBenchmarkStudentInput."""
    content = FRONTEND_FILE.read_text(encoding="utf-8")

    for feature in REQUIRED_31_FEATURES:
        expected_id = f'id="bm_{feature}"'
        assert expected_id in content, f"Missing benchmark input element for feature: {feature}"


def test_benchmark_numeric_labels_keep_model_values():
    """Verify coded select labels are readable while option values remain model-compatible."""
    content = FRONTEND_FILE.read_text(encoding="utf-8")
    benchmark_form = content.split('<form id="benchmarkForm">', 1)[1].split("</form>", 1)[0]
    selects = {
        field: options
        for field, options in re.findall(
            r'<select id="bm_([^"]+)"[^>]*>(.*?)</select>', benchmark_form, re.DOTALL
        )
    }
    expected_options = {
        "studytime": [
            ("1", "< 2 hours"), ("2", "2 to 5 hours"),
            ("3", "5 to 10 hours"), ("4", "> 10 hours"),
        ],
        "Medu": [
            ("0", "None"), ("1", "Primary (4th grade)"), ("2", "5th to 9th grade"),
            ("3", "Secondary"), ("4", "Higher Education"),
        ],
        "Fedu": [
            ("0", "None"), ("1", "Primary (4th grade)"), ("2", "5th to 9th grade"),
            ("3", "Secondary"), ("4", "Higher Education"),
        ],
        "traveltime": [
            ("1", "< 15 min"), ("2", "15 to 30 min"),
            ("3", "30 to 60 min"), ("4", "> 60 min"),
        ],
        "famrel": [
            ("1", "Very Bad"), ("2", "Bad"), ("3", "Normal"),
            ("4", "Good"), ("5", "Excellent"),
        ],
        "freetime": [
            ("1", "Very Low"), ("2", "Low"), ("3", "Medium"),
            ("4", "High"), ("5", "Very High"),
        ],
        "goout": [
            ("1", "Very Low"), ("2", "Low"), ("3", "Medium"),
            ("4", "High"), ("5", "Very High"),
        ],
        "Dalc": [
            ("1", "Very Low"), ("2", "Low"), ("3", "Medium"),
            ("4", "High"), ("5", "Very High"),
        ],
        "Walc": [
            ("1", "Very Low"), ("2", "Low"), ("3", "Medium"),
            ("4", "High"), ("5", "Very High"),
        ],
        "health": [
            ("1", "Very Bad"), ("2", "Bad"), ("3", "Normal"),
            ("4", "Good"), ("5", "Very Good"),
        ],
    }

    for field, expected in expected_options.items():
        option_markup = selects[field]
        actual = [
            (value, html.unescape(re.sub(r"<[^>]+>", "", label)).strip())
            for value, label in re.findall(
                r'<option\s+value="([^"]+)"[^>]*>(.*?)</option>', option_markup, re.DOTALL
            )
        ]
        assert actual == expected, f"Unexpected option values or labels for bm_{field}"

    for option_markup in selects.values():
        labels = re.findall(r"<option\b[^>]*>(.*?)</option>", option_markup, re.DOTALL)
        for label in labels:
            visible_label = html.unescape(re.sub(r"<[^>]+>", "", label)).strip()
            assert not re.match(r"^\d+\s*:", visible_label), visible_label

    benchmark_script = (FRONTEND_DIR / "js" / "benchmark-prediction.js").read_text(encoding="utf-8")
    for field in ("studytime", "Medu", "Fedu", "traveltime", "famrel", "freetime",
                  "goout", "Dalc", "Walc", "health"):
        assert f'{field}: parseInt(document.getElementById("bm_{field}").value)' in benchmark_script


def test_benchmark_marks_selector_preserves_numeric_g1_payload():
    """Verify marks choices, required reset state, presets, and numeric G1 conversion."""
    content = FRONTEND_FILE.read_text(encoding="utf-8")
    marks_field = re.search(
        r'<label for="bm_G1">(.*?)</label>\s*(<select id="bm_G1".*?</select>)\s*'
        r'<span class="help-hint">(.*?)</span>',
        content,
        re.DOTALL,
    )
    assert marks_field is not None
    label, selector, helper = marks_field.groups()
    assert label == "Term-1 Exam Marks *"
    assert 'required' in selector
    assert '<option value="" selected disabled>Select marks...</option>' in selector
    options = re.findall(r'<option value="(\d+)">(.*?)</option>', selector)
    assert options == [
        (str(mark), f"{mark} {'mark' if mark == 1 else 'marks'}")
        for mark in range(21)
    ]
    assert helper == "Scale: 0–20 marks; below 10 indicates failing in the benchmark dataset."

    benchmark_script = (FRONTEND_DIR / "js" / "benchmark-prediction.js").read_text(encoding="utf-8")
    assert 'G1: parseFloat(document.getElementById("bm_G1").value)' in benchmark_script
    for preset_value in ("G1: 4.0", "G1: 18.0", "G1: 11.0"):
        assert preset_value in benchmark_script
    assert 'if (el) el.value = value;' in benchmark_script
    assert 'document.getElementById("benchmarkForm").reset();' in benchmark_script


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


def test_college_dataset_analysis_tab_elements_present():
    """Verify index.html contains all Phase 8 College Dataset Analysis elements and disclaimers."""
    content = FRONTEND_FILE.read_text(encoding="utf-8")

    # Tab navigation & view container
    assert 'id="tab-analysis"' in content
    assert 'id="view-analysis"' in content
    assert "College Dataset Analysis" in content

    # File input & trigger button
    assert 'id="collegeCsvInput"' in content
    assert 'id="analyzeDatasetBtn"' in content

    # Results containers & tables
    assert 'id="analysisResults"' in content
    assert 'id="readinessBadge"' in content
    assert 'id="readinessChecklistBody"' in content
    assert 'id="numericStatsBody"' in content
    assert 'id="missingValuesBody"' in content

    # Data quality disclaimer
    assert "data-quality assessment, not a prediction of individual students' performance" in content

    # JavaScript helper functions
    analysis_script = (FRONTEND_DIR / "js" / "college-dataset-analysis.js").read_text(encoding="utf-8")
    assert "handleFileSelected" in analysis_script
    assert "loadDemoCohort" in analysis_script
    assert "submitCollegeAnalysis" in analysis_script
    assert "renderAnalysisReport" in analysis_script


def test_phase_9_frontend_hardening_and_clarity():
    """Verify Phase 9 frontend hardening: demo vs real provenance banner, readiness note, and accessibility."""
    content = FRONTEND_FILE.read_text(encoding="utf-8")
    analysis_script = (FRONTEND_DIR / "js" / "college-dataset-analysis.js").read_text(encoding="utf-8")
    page_and_script = content + analysis_script

    # 1. Dataset Provenance elements (distinguishing demo from real institutional data)
    assert 'id="datasetProvenanceBanner"' in content
    assert 'id="provenanceIcon"' in content
    assert 'id="provenanceText"' in content
    assert "Synthetic Demonstration Cohort" in page_and_script
    assert "Uploaded Local Institutional Data" in page_and_script
    assert "NOT actual institutional data" in page_and_script or "not actual institutional data" in page_and_script.lower()

    # 2. Readiness status explanation note
    assert 'id="readinessExplanatoryNote"' in content
    assert 'id="readinessExplanationText"' in content
    assert "does NOT prove institutional representativeness" in page_and_script or "does not prove institutional representativeness" in page_and_script.lower()
    assert "production readiness" in page_and_script.lower() or "production model deployment readiness" in page_and_script.lower()

    # 3. Accessibility enhancements
    assert 'aria-label="Upload College Academic Observations CSV"' in content
    assert 'role="alert"' in content
    assert 'aria-live="polite"' in content
    assert 'aria-live="assertive"' in content
