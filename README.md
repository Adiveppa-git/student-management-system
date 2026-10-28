# Student Management & AI Early Warning System

A full-stack FastAPI and MongoDB application for managing student records and providing an experimental academic-risk interface. The project also includes tools for uploading, validating, profiling, and assessing de-identified college academic CSV files for prospective offline review.

> The benchmark prediction is based on Portuguese secondary-school data. It is not validated for Indian engineering-college students. College-specific model training is not implemented, and college dataset readiness does not authorize individual prediction, model deployment, or high-stakes academic decisions.

## Table of Contents

- [Overview](#overview)
- [Main Features](#main-features)
- [Technology Stack](#technology-stack)
- [Architecture and Data Flow](#architecture-and-data-flow)
- [Repository Structure](#repository-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [MongoDB Configuration](#mongodb-configuration)
- [Running the Application](#running-the-application)
- [Frontend Pages and UI Tabs](#frontend-pages-and-ui-tabs)
- [API Reference](#api-reference)
- [College Dataset CSV Schema](#college-dataset-csv-schema)
- [Dataset Readiness Assessment](#dataset-readiness-assessment)
- [Using Built-in Synthetic Cohorts](#using-built-in-synthetic-cohorts)
- [Automated Tests](#automated-tests)
- [Synthetic Data Disclaimer](#synthetic-data-disclaimer)
- [Privacy and Data Handling](#privacy-and-data-handling)
- [Known Limitations](#known-limitations)
- [Author and Repository](#author-and-repository)

## Overview

The application has three connected areas:

1. **Student management** — register, list, view, edit, and delete MongoDB student records.
2. **Experimental benchmark model interface** — inspect an existing UCI secondary-school model, its saved metrics, model health, and make a 31-feature prediction request.
3. **College dataset analysis** — upload an authorized de-identified college CSV for schema checks, profiling, risk screening, leakage checks, class-balance review, and an experimental readiness checklist.

The system does not train a college-specific model from uploaded CSV files. The college dataset endpoints are data-quality and readiness analysis tools only.

## Main Features

### Student Management

- Create students with normalized USNs and validated email addresses.
- Store and retrieve optional attendance, internal assessment, assignment, study-hours, GPA, and backlog indicators.
- Search students and filter by branch or academic year.
- List students in batches of 10 with a **View More** control.
- View a dedicated student-details page.
- Edit students from the main dashboard and delete them from the student list with confirmation.
- Enforce duplicate USN checks at record creation and conflict checks when changing USNs.

### AI and Model Inspection

- Check benchmark pipeline health and loaded artifact integrity.
- Display saved holdout metrics, confusion matrix data, and model comparison information.
- Submit the 31 validated features from the UCI Student Performance benchmark to an existing Scikit-learn pipeline.
- Return experimental risk status, probability, confidence, and risk tier with mandatory disclaimers.

### College Dataset Analysis

- Upload a CSV up to 5 MB.
- Require the six de-identified academic columns listed below.
- Check Pydantic data types, numeric ranges, branch and semester consistency, and first-semester rules.
- Profile missing values and numeric summary statistics.
- Detect duplicate `(student_ref, academic_year, semester)` observation keys.
- Detect suspicious target-leakage columns by feature-name patterns.
- Analyze binary labels and verified outcome distributions.
- Produce a seven-check readiness assessment.
- Build preliminary rule-based student risk categories, screening factors, and intervention suggestions.
- Compare attendance, normalized CIE, and risk category across distinct semesters where the upload contains enough history.
- Filter results by risk category, branch, semester, or pseudonymous student reference.
- Export the currently filtered student-risk records to `student-risk-report.csv`.

## Technology Stack

### Backend

- Python
- FastAPI
- Uvicorn
- Pydantic 2
- MongoDB and PyMongo
- python-dotenv
- NumPy, pandas, SciPy, and scikit-learn
- joblib and requests

### Frontend

- HTML5 and CSS
- Browser JavaScript using the Fetch API
- Static frontend files mounted by FastAPI
- No npm or separate frontend build process is defined in this repository

### Testing

- pytest
- FastAPI TestClient through HTTPX

## Architecture and Data Flow

The FastAPI application serves both the API and the static frontend at `/frontend`:

```text
Browser UI
   ├── Student CRUD requests ──> FastAPI student routes ──> MongoDB `students` collection
   └── AI / CSV requests ──────> FastAPI AI routes ──────> In-memory analysis or saved benchmark pipeline
```

- The static frontend defaults its API base to `http://127.0.0.1:8000` and can read a global `window.API_BASE_URL` value if supplied before `api.js` runs.
- Startup attempts to load the benchmark pipeline from `app/ml/artifacts/` into memory. Startup continues if artifacts are unavailable; the health endpoint reports unavailable status in that case.
- Student CRUD operations persist records in MongoDB.
- College audit and analysis functions parse and analyze uploaded content in memory. The implementation does not insert uploaded observation records into MongoDB and does not train a college model.
- CSV risk-report export happens locally in the browser.

## Repository Structure

```text
.
├── app/
│   ├── database/connection.py       # MongoDB connection and environment resolution
│   ├── models/                      # Pydantic request and response schemas
│   ├── ml/
│   │   ├── artifacts/               # Saved benchmark model and metric metadata
│   │   ├── college_data_prep.py     # CSV parsing, validation, profiling, screening, readiness
│   │   ├── dataset.py               # Benchmark dataset loading utilities
│   │   ├── predictor.py             # Artifact loading and benchmark inference
│   │   └── train.py                 # Benchmark training utilities
│   ├── routes/
│   │   ├── ai_routes.py             # AI, benchmark, and college dataset endpoints
│   │   └── student_routes.py        # Student CRUD endpoints
│   └── main.py                      # FastAPI startup, CORS, routers, static frontend mount
├── frontend/
│   ├── index.html                   # Dashboard, registration, benchmark, and analysis tabs
│   ├── students.html                # Student list page
│   ├── student-details.html         # Student detail page
│   ├── css/app.css                  # Shared styles
│   └── js/                          # Browser API and UI logic
├── tests/                           # Student CRUD, AI, college analysis, frontend, and security tests
├── .env.example                     # Sanitized environment-variable template
├── requirements.txt                 # Python dependency ranges
└── README.md
```

## Prerequisites

- Python 3.10 or newer is the project-recommended runtime based on the existing project documentation and tested environment.
- MongoDB 4.4 or newer for student CRUD persistence, as documented by this project.
- A MongoDB server reachable through a local or cloud connection URI.
- Windows PowerShell, or another shell capable of running Python and MongoDB tools.
- No Node.js package manager is required by the checked-in frontend.

There is no checked-in `pyproject.toml`, `setup.cfg`, or package metadata; install dependencies from `requirements.txt`.

## Installation

From PowerShell in the project root:

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If script execution is restricted, Command Prompt activation is also available:

```bat
venv\Scripts\activate.bat
```

Copy the environment template:

```powershell
Copy-Item .env.example .env
```

Do not commit `.env`. The repository `.gitignore` excludes `.env` and related environment files.

## MongoDB Configuration

The database module reads these variables:

| Variable | Behavior |
|---|---|
| `MONGO_URI` | MongoDB connection URI; defaults to `mongodb://localhost:27017/`. |
| `DATABASE_NAME` | Primary database name; takes precedence. |
| `DB_NAME` | Legacy fallback database name. |
| `DATABASE_NAME` and `DB_NAME` | If neither is set, the application uses `student_db`. |

The student collection is fixed as `db["students"]`.

Example local `.env`:

```dotenv
MONGO_URI=mongodb://localhost:27017/
DATABASE_NAME=student_db
CORS_ORIGINS=http://localhost:8000,http://127.0.0.1:8000,http://localhost:3000,http://127.0.0.1:5500
```

`APP_HOST` and `APP_PORT` appear in `.env.example`, but `app/main.py` and `app/database/connection.py` do not read them. They do not change the Uvicorn bind address automatically. Pass host and port explicitly when starting Uvicorn.

## Running the Application

Start MongoDB separately, then start FastAPI from the project root:

```powershell
venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The frontend is static and mounted by the same FastAPI process; no separate frontend server is required. Browser access is served through the backend.

## Application URLs

These are the local URLs configured or mounted by the application:

- Frontend: `http://127.0.0.1:8000/frontend/`
- API root: `http://127.0.0.1:8000/`
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`
- OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`

## Frontend Pages and UI Tabs

- `/frontend/index.html` — student registration, AI dashboard, benchmark predictor, and college dataset analysis.
- `/frontend/students.html` — batch student listing with View, Edit, and Delete actions.
- `/frontend/student-details.html?usn=<USN>` — details for a selected student.

When editing a student, the frontend returns to `index.html` with a USN query parameter and loads it into the registration form as an update operation.

## API Reference

### Student CRUD

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/students` | Create a student; USN uniqueness is checked. |
| `GET` | `/students` | List students; optional `search`, `branch`, and `year` query parameters. |
| `GET` | `/students/{usn}` | Retrieve a student by USN. |
| `PUT` | `/students/{usn}` | Partially update a student. |
| `DELETE` | `/students/{usn}` | Delete a student by USN. |
| `DELETE` | `/delete-student/{id}` | Legacy MongoDB ObjectId-based delete. |

### AI and Dataset Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/ai/health` | Check benchmark pipeline and artifact health. |
| `GET` | `/api/ai/model-metrics` | Retrieve saved benchmark metrics and limitations. |
| `POST` | `/api/ai/benchmark-predict` | Submit the 31 UCI benchmark features for prediction. |
| `POST` | `/api/ai/college/audit-dataset` | Upload a college CSV for schema, quality, duplicate, leakage, and balance audit. |
| `POST` | `/api/ai/college/analyze-dataset` | Upload a college CSV for deeper profiling and seven-check readiness analysis. |

Upload CSVs as multipart form data:

```text
Content-Type: multipart/form-data
field name: file
```

Files must end in `.csv` and be no larger than 5 MB.

## College Dataset CSV Schema

### Required Columns

| Column | Description |
|---|---|
| `student_ref` | Pseudonymous student reference, at least 3 characters and no raw PII. |
| `branch` | Academic branch or department. |
| `academic_year` | Integer academic year from 1 to 5 in the college observation schema. |
| `semester` | Semester integer from 1 to 10, with year/semester consistency checked. |
| `attendance_pct` | Attendance percentage from 0 to 100. |
| `cie_marks_obtained` | CIE marks obtained; cannot exceed the maximum CIE value. |

### Common Optional Columns

| Column | Validation |
|---|---|
| `program` | Defaults to `B.Tech`; requires 2–50 characters if supplied. |
| `cie_max_marks` | Positive numeric maximum, defaulting to 50. |
| `assignment_score_avg` | 0–100 percentage. |
| `previous_sgpa` | 0–10. First-semester rows cannot contain prior positive SGPA. |
| `cumulative_cgpa` | 0–10. First-semester rows cannot contain prior positive CGPA. |
| `gpa_scale_max` | Positive GPA scale, defaulting to 10. |
| `active_backlogs` | Integer 0–30; first-semester rows cannot contain prior backlogs. |
| `credits_registered` | 1–40. |
| `credits_earned_prior` | 0–250. |
| `study_hours_per_week` | 0–80. |
| `verified_outcome` | `PASS`, `FAIL_OR_DETAINED`, `ACADEMIC_PROBATION`, or `WITHDRAWN`. |
| `outcome_source` | Required when `verified_outcome` is supplied. |
| `is_at_risk_label` | Optional binary at-risk label. |

Duplicate column names and missing required headers are rejected as CSV-format errors.

### Binary Label Values

The CSV parser accepts the following `is_at_risk_label` values, case-insensitively:

- At-risk/true: `true`, `1`, `yes`, `t`, or `y`
- Not-at-risk/false: `false`, `0`, `no`, `f`, or `n`

Blank values are parsed as missing and therefore do not count as labeled observations.

## Dataset Readiness Assessment

The readiness engine uses these configured thresholds:

| Check | Configured Requirement |
|---|---|
| Valid observations | At least 100 valid records. |
| Binary labels | At least 80 binary-labeled observations. |
| At-risk observations | At least 15 observations with the true/at-risk class. |
| Minority class | At least 15 observations in the smaller binary class. |
| Validation errors | Validation error rate no greater than 5%. |
| Duplicate records | Zero duplicate `(student_ref, academic_year, semester)` observation keys. |
| Target leakage | No suspicious leakage feature names detected. |
| Population context | At least one valid branch and valid academic-year/semester ranges. |

The seven displayed checks combine these criteria, class balance, label availability, and target-leakage inspection.

### Status Interpretation

- `READY_FOR_REVIEW` — all configured blockers resolved, so the dataset is eligible only for prospective offline human review under the application's own criteria.
- `TRAINING_BLOCKED` — one or more configured blockers remain unresolved.
- No college model is trained even when `READY_FOR_REVIEW` is returned.

`READY_FOR_REVIEW` does **not** establish real-world model accuracy, independently verified institutional outcomes, label quality, algorithmic fairness, institutional representativeness, demographic adequacy, or production readiness.

## Using Built-in Synthetic Cohorts

The College Dataset Analysis tab provides three client-generated cohort buttons:

- **Valid cohort** — 120 synthetic records designed to pass the configured criteria.
- **Small cohort** — a small synthetic cohort intended to trigger sample-size blockers.
- **Leaky cohort** — synthetic records containing `see_marks` and `promotion_status` to exercise target-leakage detection.

Built-in sample cohorts are generated in the browser and explicitly marked as synthetic. They are for testing the CSV upload flow, parsing, readiness display, and schema or leakage checks.

Synthetic labels, outcomes, and records must not be interpreted as genuine institutional observations or verified student outcomes.

## Automated Tests

Run the complete suite from the project root:

```powershell
python -m pytest -q
```

Verbose output is also supported:

```powershell
python -m pytest -v
```

A focused college and integration suite can be run with:

```powershell
python -m pytest tests/test_college_dataset_analysis.py tests/test_college_data_prep.py tests/test_college_dataset_import.py tests/test_ai_routes.py tests/test_frontend_integration.py -q
```

The suite covers student CRUD, benchmark artifacts and prediction behavior, college data preparation, CSV import and analysis, API behavior, frontend integration, configuration, security controls, and MongoDB preservation assumptions. Test results can vary if the local MongoDB contains different baseline records, so inspect failures rather than treating historical README counts as current results.

## Synthetic Data Disclaimer

Synthetic cohorts exercise application behavior only. They are not real academic observations, do not represent verified outcomes, and do not provide evidence of fairness, accuracy, calibration, or population representativeness. Any institutional decision should rely on independently governed institutional data and an approved review process.

## Privacy and Data Handling

- College CSV endpoints are designed as in-memory analysis workflows. Uploaded observation rows are parsed and evaluated without `insert_one`, `update_one`, or `delete` calls to MongoDB in the audit and analysis implementation.
- Student CRUD operations do persist student records in MongoDB.
- The benchmark pipeline loads model files from disk and keeps the pipeline and saved metrics cached in memory when loaded successfully.
- College risk reports should only contain de-identified `student_ref` values. Unsafe raw-looking student references may be withheld or replaced by the screening report with a row-based reference label.
- The browser generates the filtered risk CSV locally for download.
- This README does not claim that web-server access logs, process logs, proxy logs, browser downloads, or external infrastructure retain no copies. Verify the hosting environment, framework logging, reverse proxy, and browser behavior before institutional use.
- Upload only authorized, de-identified data and keep credentials out of `.env`, source control, screenshots, and application responses.

## Known Limitations

### Population Representation

The current population check only requires:

- at least one valid branch;
- academic-year values in the valid 1–5 range; and
- semester values in the valid 1–10 range.

It does not establish coverage across every department, study year, demographic group, disability status, socioeconomic group, campus, cohort, or broader student population. Passing the check should not be read as representativeness evidence.

### Label Provenance

The application validates `is_at_risk_label` syntax and class balance. It does not independently authenticate the person, institution, examination cell, timestamp, collection process, or authorization behind a binary label. A documented `outcome_source` for `verified_outcome` is checked in record validation, but this remains local metadata rather than independent institutional verification.

### Benchmark Model Scope

The existing benchmark pipeline is trained from a UCI Student Performance secondary-school dataset. Its schema and 31 features are not compatible with a college's CIE, CGPA, branch, semester, or backlog records. Its predictions are retained for experimental interface and baseline evaluation only.

### College Model Training

No college-specific training implementation is active in the application, and no college-specific predictive artifact is loaded for uploaded datasets. Dataset status is not model validation.

### Risk Screening

The student risk report is rule-based:

- **At Risk:** attendance below 75%, normalized CIE below 40%, or one or more active backlogs.
- **Moderate Risk:** attendance from 75% through 85%, or normalized CIE from 40% through 60%, with no stronger indicator.
- **Good:** none of the listed indicators.

These thresholds are screening rules, not medical, clinical, legal, or validated institutional decisions.

### Application Security

The repository configures CORS through environment variables and preserves MongoDB/CORS behavior through tests. Authentication, role-based authorization, and user-session management are not represented in the checked-in student routes or frontend. Deployment access controls should be supplied by the hosting environment and must be reviewed separately.

### Full-Stack Behavior

- MongoDB connection failures can prevent student CRUD operations.
- The frontend static API base defaults to port 8000 rather than discovering a deployment automatically.
- The benchmark pipeline status depends on artifact files in `app/ml/artifacts/`.
- `index.backup.html` is a legacy backup and is not the primary mounted navigation target.

## Author and Repository

- Repository: [https://github.com/Adiveppa-git/student-management-system](https://github.com/Adiveppa-git/student-management-system)
- GitHub account visible in the repository URL: [Adiveppa-git](https://github.com/Adiveppa-git)

No separate personal author name or organization name is published in the checked-in source files, so it is not asserted here.
