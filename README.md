# 📝 Student Management System

🚀 **Student Management System** is a full-stack web application designed to manage student records efficiently.
It supports basic operations like **adding, viewing, updating, and deleting students** with a clean UI.

This project demonstrates real-world concepts like **REST API development, database integration, and dynamic frontend interaction**.

---

# 🖼️ Application Preview

---

## 🏠 Add Student
![Home](screenshots/home.png)

---

## ✏️ Edit Student
![Edit](screenshots/edit.png)

---

## 👁 View Student Details
![View](screenshots/view.png)

---

## 📋 View More Students
![More](screenshots/more.png)

---

# ✨ Core Features

### 👨‍🎓 Student Features
- ➕ Add student
- 📋 View student list
- ✏️ Edit student details
- ❌ Delete student
- 👁 View full student information

---

### 🎨 UI Features
- 📊 Serial number display
- 🔽 View More / Show Less option
- 🎯 Color-coded buttons
  - 🔵 Add
  - 🟢 Update
  - 🟡 Edit
  - 🔴 Delete

---

# ⚙️ Quick Start & Environment Configuration

### 1. Prerequisites
- **Python**: Version 3.10 or higher.
- **MongoDB**: Version 4.4 or higher running locally or via a cloud instance.
- **Git**: For version control.

### 2. Environment Setup & Dependency Installation
Create and activate an isolated virtual environment:
```bash
# Clone the repository (if not already cloned)
git clone https://github.com/Adiveppa-git/student-management-system.git
cd student-management-system

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows (Command Prompt / PowerShell):
venv\Scripts\activate
# On Linux / macOS:
source venv/bin/activate

# Install dependencies from manifest
pip install -r requirements.txt
```

### 3. Environment Variables Configuration
Copy the configuration template to initialize your local `.env`:
```bash
cp .env.example .env
```
The application uses `python-dotenv` with `override=False` to load configuration without overriding environment variables set in the host shell, Docker container, or CI/CD runner.

| Variable | Required | Default | Precedence & Description |
| :--- | :---: | :--- | :--- |
| `MONGO_URI` | Optional | `mongodb://localhost:27017/` | Connection URI for MongoDB. Supports standalone, replica sets, and authenticated clusters. |
| `DATABASE_NAME` | Optional | `student_db` | **Primary database name variable**. Takes precedence over `DB_NAME`. |
| `DB_NAME` | Optional | `student_db` | **Legacy fallback variable**. Preserved for backward compatibility with older deployments. |
| `CORS_ORIGINS` | Optional | Local dev origins | Comma-separated list of allowed frontend origins (see CORS section below). |
| `APP_HOST` | Optional | `127.0.0.1` | Application server bind address. |
| `APP_PORT` | Optional | `8000` | Application server bind port. |

> [!IMPORTANT]
> **Database Name Resolution Precedence**:
> `DATABASE_NAME` takes precedence if explicitly supplied. If `DATABASE_NAME` is not set or empty, the application falls back to `DB_NAME`. If neither is defined, the system defaults safely to `"student_db"`.

### 4. Cross-Origin Resource Sharing (CORS) Configuration
- **Local Development Default**: If `CORS_ORIGINS` is unset, the application automatically permits standard local development servers:
  `http://localhost:8000`, `http://127.0.0.1:8000`, `http://localhost:3000`, `http://127.0.0.1:3000`, `http://localhost:5500`, `http://127.0.0.1:5500` with `allow_credentials=True`.
- **Production Frontend Configuration**: Set `CORS_ORIGINS` to a comma-separated list of explicit origin URLs without trailing slashes:
  ```env
  CORS_ORIGINS=https://student-system.your-college.edu,https://admin.your-college.edu
  ```
- **Strict Wildcard Protection**: Under browser CORS specifications (RFC 6454 / Fetch Spec), combining a wildcard origin (`*`) with credentials (`allow_credentials=True`) is invalid and blocked by modern browsers. If wildcard `*` is specified in `CORS_ORIGINS`, the application automatically sets `allow_credentials=False` to avoid security vulnerabilities.

### 5. Running the Application
Ensure MongoDB is running, then launch the FastAPI server using Uvicorn:
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
- **API Root**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Interactive Swagger Documentation**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Alternative ReDoc Documentation**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Web Frontend**: [http://127.0.0.1:8000/frontend](http://127.0.0.1:8000/frontend)

### 6. Running Automated Tests
Execute the full test suite with verbose output:
```bash
pytest -v
```

---

# 🔗 API Features


### 🎓 Student CRUD Endpoints
- `POST /students` — Create new student record (with Pydantic validation and USN uniqueness check).
- `GET /students` — List students with optional query filters (`search`, `branch`, `year`).
- `GET /students/{usn}` — Retrieve a single student by USN.
- `PUT /students/{usn}` — Update student fields with validation.
- `DELETE /students/{usn}` — Delete student record by USN.
- `DELETE /delete-student/{id}` — Legacy delete by MongoDB ObjectId (preserved for backward compatibility).

### 🤖 AI Academic Risk & Early Warning Endpoints (Phase 4, Phase 7 & Phase 8)
- `GET /api/ai/health` — Check model readiness and artifact integrity.
- `GET /api/ai/model-metrics` — Inspect genuine test-set evaluation metrics, confusion matrix, and limitations.
- `POST /api/ai/benchmark-predict` — Execute benchmark risk prediction using validated UCI features.
- `POST /api/ai/college/audit-dataset` — Securely upload, validate, and audit de-identified college CSV datasets (in-memory; zero database writes).
- `POST /api/ai/college/analyze-dataset` — Comprehensive college dataset profiling, missing-value analysis, numeric summary statistics, cohort distributions, and 7-point ML readiness evaluation (`READY_FOR_REVIEW` vs `TRAINING_BLOCKED`). Ephemeral in-memory execution.


#### Example: `POST /api/ai/benchmark-predict`

**Request:**
```json
POST /api/ai/benchmark-predict
Content-Type: application/json

{
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
  "G1": 4.0
}
```

**Response (`200 OK`):**
```json
{
  "is_at_risk": true,
  "risk_status": "At-Risk",
  "risk_probability": 0.8872,
  "confidence": 0.8872,
  "risk_level": "High",
  "model_name": "Random Forest",
  "dataset_source": "https://archive.ics.uci.edu/dataset/320/student+performance",
  "disclaimer": "EXPERIMENTAL BENCHMARK MODEL: This prediction is generated by a model trained exclusively on secondary-school mathematics data from Portugal (Cortez & Silva, 2008). It is NOT intended, calibrated, or validated for making academic determinations for college students or Indian engineering degree programs. Do not make high-stakes interventions based solely on this prediction.",
  "domain_applicability_note": "Domain Applicability Notice: Reliable academic prediction for Indian engineering colleges requires local institution metrics (continuous internals, assignment scores, university attendance percentages, VTU backlogs, and semester SGPA/CGPA). This benchmark model does not accept or process those college-specific indicators.",
  "evaluated_features_count": 31
}
```

#### Example: `GET /api/ai/health`
**Response (`200 OK`):**
```json
{
  "status": "healthy",
  "model_loaded": true,
  "model_type": "RandomForestClassifier",
  "features_count": 31,
  "artifacts_intact": true,
  "message": "Academic risk machine learning pipeline is loaded and operational."
}
```

---

# ⚠️ Important Domain Limitations & AI Safety Disclaimers

> [!WARNING]
> **Benchmark Metrics Do NOT Establish Performance on Indian Engineering Students**:
> 1. **Institutional Domain Gap**: The benchmark model was trained on secondary school students (ages 15–22) in Portugal (Cortez & Silva, 2008). Its 88.61% accuracy and 84.62% recall do **not** imply equivalent predictive power for college students in Indian engineering institutions (VTU / AICTE).
> 2. **No Silent Feature Substitution**: College indicators (`attendance_pct`, `internal_marks_avg`, `previous_gpa`, `backlog_count`) are **not** silently mapped or substituted into the UCI feature schema.
> 3. **Non-Invasive Architecture**: Predictions are strictly on-demand. The benchmark model does **not** modify or automatically attach risk predictions to real student records in MongoDB.

---

# 🧩 Technology Stack

### 💻 Frontend
- HTML5, CSS3, JavaScript (Vanilla)

### ⚙️ Backend & AI
- FastAPI (Python 3.10)
- Scikit-learn (Random Forest & Logistic Regression Pipelines)
- Pydantic v2 (Input validation & response schemas)
- Joblib (Model serialization)

### 🗄️ Database
- MongoDB & Motor / PyMongo

---

# ⚙️ Installation & Setup

### 1️⃣ Clone the repository
```bash
git clone https://github.com/Adiveppa-git/student-management-system.git
cd student-management-system
```

### 2️⃣ Environment Variables
Create a `.env` file in the project root if connecting to a custom MongoDB instance or port (defaults are preconfigured):
```env
# MongoDB Connection (Local or Atlas URI)
MONGO_URI=mongodb://localhost:27017
DATABASE_NAME=student_management

# Optional Frontend API Base URL (if frontend is hosted on a different host/port)
# API_BASE_URL=http://127.0.0.1:8000
```

### 3️⃣ Run Automated Tests
Execute the comprehensive 96-test suite (CRUD, ML pipelines, AI routes, frontend integration, college data preparation, secure dataset import & audit, Phase 8 dataset analysis & model readiness, and Phase 9 security hardening):
```bash
pytest -v
```

### 4️⃣ Start Backend & Access Frontend
Start the FastAPI server:
```bash
uvicorn app.main:app --reload
```

Once running:
* **Interactive Frontend UI**: Open [`http://127.0.0.1:8000/frontend/`](http://127.0.0.1:8000/frontend/) in your browser. The student list is available at [`http://127.0.0.1:8000/frontend/students.html`](http://127.0.0.1:8000/frontend/students.html).
* **Interactive OpenAPI / Swagger Docs**: [`http://127.0.0.1:8000/docs`](http://127.0.0.1:8000/docs)
* **Backend API Base**: [`http://127.0.0.1:8000/`](http://127.0.0.1:8000/)

---

# 📖 How to Use the Frontend (Phase 5 & Phase 8)

The frontend separates student registration and student records into two pages. Use the navigation links at the top of either page to switch between them.

### 1. 👨‍🎓 Student Registration and Records
* **Register**: Open the Student Registration page, fill in Name, USN, Branch, Year, and Email, then click **Add Student**.
* **View Students**: Open the View Students page to see the first three records or choose **View More**.
* **View Details**: Click **View** to inspect the student's record, including available attendance, CGPA, and backlog details.
* **Edit**: Click **Edit** to open the registration form with the selected student's existing details. Submit the form to save the update.
* **Delete**: Click **Delete** and confirm to remove the selected record.

### 2. 📊 AI Dashboard Tab
* **Operational Health**: Displays real-time model status, algorithm name (`RandomForestClassifier`), and evaluated features count (`31`).
* **Test Metrics Grid**: Holds genuine test-set evaluation numbers (88.61% Accuracy, 84.62% Recall, 81.48% Precision, 83.02% F1-score, 93.54% ROC-AUC).
* **Confusion Matrix**: Visual 2x2 grid breakdown of true negatives (48), false positives (5), false negatives (4), and true positives (22).
* **Model Comparison**: Side-by-side comparison between the production Random Forest model and Logistic Regression baseline.
* **Retry Connection**: Provides an interactive retry button if the backend is temporarily offline.

### 3. 🧪 Benchmark Predictor Tab
* **Quick-Fill Presets**: Click **🔴 Struggling Student Profile**, **🟢 Thriving Student Profile**, or **🟡 Average Passing Profile** to immediately populate all 31 features for evaluation.
* **Run Prediction**: Click **⚡ Predict Academic Risk (UCI Model)**.
* **Inspect Output**: View Risk Status (`At-Risk` vs `Normal`), Risk Probability meter, Confidence score, and Risk Tier (`High`, `Medium`, `Low`).
* **Domain Disclaimers**: Review the official dataset disclaimer directly in the response box.

### 4. 🏫 College Dataset Analysis Tab (Phase 8)
* **Select CSV**: Click **📂 Browse Local Computer...** to upload an authorized de-identified CSV dataset (enforces 5 MB limit).
* **Quick Sample Cohorts**: Click **🟢 Valid Cohort (120 rows)**, **🔴 Small Cohort (Blocked)**, or **🟡 Leaky Cohort (Blocked)** to immediately generate and evaluate synthetic cohorts.
* **Inspect Readiness Decision**: View status badge (`READY_FOR_REVIEW` or `TRAINING_BLOCKED`) and defensible split viability.
* **Blockers & Warnings**: Review explicit lists of unmet criteria and advisory data skew warnings.
* **7-Point Checklist**: Inspect status (PASS/FAIL) and quantitative metrics across all seven readiness criteria.
* **Cohorts & Distributions**: View breakdown badges for departments (CSE, ISE, ECE, MECH), study years, and semesters.
* **Numeric Summaries**: Inspect count, min, max, mean, median, and std dev across continuous academic features.
* **Missing Values**: Review completeness percentages per column.
* **Data Quality Disclaimer**: Prominently notes that the report is a data-quality audit, not an individual student prediction.

#### Readiness Assessment

The College Dataset Analysis module evaluates uploaded data against these configured criteria:

* At least 100 valid observations.
* At least 80 binary-labeled observations.
* At least 15 at-risk observations.
* At least 15 observations in the minority class.
* A validation error rate no greater than 5%.
* No duplicate student-year-semester keys.
* No detected target-leakage columns.
* A basic engineering-academic population representation check.

The system reports `READY_FOR_REVIEW` when all configured readiness blockers are resolved. Otherwise, it reports `TRAINING_BLOCKED`.

`READY_FOR_REVIEW` indicates suitability for prospective offline human review under the application's configured checks. It does **not** establish real-world model accuracy, algorithmic fairness, institutional representativeness, or production deployment readiness. Passing readiness checks does not train or validate a predictive model.

#### College Dataset Known Limitations

* **Population representation:** The current check requires at least one valid branch and valid academic-year and semester ranges. It does not establish adequate coverage across all branches, years, demographic groups, or student populations.
* **Label provenance:** Binary risk labels are syntactically validated, but an institutional source is not independently authenticated by the application. Labels should be treated as verified only after their provenance has been independently established.
* **Synthetic data:** Synthetic records are suitable for testing upload, validation, class balance, and readiness behavior. They are not evidence of real-world student outcomes or model performance.
* **Readiness versus prediction:** Dataset readiness does not imply that an individual prediction is accurate, calibrated, fair, or appropriate for a high-stakes academic decision.


---

# 🏫 Engineering-College Academic Data Preparation & ML Readiness (Phase 6)

Phase 6 introduces a separate, validated engineering-college academic data framework designed for future college-specific model development, strictly decoupled from the secondary-school benchmark.

### 📐 College Academic Observation Schema (`CollegeAcademicObservation`)
The schema ([`app/models/college_schemas.py`](file:///c:/Users/ADIVEPPA%20D%20MAMADAPUR/Downloads/student-management-system/app/models/college_schemas.py)) models semester-level academic observations in Indian engineering colleges (AICTE / VTU / autonomous institutions):

| Field | Type | Required | Constraints / Assumptions | Description |
| :--- | :---: | :---: | :--- | :--- |
| `student_ref` | `str` | Yes | 3–64 chars, uppercase | Pseudonymous identifier (hashed USN or token). Zero raw PII. |
| `program` | `str` | Yes (default `B.Tech`) | 2–50 chars | Academic degree program (B.E., B.Tech, M.Tech). |
| `branch` | `str` | Yes | 2–50 chars | Department (e.g. CSE, ISE, ECE, MECH, AIML). |
| `academic_year` | `int` | Yes | 1 to 5 | Academic study year (1–4 for 4-year B.E./B.Tech). |
| `semester` | `int` | Yes | 1 to 10 | Semester number. Must be consistent with `academic_year` (e.g. Year 1 $\rightarrow$ Sem 1 or 2). |
| `attendance_pct` | `float` | Yes | 0.0 to 100.0% | Semester cumulative attendance. 75% is the statutory condonation limit. |
| `cie_marks_obtained` | `float` | Yes | $\ge 0.0, \le \text{cie\_max\_marks}$ | Continuous Internal Evaluation (CIE) / midterm marks earned. |
| `cie_max_marks` | `float` | Yes (default `50.0`) | $> 0.0$ | **Explicit maximum marks** for CIE (avoids silent grading assumptions). |
| `assignment_score_avg`| `float` | No | 0.0 to 100.0% | Continuous assignment / lab coursework score percentage. |
| `previous_sgpa` | `float` | No | 0.0 to 10.0 scale | Preceding semester SGPA. Must be `None` or `0.0` for Semester 1 students. |
| `cumulative_cgpa` | `float` | No | 0.0 to 10.0 scale | Cumulative CGPA prior to current semester. Must be `None` for Semester 1. |
| `gpa_scale_max` | `float` | Yes (default `10.0`) | $> 0.0$ | Explicit grading scale ceiling (10.0 UGC/AICTE standard). |
| `active_backlogs` | `int` | Yes (default `0`) | 0 to 30 | Uncleared backlogs / course arrears. Must be `0` for Semester 1. |
| `credits_registered` | `float` | No (default `20.0`) | 1.0 to 40.0 | Academic credits enrolled in the current semester. |
| `credits_earned_prior`| `float` | No | 0.0 to 250.0 | Cumulative earned credits prior to current semester. |
| `study_hours_per_week`| `float` | No | 0.0 to 80.0 | Self-study hours per week outside classroom instruction. |
| `verified_outcome` | `str` | No | Enum: `PASS`, `FAIL_OR_DETAINED`, `ACADEMIC_PROBATION`, `WITHDRAWN` | Ground-truth outcome label. Optional; only for post-hoc verified records. |
| `is_at_risk_label` | `bool` | No | `True` / `False` | Binary risk ground-truth label. |
| `outcome_source` | `str` | Conditional | Required if `verified_outcome` set | Institutional audit source (e.g. `OFFICIAL_EXAM_CELL`). |

### 🔍 Data Quality & Readiness Audit (`app/ml/college_data_prep.py`)
The reusable data preparation utility ([`app/ml/college_data_prep.py`](file:///c:/Users/ADIVEPPA%20D%20MAMADAPUR/Downloads/student-management-system/app/ml/college_data_prep.py)) runs 6 automated checks:
1. **Numeric Range & Bounds Validation**: Validates attendance (0–100%), CIE marks within max ceiling, and GPA within scale.
2. **Domain Consistency Validation**: Enforces that semesters match academic years, and prevents first-semester records from having prior GPAs or backlogs.
3. **Duplicate Observation Detection**: Evaluates the composite key `(student_ref, academic_year, semester)` to identify and locate conflicting duplicate semester records.
4. **Target Leakage Prevention**: Automatically scans input feature names against known post-examination leakage patterns (`see_marks`, `external_marks`, `end_sem_marks`, `current_sem_sgpa`, `promotion_status`). Flagged fields are marked as HIGH risk and blocked.
5. **Class Balance Reporting**: Calculates true positive vs false negative distribution on verified labeled records.
6. **ML Readiness Checklist**: Evaluates if the dataset satisfies strict criteria before college model training is permitted.

### 🚦 Criteria for Future College Model Training
A college-specific machine learning model will **NOT** be trained until the following criteria checklist is satisfied:
* [x] **Sample Size**: $\ge 100$ valid semester observations from authorized institutional sources.
* [x] **Ground-Truth Labels**: $\ge 80$ verified labeled records backed by official exam cell records.
* [x] **Class Distribution**: $\ge 15$ verified at-risk samples in the minority class to prevent degenerate learning.
* [x] **Zero Target Leakage**: Zero end-semester or post-hoc examination features in the input feature matrix.
* [x] **Deduplication**: Zero unresolved duplicate observations for the same student-semester.
* [x] **Data Quality Error Rate**: $< 5\%$ validation error rate.

*Status: **TRAINING_BLOCKED** until an authorized, labeled institutional dataset is provided. College predictions remain disabled to prevent fabricated predictions.*

### ⚖️ Comparison: UCI Benchmark vs. Future College Model
| Attribute | Current UCI Benchmark (Phase 3–5) | Future College-Specific Model (Phase 6+) |
| :--- | :--- | :--- |
| **Domain** | Secondary School (Portugal) | Engineering Degree Program (India / VTU) |
| **Subject Scope** | Single Subject (Mathematics) | Semester Program Across Multi-Credit Courses |
| **Key Features** | G1 (0–20), absences, study time, alcohol consumption, family background | CIE marks (out of explicit max), attendance %, CGPA (10.0 scale), active backlogs |
| **Operational Role** | Educational benchmarking & architectural demonstration | Institutional early warning & academic advisory interventions |
| **Readiness Status** | Operational (`POST /api/ai/benchmark-predict`) | Schema & validation ready; training blocked pending labeled real data |

---

# 🔒 Secure College Dataset Import & Audit (Phase 7)

Phase 7 implements a secure, leak-free import and audit pipeline for authorized CSV files containing de-identified engineering-college academic observations.

### 🌐 Audit Endpoint: `POST /api/ai/college/audit-dataset`
- **Method**: `POST`
- **Content-Type**: `multipart/form-data` (`file=@dataset.csv`)
- **Status Codes**:
  - `200 OK`: Dataset successfully parsed and comprehensive audit report returned.
  - `400 Bad Request`: File is empty, non-CSV format, or unparseable.
  - `413 Payload Too Large`: Uploaded file exceeds the 5 MB maximum file size limit.
  - `422 Unprocessable Entity`: CSV is missing required academic columns.
  - `500 Internal Server Error`: Unexpected server processing error.

### 📋 Supported CSV Columns

| Column | Type | Required | Default | Bounds / Constraints |
| :--- | :---: | :---: | :---: | :--- |
| `student_ref` | `string` | **Yes** | — | Pseudonymous token/hash (3–64 chars, uppercase). **Zero raw PII**. |
| `branch` | `string` | **Yes** | — | Engineering department code (e.g., `CSE`, `ISE`, `ECE`, `MECH`). |
| `academic_year` | `integer` | **Yes** | — | Study year (1 to 5). Must align with semester. |
| `semester` | `integer` | **Yes** | — | Semester number (1 to 10). Must align with study year. |
| `attendance_pct` | `float` | **Yes** | — | Cumulative attendance percentage (0.0 to 100.0%). |
| `cie_marks_obtained` | `float` | **Yes** | — | Internal test marks scored ($\ge 0.0$ and $\le \text{cie\_max\_marks}$). |
| `cie_max_marks` | `float` | No | `50.0` | Maximum marks ceiling for Continuous Internal Evaluation ($> 0.0$). |
| `program` | `string` | No | `B.Tech` | Degree program (e.g. `B.Tech`, `B.E.`). |
| `assignment_score_avg` | `float` | No | `None` | Continuous assignment average percentage (0.0 to 100.0%). |
| `previous_sgpa` | `float` | No | `None` | Preceding semester SGPA (0.0 to 10.0 scale; `None` or 0 for Sem 1). |
| `cumulative_cgpa` | `float` | No | `None` | Prior cumulative CGPA (0.0 to 10.0 scale; `None` for Sem 1). |
| `gpa_scale_max` | `float` | No | `10.0` | Explicit maximum GPA ceiling ($> 0.0$). |
| `active_backlogs` | `integer` | No | `0` | Count of active uncleared backlogs (0 to 30; must be 0 for Sem 1). |
| `credits_registered` | `float` | No | `20.0` | Course credits enrolled in the observation semester (1.0 to 40.0). |
| `credits_earned_prior`| `float` | No | `None` | Cumulative earned credits prior to observation semester. |
| `study_hours_per_week`| `float` | No | `None` | Weekly self-study hours outside instruction (0.0 to 80.0). |
| `verified_outcome` | `string` | No | `None` | Ground-truth outcome enum (`PASS`, `FAIL_OR_DETAINED`, `ACADEMIC_PROBATION`, `WITHDRAWN`). |
| `is_at_risk_label` | `boolean` | No | `None` | Binary risk ground-truth label (`true`/`false`). |
| `outcome_source` | `string` | No* | `None` | Institutional validation authority (*required if `verified_outcome` set). |

### 🛡️ Privacy Precautions & Data Protection
1. **Strict Pseudonymity**: The pipeline requires pseudonymous student identifiers (`student_ref`). Real-world student names, emails, phone numbers, addresses, passwords, or government IDs are strictly prohibited and never accepted.
2. **In-Memory Volatility**: The audit executes entirely in memory. Uploaded rows are **never inserted into MongoDB** or written to disk. The existing MongoDB student collection remains completely untouched.
3. **No Automatic Training**: The import process never automatically triggers college model training or claims predictive accuracy.
4. **Safe Error Reporting**: Validation failure samples returned in audit reports only display row indices, field names, and error explanations (e.g., `Attendance cannot exceed 100.0%`). No raw record contents are exposed.

### 🚫 Leakage & Quality Validation Rules
- **Target Leakage Detection**: Scans and flags post-examination features (`see_marks`, `external_marks`, `end_sem_marks`, `promotion_status`, `current_sem_sgpa`). Any leakage flags immediately block ML readiness.
- **Duplicate Detection**: Flags multiple observations sharing the identical composite key `(student_ref, academic_year, semester)`.
- **Domain Consistency**: Rejects Semester 1 records reporting prior GPAs or backlogs, and rejects semester/academic-year mismatches (e.g. Year 1 with Semester 5).

### 📊 Example Audit Report (`200 OK`)
```json
{
  "dataset_name": "engineering_college_dataset.csv",
  "total_records": 120,
  "valid_records_count": 120,
  "invalid_records_count": 0,
  "validation_error_rate": 0.0,
  "validation_failures_sample": [],
  "duplicate_observations_count": 0,
  "duplicate_details": [],
  "missing_values_by_field": {},
  "target_leakage_warnings": [],
  "class_balance": {
    "total_records_evaluated": 120,
    "labeled_records_count": 90,
    "unlabeled_records_count": 30,
    "binary_risk_distribution": {
      "at_risk_true_count": 22,
      "at_risk_false_count": 68,
      "at_risk_prevalence_pct": 24.44
    },
    "verified_outcome_distribution": {
      "PASS": 68,
      "FAIL_OR_DETAINED": 22
    }
  },
  "ml_readiness": {
    "is_ready_for_training": true,
    "status": "READY_FOR_COLLEGE_MODEL_TRAINING",
    "blocking_reasons": [],
    "criteria_checklist": {
      "sample_size_ge_100": true,
      "labeled_samples_ge_80": true,
      "minority_class_ge_15": true,
      "zero_target_leakage_features": true,
      "zero_duplicate_observations": true,
      "error_rate_le_5pct": true
    }
  },
  "database_storage_action": "NONE_INSPECTED_ONLY",
  "training_action": "NONE_COLLEGE_TRAINING_BLOCKED",
  "privacy_guarantee": "Evaluated pseudonymously in-memory. Zero records persisted to MongoDB."
}
```

---

# 🔬 College Dataset Analysis & Model Readiness (Phase 8)

Phase 8 extends the college data framework with an in-depth data quality audit, missing-value profiling, numeric summarization, cohort distribution analysis, and an explicit 7-point Machine Learning readiness assessment.

### 🌐 Analysis Endpoint: `POST /api/ai/college/analyze-dataset`
- **Method**: `POST`
- **Content-Type**: `multipart/form-data` (`file=@dataset.csv`)
- **Status Codes**:
  - `200 OK`: Dataset successfully parsed, profiled, and comprehensive readiness report returned.
  - `400 Bad Request`: Non-CSV format, empty file, or unparseable CSV content.
  - `413 Payload Too Large`: Uploaded file exceeds the 5 MB maximum file size limit.
  - `422 Unprocessable Entity`: CSV is missing required academic columns.
  - `500 Internal Server Error`: Unexpected server processing error.

### 📊 Calculated Analysis Fields

| Category | Field Name | Description |
| :--- | :--- | :--- |
| **Observation Counts** | `total_records`, `valid_records_count`, `invalid_records_count` | Total rows, valid rows conforming to schema, and rejected row counts. |
| **Quality & Bounds** | `validation_error_rate`, `validation_failures_sample` | Failure ratio (0.0–1.0) and safe sample of error messages (row index + error explanation; zero PII). |
| **Student Metrics** | `student_metrics` | Total observations, count of unique pseudonymous students (`student_ref`), and observations-per-student ratio. |
| **Deduplication** | `duplicate_observations_count`, `duplicate_details` | Count and details of duplicate observations sharing composite key `(student_ref, academic_year, semester)`. |
| **Missing Values** | `missing_values_summary` | Dictionary mapping every column to `missing_count`, `missing_pct`, and `present_count`. |
| **Numeric Statistics** | `numeric_summary_statistics` | Quantitative summary for all numeric variables: `count`, `min`, `max`, `mean`, `median`, and `std` dev. |
| **Cohort Distributions** | `categorical_distributions` | Distribution breakdowns across engineering branches, academic years, semesters, and degree programs. |
| **Outcomes & Balance**| `outcome_and_class_balance` | Counts of passing vs at-risk observations, labeling rate, at-risk ratio, imbalance ratio string, and outcome authorities. |
| **Student Risk History** | `student_risk_analysis.records[].assessment_history` | Valid rule-based assessments ordered by academic year and semester, with attendance, normalized CIE, and risk-category comparisons when distinct unambiguous periods are available. |
| **Target Leakage** | `target_leakage_warnings` | Flagged post-examination features (`see_marks`, `promotion_status`, `end_sem_marks`) with mitigation advice. |
| **Readiness Assessment**| `readiness_assessment` | Explicit 7-point criteria checklist, status, blockers, warnings, and protocol recommendations. |

Student risk history is derived only from the valid observations in the currently analyzed CSV upload. Academic year and semester provide ordering; they are not calendar assessment dates. Duplicate student-period observations are shown without a trend comparison, invalid observations are excluded, CIE trends require explicit maximum marks in both periods, and no history is persisted between uploads.

### 🚦 7-Point ML Experimental Readiness Criteria

| # | Readiness Check | Threshold / Evaluation Rule | Severity |
| :-: | :--- | :--- | :---: |
| **1** | **Data Quality & Schema Validity** | $\le 5.0\%$ validation failure rate across observations. | **BLOCKER** |
| **2** | **Duplicates & Missing Values** | Zero duplicate student-semester records; zero missing values in mandatory columns. | **BLOCKER** |
| **3** | **Ground-Truth Labels** | $\ge 80$ verified labels backed by documented examination authority (`outcome_source`). | **BLOCKER** |
| **4** | **Sample Size & At-Risk Counts** | $\ge 100$ valid records total; $\ge 15$ verified at-risk positive cases. | **BLOCKER** |
| **5** | **Class Imbalance & Defensible Split** | Minority class $\ge 15$ samples, ensuring stratified 5-fold cross-validation or holdout evaluation is statistically viable without degenerate folds. | **BLOCKER** |
| **6** | **Target Leakage Prevention** | Zero post-hoc or end-semester examination features in the feature set. | **BLOCKER** |
| **7** | **Population Representation** | Recognized engineering branches, valid study years (1–5) and semesters (1–10) on standard 10-point GPA scale. | **BLOCKER** |

### 🚦 Readiness Statuses
- **`READY_FOR_REVIEW`**: The dataset satisfies all automated data-quality and statistical readiness thresholds. It is deemed ready for **human faculty review and experimental evaluation protocol design**.
  > [!IMPORTANT]
  > `READY_FOR_REVIEW` does **NOT** authorize production deployment or automated model training. Human review and offline evaluation design are still mandatory.
- **`TRAINING_BLOCKED`**: The dataset violates one or more readiness criteria. The response includes an explicit list of `readiness_blockers` and actionable `recommendations` for data curation.

### 📋 Example Analysis Response (`200 OK`)
```json
{
  "dataset_name": "authorized_engineering_cohort.csv",
  "total_records": 120,
  "valid_records_count": 120,
  "invalid_records_count": 0,
  "validation_error_rate": 0.0,
  "validation_failures_sample": [],
  "student_metrics": {
    "total_valid_observations": 120,
    "unique_pseudonymous_students": 120,
    "observations_per_student_avg": 1.0,
    "pseudonymity_status": "VERIFIED_NO_RAW_PII"
  },
  "duplicate_observations_count": 0,
  "duplicate_details": [],
  "missing_values_summary": {
    "attendance_pct": { "missing_count": 0, "missing_pct": 0.0, "present_count": 120 },
    "cie_marks_obtained": { "missing_count": 0, "missing_pct": 0.0, "present_count": 120 }
  },
  "numeric_summary_statistics": {
    "attendance_pct": { "count": 120, "min": 61.0, "max": 86.5, "mean": 78.0, "median": 86.5, "std": 11.87 },
    "cie_marks_obtained": { "count": 120, "min": 17.5, "max": 42.0, "mean": 33.17, "median": 41.0, "std": 11.23 }
  },
  "categorical_distributions": {
    "branch_distribution": { "CSE": 27, "ISE": 27, "ECE": 46, "MECH": 20 },
    "academic_year_distribution": { "2": 120 },
    "semester_distribution": { "4": 120 },
    "program_distribution": { "B.Tech": 120 }
  },
  "outcome_and_class_balance": {
    "labeled_records_count": 120,
    "unlabeled_records_count": 0,
    "labeling_rate": 1.0,
    "at_risk_count": 40,
    "passing_count": 80,
    "at_risk_ratio": 0.3333,
    "passing_ratio": 0.6667,
    "imbalance_ratio": "1:2.0",
    "verified_outcome_breakdown": { "PASS": 80, "FAIL_OR_DETAINED": 40 },
    "outcome_sources": ["OFFICIAL_EXAM_CELL"]
  },
  "target_leakage_warnings": [],
  "readiness_assessment": {
    "status": "READY_FOR_REVIEW",
    "is_ready_for_review": true,
    "is_ready_for_training": false,
    "defensible_split_possible": true,
    "readiness_blockers": [],
    "warnings": [],
    "checks": {
      "data_quality_and_schema": { "check_name": "Data Quality and Schema Validity", "passed": true, "severity": "BLOCKER", "details": "Validation failure rate is 0.0%." },
      "duplicates_and_missing_values": { "check_name": "Duplicate Records and Missing Values", "passed": true, "severity": "BLOCKER", "details": "Zero duplicates and zero missing mandatory fields." },
      "ground_truth_labels_availability": { "check_name": "Availability of Verified Ground-Truth Labels", "passed": true, "severity": "BLOCKER", "details": "120 verified labels available." },
      "sample_size_and_at_risk_counts": { "check_name": "Sample Size and At-Risk Example Counts", "passed": true, "severity": "BLOCKER", "details": "Cohort size is sufficient (120 valid, 40 at-risk)." },
      "class_imbalance_and_defensible_split": { "check_name": "Class Imbalance and Defensible Evaluation Split", "passed": true, "severity": "BLOCKER", "details": "Defensible evaluation split is statistically viable (minority has 40 samples)." },
      "potential_target_leakage": { "check_name": "Potential Target Leakage Inspection", "passed": true, "severity": "BLOCKER", "details": "Zero target leakage detected." },
      "population_representation": { "check_name": "Engineering College Population Representation", "passed": true, "severity": "BLOCKER", "details": "Cohort represents 4 branches." }
    },
    "recommendations": [
      "Submit the readiness report for institutional academic advisory and examination cell sign-off.",
      "Design a leak-free evaluation protocol (e.g., student-stratified 5-fold cross-validation or temporal semester-holdout).",
      "Establish benchmark performance with interpretable linear models before proceeding to tree-based ensembles."
    ]
  },
  "disclaimer": "DATA QUALITY AND READINESS ASSESSMENT DISCLAIMER: This report evaluates structural data quality, schema integrity, and statistical readiness for prospective machine learning experimentation. It is NOT an academic risk prediction or evaluation of individual students' performance. College model training remains blocked pending authorized institutional review and experimental evaluation protocol sign-off.",
  "database_storage_action": "NONE_INSPECTED_ONLY",
  "training_action": "NONE_COLLEGE_TRAINING_BLOCKED",
  "privacy_guarantee": "Evaluated pseudonymously in-memory. Zero records persisted to MongoDB. Zero student PII exposed."
}
```

# 🛡️ Testing, Security, and Validation Hardening (Phase 9)

Phase 9 implements comprehensive security hardening, data integrity verification, and validation resilience across backend endpoints, ML artifacts, and frontend interfaces:

### 1. Robust Upload Validation & Attack Surface Reduction
- **Duplicate Column Header Rejection**: Enforces uniqueness across CSV headers. Files containing exact or case-insensitive duplicate column names (e.g., `Branch,branch` or `student_ref,...,student_ref`) are rejected with `HTTP 422 Unprocessable Entity`.
- **Disguised Binary & Non-Text Content Detection**: Safely verifies uploaded payload bytes prior to parsing. Files with null bytes (`\x00`) or binary signatures (e.g., PNG/executable headers disguised with `.csv` extensions) are rejected with `HTTP 400 Bad Request` without server crashes.
- **Strict CSV Syntax Enforcement**: Employs `csv.DictReader(strict=True)` to detect unclosed quotes, malformed line endings, or invalid delimiter sequences.
- **Precise 5 MB Boundary Enforcement**: Confirmed that uploads at the exact boundary of 5,242,880 bytes (5 MB) process cleanly in memory, while uploads of 5,242,881 bytes (5 MB + 1 byte) are cleanly rejected with `HTTP 413 Payload Too Large`.
- **Information Disclosure Prevention**: Error responses return sanitized client error messages without internal file paths, usernames, database credentials, connection strings, or Python tracebacks.

### 2. Verified Data Integrity & Zero Persistence
- **Zero Database Persistence**: College CSV uploads through `POST /api/ai/college/audit-dataset` and `POST /api/ai/college/analyze-dataset` are processed exclusively in-memory. Zero records are inserted, updated, or removed from MongoDB.
- **Original Student Record Preservation**: Automated regression tests verify that MongoDB student document count remains unchanged and the 6 original student documents (`1DB24IS045`, `1DB23IS001`, `1DB25EC096`, `1DB25CS009`, `1DB23IS069`, `1DB22CS020`) retain their exact original fields without AI prediction leakage.
- **Zero Disk Caching**: Uploaded files and temporary records are never written to the local filesystem or temp directory.

### 3. Benchmark ML Artifact Immutability (SHA-256 Verified)
- **Artifact Immutability**: Cryptographic SHA-256 hashes of all existing model artifacts (`student_risk_pipeline.joblib`, `logistic_regression_pipeline.joblib`, `metadata.json`, `metrics.json`) are verified before and after dataset audits/analyses, ensuring byte-for-byte integrity.
- **No Accidental Model Training**: Automated regression tests confirm that zero college-specific models (`college_*.joblib`) are created or trained during any dataset inspection or evaluation.

### 4. Frontend Provenance & Readiness Clarification
- **Demo vs. Real Data Distinction**: The UI explicitly flags synthetic demo presets with a distinct `🧪 Synthetic Demonstration Cohort` banner to prevent confusing demonstration samples with actual college records. Real uploaded files are marked with `🏛️ Uploaded Local Institutional Data`.
- **Readiness Significance**: Clear explanatory callout clarifies that `READY_FOR_REVIEW` indicates compliance with preliminary structural and statistical thresholds for offline faculty review. It explicitly does **not** certify institutional representativeness, algorithmic fairness, or production model deployment readiness.
- **Accessibility & Safe Error Handling**: Enhanced with `role="alert"`, `aria-live="polite"`, `aria-label` tags, and safe handling of malformed API responses.

---

# ⚠️ Remaining Limitations & Privacy Guarantees

1. **Secondary-School Benchmark Limitation**:
   - The pre-trained benchmark model in `app/ml/artifacts/` was trained exclusively on Portuguese secondary-school mathematics students (Cortez & Silva, 2008).
   - Its features operate on a 0–20 grading scale and require secondary-school demographic indicators (e.g., parental cohabitation, family support, travel time, and absence counts).
   - It is **NOT** calibrated, validated, or clinically intended for making academic determinations for Indian engineering college students (VTU / AICTE credit systems, USN, branches, CIE/SEE marks, SGPA/CGPA, and active backlogs).
   - Benchmark predictions are provided strictly for comparative evaluation and baseline demonstration.

2. **College-Specific Training is NOT Implemented or Authorized**:
   - Phases 6 through 10.2 implement data preparation, schema validation, dataset profiling, and deployment configuration remediation only.
   - **No college-specific ML model has been trained, and college-specific training is strictly unauthorized by this change.**
   - All dataset import and analysis endpoints (`POST /api/ai/college/audit-dataset` and `POST /api/ai/college/analyze-dataset`) execute strictly in-memory without persisting records or triggering model training.

3. **Dual-Schema Separation**: College-specific indicators (`attendance_pct`, `cie_marks_obtained`, `cumulative_cgpa`, `active_backlogs`) remain strictly separated from the UCI benchmark feature schema. Real college risk predictions require local semester data collection and institutional sign-off.
4. **Non-Invasive Architecture**: Benchmark predictions are strictly on-demand in the UI and are **never** automatically saved or attached to existing student records in MongoDB.
5. **Zero Persistence on Audit / Analysis**: Uploading CSV datasets through `POST /api/ai/college/audit-dataset` or `POST /api/ai/college/analyze-dataset` executes entirely in memory. Zero records are written to MongoDB. The 6 original MongoDB student records remain completely untouched.
6. **No Production Readiness Claims**: A status of `READY_FOR_REVIEW` indicates structural and statistical readiness for offline experimental evaluation; it does not prove model accuracy, institutional representativeness, algorithmic fairness, or production deployment readiness. Institutional sign-off, ethical review, independent label-provenance verification, and leak-free validation protocol design are required.

---

# 🛡️ Safe Deployment Configuration Remediation (Phase 10.2)

Phase 10.2 implements non-breaking, safety-hardened configuration and deployment readiness updates based on the Phase 10.1 audit report:

1. **Enhanced Repository Hygiene (`.gitignore`)**:
   - Added ignore patterns for virtual environments (`.venv/`, `venv/`, `env/`), editor artifacts (`.vscode/`, `.idea/`), test coverage (`.coverage`, `htmlcov/`), application logs (`*.log`, `logs/`), and operating system metadata (`.DS_Store`, `Thumbs.db`).
   - Verified that zero sensitive files, virtual environments, or credentials are tracked in Git.

2. **Environment Variable Configuration & Safe Loading**:
   - Integrated `python-dotenv` with `override=False` to respect environment variables explicitly passed by the OS, container runtime, or CI/CD runner.
   - Resolved the `DATABASE_NAME` vs `DB_NAME` configuration discrepancy: `DATABASE_NAME` takes primary precedence, falling back to `DB_NAME` for backward compatibility, with a safe default of `"student_db"`.
   - Created root [`.env.example`](file:///c:/Users/ADIVEPPA%20D%20MAMADAPUR/Downloads/student-management-system/.env.example) containing sanitized placeholders and zero actual secrets or credentials.

3. **Explicit Dependency Manifest (`requirements.txt`)**:
   - Created a verified, tested [requirements.txt](file:///c:/Users/ADIVEPPA%20D%20MAMADAPUR/Downloads/student-management-system/requirements.txt) manifest recording compatible versions for runtime dependencies and clearly identifying testing dependencies (`pytest`, `httpx`).

4. **Configurable and Safe CORS Handling**:
   - Updated `app/main.py` to parse `CORS_ORIGINS` dynamically from environment variables.
   - Configured safe explicit local-development origins by default.
   - Enforced modern browser security standards: if wildcard `*` is specified in origins, `allow_credentials` is strictly forced to `False`.

5. **ML Startup Diagnostics & Health Integrity**:
   - Replaced silent startup exception suppression with structured logging via `uvicorn.error`.
   - Preserved fault-tolerant server startup when model artifacts are absent.
   - Verified that `/api/ai/health` accurately returns `HTTP 503` with operational status when artifacts are unreadable, without leaking filesystem paths, credentials, or internal stack traces.

---

# 🧪 Automated Test Verification

All automated tests can be executed with:
```bash
pytest -v
```

The focused college dataset analysis and integration suites can be run with:
```bash
python -m pytest tests/test_college_dataset_analysis.py tests/test_college_data_prep.py tests/test_college_dataset_import.py tests/test_ai_routes.py tests/test_frontend_integration.py -q
```
Check the current terminal output for the actual test count and warnings in your environment.

**Actual Test Output**:
```text
====================== 113 passed, 8 warnings in 5.19s =======================
```
* **113 tests passed** across student CRUD operations, ML model pipelines, AI routing, frontend integration, college data preparation, secure dataset import/audit, Phase 8 dataset analysis and model readiness, Phase 9 security, data integrity, and hardening regression tests, and Phase 10.2 configuration and deployment remediation tests.
* **0 failures**, **0 errors**.
