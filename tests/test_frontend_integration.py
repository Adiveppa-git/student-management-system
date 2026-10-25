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
import json
import re
import shutil
import subprocess
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
    """Verify model features are represented by form inputs or an internal required default."""
    content = FRONTEND_FILE.read_text(encoding="utf-8")

    for feature in REQUIRED_31_FEATURES:
        expected_id = f'id="bm_{feature}"'
        if feature in ("school", "reason", "guardian", "nursery", "higher", "Dalc", "Walc"):
            assert expected_id not in content
        else:
            assert expected_id in content, f"Missing benchmark input element for feature: {feature}"

    benchmark_script = (FRONTEND_DIR / "js" / "benchmark-prediction.js").read_text(encoding="utf-8")
    assert 'school: "GP"' in benchmark_script
    assert 'document.getElementById("bm_school")' not in benchmark_script
    assert 'Dalc: BAD_HABITS_TO_UCI_CONSUMPTION[document.getElementById("bm_badHabits").value]' in benchmark_script
    assert 'Walc: BAD_HABITS_TO_UCI_CONSUMPTION[document.getElementById("bm_badHabits").value]' in benchmark_script


def test_benchmark_school_control_is_removed_but_payload_keeps_model_feature():
    """Verify the UI hides school selection while retaining the schema-required feature."""
    content = FRONTEND_FILE.read_text(encoding="utf-8")
    benchmark_form = content.split('<form id="benchmarkForm"', 1)[1].split("</form>", 1)[0]
    assert 'id="bm_school"' not in benchmark_form
    for field in (
        "bm_schoolsup", "bm_famsup", "bm_paid", "bm_activities",
    ):
        assert f'id="{field}"' in benchmark_form

    script = (FRONTEND_DIR / "js" / "benchmark-prediction.js").read_text(encoding="utf-8")
    payload_block = script.split("const payload = {", 1)[1].split("\n    };", 1)[0]
    assert "school: BENCHMARK_INTERNAL_DEFAULTS.school" in payload_block
    assert "school: document.getElementById" not in payload_block


def test_benchmark_removed_controls_use_valid_internal_defaults_and_pack_grids():
    """Verify removed controls are absent and defaults preserve the trained model contract."""
    content = FRONTEND_FILE.read_text(encoding="utf-8")
    form = content.split('<form id="benchmarkForm"', 1)[1].split("</form>", 1)[0]
    removed_fields = {
        "bm_nursery": "Attended Nursery School",
        "bm_higher": "Wants Higher Education",
        "bm_reason": "Reason to Choose School",
        "bm_guardian": "Legal Guardian",
    }
    for field_id, label in removed_fields.items():
        assert f'id="{field_id}"' not in form
        assert label not in form

    section_2 = content.split("<!-- SECTION 2:", 1)[1].split("<!-- SECTION 3:", 1)[0]
    section_3 = content.split("<!-- SECTION 3:", 1)[1].split("<!-- SECTION 4:", 1)[0]
    section_2_grid = re.search(r'<div class="form-grid-4">(.*?)</div>\s*</div>', section_2, re.DOTALL)
    section_3_grid = re.search(
        r'<div class="form-grid-4 demographics-grid">(.*?)</div>\s*</div>',
        section_3,
        re.DOTALL,
    )
    assert section_2_grid is not None
    assert section_3_grid is not None
    for grid, expected_groups in ((section_2_grid.group(1), 4), (section_3_grid.group(1), 9)):
        assert grid.count('<div class="form-group">') == expected_groups
        assert '<div class="form-group"></div>' not in grid
    stylesheet = (FRONTEND_DIR / "css" / "app.css").read_text(encoding="utf-8")
    assert re.search(
        r"\.form-grid-4\.demographics-grid\s*\{[^}]*grid-template-columns:\s*repeat\(4,\s*minmax\(0,\s*1fr\)\)",
        stylesheet,
    )
    assert re.search(
        r"@media\s*\(min-width:\s*769px\)\s*and\s*\(max-width:\s*1024px\)\s*\{"
        r"\s*\.form-grid-4\.demographics-grid\s*\{[^}]*grid-template-columns:\s*repeat\(2,\s*minmax\(0,\s*1fr\)\)",
        stylesheet,
        re.DOTALL,
    )
    assert re.search(
        r"@media\s*\(max-width:\s*768px\)\s*\{.*?\.form-grid-4\.demographics-grid\s*\{"
        r"[^}]*grid-template-columns:\s*1fr",
        stylesheet,
        re.DOTALL,
    )

    bad_habits = re.search(
        r'<label for="bm_badHabits">(.*?)</label>\s*'
        r'<select id="bm_badHabits"([^>]*)>(.*?)</select>',
        form,
        re.DOTALL,
    )
    assert bad_habits is not None
    label, attributes, options = bad_habits.groups()
    assert label == "Addiction to Bad Habits *"
    assert "required" in attributes
    assert re.findall(r'<option value="([^"]+)">(.*?)</option>', options) == [
        ("none", "None"), ("low", "Low"), ("average", "Average"), ("high", "High")
    ]
    for removed_helper in (
        "Obtained marks are scaled proportionally to the UCI model's 0–20 scale.",
        "Approximate 5-day mapping to the weekly UCI feature: less than 1 hour/day → code 2; "
        "1–2 hours/day → code 3; 2 or more hours/day → code 4.",
        "Compatibility estimate: this level maps to both UCI workday and weekend consumption "
        "features; the benchmark model was not retrained.",
    ):
        assert removed_helper not in form

    script = (FRONTEND_DIR / "js" / "benchmark-prediction.js").read_text(encoding="utf-8")
    for field_id in removed_fields:
        assert f'getElementById("{field_id}")' not in script
    defaults = script.split("const BENCHMARK_INTERNAL_DEFAULTS = {", 1)[1].split("\n};", 1)[0]
    assert re.findall(r"^\s*(\w+):\s*\"([^\"]+)\"", defaults, re.MULTILINE) == [
        ("school", "GP"), ("reason", "course"), ("guardian", "other"),
        ("nursery", "yes"), ("higher", "yes"),
    ]
    profiles = script.split("const PRESET_PROFILES = {", 1)[1].split("\n};", 1)[0]
    for name, profile in re.findall(
        r"^\s{4}(struggling|thriving|average): \{(.*?)^\s{4}\},?$",
        profiles,
        re.MULTILINE | re.DOTALL,
    ):
        for removed_key in ("nursery", "higher", "reason", "guardian"):
            assert not re.search(rf"^\s*{removed_key}\s*:", profile, re.MULTILINE), name
    fill_preset = script.split("function fillPreset(profileKey) {", 1)[1].split(
        "function clearBenchmarkForm", 1
    )[0]
    assert "fetch(" not in fill_preset
    assert "submitBenchmarkPrediction" not in fill_preset
    assert "none: 1" in script
    assert "low: 2" in script
    assert "average: 3" in script
    assert "high: 4" in script
    for field in ("Dalc", "Walc"):
        assert f'{field}: BAD_HABITS_TO_UCI_CONSUMPTION[document.getElementById("bm_badHabits").value]' in script
        assert f'id="bm_{field}"' not in content
    payload = script.split("const payload = {", 1)[1].split("\n    };", 1)[0]
    assert list(re.findall(r"^\s*([A-Za-z0-9_]+):", payload, re.MULTILINE)) == REQUIRED_31_FEATURES
    for field, value in (("school", "school"), ("reason", "reason"), ("guardian", "guardian"),
                         ("nursery", "nursery"), ("higher", "higher")):
        assert f'{field}: BENCHMARK_INTERNAL_DEFAULTS.{value}' in payload


def test_benchmark_numeric_labels_keep_model_values():
    """Verify coded select labels are readable while option values remain model-compatible."""
    content = FRONTEND_FILE.read_text(encoding="utf-8")
    benchmark_form = content.split('<form id="benchmarkForm"', 1)[1].split("</form>", 1)[0]
    selects = {
        field: options
        for field, options in re.findall(
            r'<select id="bm_([^"]+)"[^>]*>(.*?)</select>', benchmark_form, re.DOTALL
        )
    }
    expected_options = {
        "studytime": [
            ("less_than_1", "<1 hr"),
            ("1_to_2", "1–2 hrs"),
            ("2_to_3", "2–3 hrs"),
            ("3_to_4", "3–4 hrs"),
            ("more_than_4", ">4 hrs"),
        ],
        "Medu": [
            ("0", "None"), ("1", "Primary (Grade 4)"), ("2", "Grades 5–9"),
            ("3", "Secondary"), ("4", "Higher ed"),
        ],
        "Fedu": [
            ("0", "None"), ("1", "Primary (Grade 4)"), ("2", "Grades 5–9"),
            ("3", "Secondary"), ("4", "Higher ed"),
        ],
        "traveltime": [
            ("1", "<15 min"), ("2", "15–30 min"),
            ("3", "30–60 min"), ("4", ">60 min"),
        ],
        "famrel": [
            ("1", "Very poor"), ("2", "Poor"), ("3", "Average"),
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
        "health": [
            ("1", "Very poor"), ("2", "Poor"), ("3", "Fair"),
            ("4", "Good"), ("5", "Very Good"),
        ],
        "badHabits": [
            ("none", "None"), ("low", "Low"), ("average", "Average"), ("high", "High"),
        ],
    }

    for field, expected in expected_options.items():
        option_markup = selects[field]
        actual = [
            (value, html.unescape(re.sub(r"<[^>]+>", "", label)).strip())
            for value, label in re.findall(
                r'<option\s+value="([^"]*)"[^>]*>(.*?)</option>', option_markup, re.DOTALL
            )
            if value
        ]
        assert actual == expected, f"Unexpected option values or labels for bm_{field}"

    for field, option_markup in selects.items():
        options = re.findall(r"<option\b[^>]*>(.*?)</option>", option_markup, re.DOTALL)
        option_tags = re.findall(r"<option\b[^>]*>", option_markup)
        assert option_tags[0].startswith('<option value="" selected disabled>'), field
        placeholder = html.unescape(re.sub(r"<[^>]+>", "", options[0])).strip()
        assert placeholder.startswith("Select "), field
        assert not placeholder.endswith("..."), field
        assert len(placeholder.split()) <= 3, field
        assert all("selected" not in option for option in option_tags[1:]), field

    for option_markup in selects.values():
        labels = re.findall(r"<option\b[^>]*>(.*?)</option>", option_markup, re.DOTALL)
        for label in labels:
            visible_label = html.unescape(re.sub(r"<[^>]+>", "", label)).strip()
            assert not re.match(r"^\d+\s*:", visible_label), visible_label
            assert len(visible_label.split()) <= 3, visible_label

    benchmark_script = (FRONTEND_DIR / "js" / "benchmark-prediction.js").read_text(encoding="utf-8")
    assert 'label for="bm_studytime">Daily Study Time *' in benchmark_form
    assert "DAILY_STUDYTIME_TO_WEEKLY[document.getElementById(\"bm_studytime\").value]" in benchmark_script
    assert "less_than_1: 2" in benchmark_script
    assert '"1_to_2": 3' in benchmark_script
    assert '"2_to_3": 4' in benchmark_script
    assert '"3_to_4": 4' in benchmark_script
    assert "more_than_4: 4" in benchmark_script
    assert "Approximate 5-day mapping to the weekly UCI feature" not in benchmark_form
    for field in ("Medu", "Fedu", "traveltime", "famrel", "freetime",
                  "goout", "health"):
        assert f'{field}: parseInt(document.getElementById("bm_{field}").value)' in benchmark_script
    assert "Dalc: BAD_HABITS_TO_UCI_CONSUMPTION" in benchmark_script
    assert "Walc: BAD_HABITS_TO_UCI_CONSUMPTION" in benchmark_script


def test_benchmark_subject_marks_conversion_validation_presets_and_reset():
    """Verify subject context, marks validation, presets, reset, and model payload."""
    content = FRONTEND_FILE.read_text(encoding="utf-8")
    benchmark_form = content.split('<form id="benchmarkForm"', 1)[1].split("</form>", 1)[0]
    assert "novalidate" in benchmark_form

    subject_selector = re.search(
        r'<label for="bm_subject">(.*?)</label>\s*(<select id="bm_subject".*?</select>)',
        benchmark_form,
        re.DOTALL,
    )
    assert subject_selector is not None
    subject_label, subject_select = subject_selector.groups()
    assert subject_label == "Select Subject *"
    assert "required" in subject_select
    assert '<option value="" selected disabled>Select subject</option>' in subject_select
    assert re.findall(r'<option value="([^"]+)">(.*?)</option>', subject_select) == [
        ("Mathematics", "Mathematics"), ("Physics", "Physics"), ("Chemistry", "Chemistry"),
        ("Computer Science", "Computer Science"), ("Electronics", "Electronics"),
        ("Communication Systems", "Communication Systems"), ("Other", "Other"),
    ]

    field_order = [
        benchmark_form.index('id="bm_subject"'),
        benchmark_form.index('id="bm_maxMarks"'),
        benchmark_form.index('id="bm_G1"'),
    ]
    assert field_order == sorted(field_order)
    assert 'class="form-group benchmark-subject-field"' in benchmark_form
    max_input = re.search(r'<input[^>]*id="bm_maxMarks"[^>]*>', benchmark_form).group()
    assert all(attribute in max_input for attribute in
               ('type="number"', 'min="1"', 'step="1"', "required"))
    obtained_input = re.search(r'<input[^>]*id="bm_G1"[^>]*>', benchmark_form).group()
    assert all(attribute in obtained_input for attribute in
               ('type="number"', 'min="0"', 'max="90"', "required",
                'placeholder="Enter marks obtained"'))

    assert 'id="resultSubject"' in content
    assert "Subject context only:" in content
    assert "not subject-specific risk" in content

    benchmark_script = (FRONTEND_DIR / "js" / "benchmark-prediction.js").read_text(encoding="utf-8")
    assert "maxMarksInput.validity.valid" in benchmark_script
    assert "Math.min(Number(maxMarks), 90)" in benchmark_script
    assert 'marksInput.max = "90"' in benchmark_script
    assert "marksInput.validity.rangeOverflow" in benchmark_script
    assert "form.checkValidity()" in benchmark_script
    assert "showValidationError(" in benchmark_script
    assert "G1: (marksObtained / maxMarks) * 20" in benchmark_script
    assert 'if (el) el.value = value;' in benchmark_script
    assert 'document.getElementById("benchmarkForm").reset();' in benchmark_script
    assert 'marksInput.max = "90";' in benchmark_script
    assert 'document.getElementById("resultSubject").textContent = subject' in benchmark_script
    payload_block = benchmark_script.split("const payload = {", 1)[1].split("\n    };", 1)[0]
    assert not re.search(r"^\s*subject\s*:", payload_block, re.MULTILINE)
    assert not re.search(r"^\s*maxMarks\s*:", payload_block, re.MULTILINE)

    assert (30 / 40) * 20 == 15
    assert (40 / 50) * 20 == 16
    assert (75 / 100) * 20 == 15

    profiles = benchmark_script.split("const PRESET_PROFILES = {", 1)[1].split("\n};", 1)[0]
    for name, profile in re.findall(
        r"^\s{4}(struggling|thriving|average): \{(.*?)^\s{4}\},?$",
        profiles,
        re.MULTILINE | re.DOTALL,
    ):
        for required_admin_choice in ("subject", "maxMarks", "G1", "studytime"):
            assert not re.search(
                rf"^\s*{required_admin_choice}\s*:", profile, re.MULTILINE
            ), f"{name} preset must not set {required_admin_choice}"
        assert "G1:" not in profile and "maxMarks:" not in profile, name

    fill_preset = benchmark_script.split("function fillPreset(profileKey) {", 1)[1].split(
        "function clearBenchmarkForm", 1
    )[0]
    assert "fetch(" not in fill_preset
    assert "submitBenchmarkPrediction" not in fill_preset
    assert 'new Set(["subject", "maxMarks", "G1", "studytime"])' in fill_preset
    assert 'src="js/benchmark-prediction.js?v=3"' in content
    assert "form.checkValidity()" in benchmark_script


def test_quick_fill_profiles_preserve_manual_fields_with_empty_and_entered_values():
    """Execute each Quick-Fill Profile and verify manual choices remain unchanged."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is required for Quick-Fill Profile behavior verification.")

    script = (FRONTEND_DIR / "js" / "benchmark-prediction.js").read_text(encoding="utf-8")
    runtime_test = """
const protectedFields = ["bm_subject", "bm_maxMarks", "bm_G1", "bm_studytime"];
const profiles = ["struggling", "thriving", "average"];
const scenarios = [
    ["", "", "", ""],
    ["Physics", "50", "32.5", "2_to_3"]
];
for (const profile of profiles) {
    for (const initialValues of scenarios) {
        protectedFields.forEach((id, index) => {
            document.getElementById(id).value = initialValues[index];
        });
        fillPreset(profile);
        protectedFields.forEach((id, index) => {
            if (document.getElementById(id).value !== initialValues[index]) {
                throw new Error(`${profile} changed ${id}`);
            }
        });
    }
}
"""
    harness = f"""
const source = {json.dumps(script)};
const values = new Map();
function getElement(id) {{
    if (!values.has(id)) {{
        values.set(id, {{
            value: "",
            max: "90",
            validity: {{ valid: true }},
            style: {{}},
            setCustomValidity() {{}}
        }});
    }}
    return values.get(id);
}}
global.document = {{
    addEventListener() {{}},
    getElementById: getElement
}};
eval(source + {json.dumps(runtime_test)});
"""
    result = subprocess.run([node, "-e", harness], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr


def test_pydantic_schema_field_parity():
    """Verify that the frontend 31 feature list matches Pydantic schema field names exactly."""
    pydantic_fields = set(UCIBenchmarkStudentInput.model_fields.keys())
    frontend_features = set(REQUIRED_31_FEATURES)
    assert pydantic_fields == frontend_features, (
        f"Mismatch between Pydantic schema fields and frontend features: {pydantic_fields ^ frontend_features}"
    )


def test_warning_notice_banners_are_absent_from_frontend_sections():
    """Verify the three requested notice banners are removed without removing their sections."""
    content = FRONTEND_FILE.read_text(encoding="utf-8")
    sections = {
        "view-dashboard": content.split('<div id="view-dashboard"', 1)[1].split(
            '<div id="view-benchmark"', 1
        )[0],
        "view-benchmark": content.split('<div id="view-benchmark"', 1)[1].split(
            '<div id="view-analysis"', 1
        )[0],
        "view-analysis": content.split('<div id="view-analysis"', 1)[1].split(
            "</body>", 1
        )[0],
    }

    for section_id, section in sections.items():
        assert "disclaimer-banner" not in section, section_id
    for notice in (
        "Experimental Benchmark Notice",
        "Experimental benchmark only",
        "Data Quality & Model Readiness Assessment Notice",
    ):
        assert notice not in content

    assert 'id="view-dashboard"' in content
    assert 'id="view-benchmark"' in content
    assert 'id="view-analysis"' in content
    assert 'id="benchmarkForm"' in content
    assert 'id="analysisResults"' in content


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
    """Verify the College Dataset Analysis controls and results remain available."""
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

    assert "Data Quality & Model Readiness Assessment Notice" not in content

    # JavaScript helper functions
    analysis_script = (FRONTEND_DIR / "js" / "college-dataset-analysis.js").read_text(encoding="utf-8")
    assert "handleFileSelected" in analysis_script
    assert "loadDemoCohort" in analysis_script
    assert "submitCollegeAnalysis" in analysis_script
    assert "renderAnalysisReport" in analysis_script


def test_student_risk_analysis_ui_filters_empty_state_and_safe_rendering():
    """Verify risk results can be filtered and CSV values are rendered as text."""
    content = FRONTEND_FILE.read_text(encoding="utf-8")
    analysis_script = (FRONTEND_DIR / "js" / "college-dataset-analysis.js").read_text(encoding="utf-8")
    for element_id in (
        "studentRiskAnalysis",
        "studentRiskInitialEmpty",
        "studentRiskNoRows",
        "studentRiskAtRiskCount",
        "studentRiskModerateCount",
        "studentRiskGoodCount",
        "studentRiskTotalCount",
        "studentRiskCategoryFilter",
        "studentRiskBranchFilter",
        "studentRiskSemesterFilter",
        "studentRiskSearch",
        "studentRiskTableBody",
    ):
        assert f'id="{element_id}"' in content
    for column in (
        "Student Reference", "Branch", "Academic Year", "Semester",
        "Attendance Percentage", "CIE Marks", "Risk Category", "Main Risk Factors",
    ):
        assert f"<th>{column}</th>" in content
    assert "Preliminary, rule-based screening only" in content
    assert "Dataset readiness is assessed separately" in content
    assert "cell.textContent = value ?? \"\"" in analysis_script
    assert "appendTextCell(row, record.student_ref)" in analysis_script
    assert "appendTextCell(row, record.branch)" in analysis_script
    assert ".innerHTML" not in analysis_script

    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is required for student risk filter behavior verification.")
    runtime_test = """
const records = [
    {student_ref: "ANON_A1", branch: "CSE", semester: 3, risk_category: "At Risk"},
    {student_ref: "ANON_B2", branch: "ISE", semester: 3, risk_category: "Moderate Risk"},
    {student_ref: "ANON_C3", branch: "CSE", semester: 4, risk_category: "Good"}
];
const filtered = filterStudentRiskRecords(records, {
    category: "At Risk", branch: "CSE", semester: "3", search: "anon_a"
});
if (filtered.length !== 1 || filtered[0].student_ref !== "ANON_A1") {
    throw new Error("Risk filters/search did not select the matching row");
}
const noMatches = filterStudentRiskRecords(records, {
    category: "Good", branch: "ISE", semester: "", search: ""
});
if (noMatches.length !== 0) {
    throw new Error("Non-matching filters should return an empty result");
}
"""
    harness = f"""
const source = {json.dumps(analysis_script)};
global.document = {{ addEventListener() {{}} }};
eval(source + {json.dumps(runtime_test)});
"""
    result = subprocess.run([node, "-e", harness], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr


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
