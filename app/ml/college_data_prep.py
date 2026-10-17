"""Engineering College Academic Data Preparation and ML Readiness Utilities.

Provides reusable data validation, quality auditing, duplicate detection,
target-leakage inspection, class-balance analysis, and ML readiness evaluation.
Operates independently of database storage and preserves student privacy.
"""

import csv
import io
import statistics
from collections import Counter
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from pydantic import ValidationError

from app.models.college_schemas import CollegeAcademicObservation

# Known target leakage and post-hoc feature identifiers
SUSPICIOUS_LEAKAGE_PATTERNS = {
    "see_marks": "Semester End Examination (SEE) marks are determined at the end of the semester and cause circular target leakage.",
    "external_marks": "External university examination marks are not available at early-warning prediction time.",
    "end_sem_marks": "End-semester marks reflect the post-course evaluation, introducing post-hoc outcome leakage.",
    "current_sem_sgpa": "Current semester SGPA is the final outcome to be predicted or prevented, not an input.",
    "final_sgpa": "Final SGPA is computed after exams and constitutes direct ground-truth leakage.",
    "promotion_status": "Promotion status is assigned after semester results and leaks the risk label.",
    "detention_flag": "Detention flags are finalized at semester close; using them as predictors is trivial leakage.",
    "reval_marks": "Revaluation marks occur after initial grade release and represent post-examination information.",
    "revaluation_marks": "Revaluation marks occur after initial grade release and represent post-examination information.",
    "final_grade": "Final letter grade or credit points are post-examination outcomes.",
}

# Criteria thresholds for College ML Training Readiness
MIN_REQUIRED_SAMPLES = 100
MIN_LABELED_SAMPLES = 80
MIN_MINORITY_CLASS_SAMPLES = 15
MAX_ALLOWABLE_ERROR_RATE = 0.05


def validate_college_observation(record: Dict[str, Any]) -> Tuple[Optional[CollegeAcademicObservation], List[str]]:
    """Validate a single dictionary against the CollegeAcademicObservation schema.

    Returns:
        (validated_observation, error_messages)
    """
    try:
        obs = CollegeAcademicObservation(**record)
        return obs, []
    except ValidationError as ve:
        errors = []
        for err in ve.errors():
            loc = ".".join(str(x) for x in err.get("loc", []))
            msg = err.get("msg", "Validation error")
            errors.append(f"{loc}: {msg}" if loc else msg)
        return None, errors
    except Exception as e:
        return None, [str(e)]


def detect_duplicate_observations(
    observations: List[CollegeAcademicObservation],
) -> List[Dict[str, Any]]:
    """Identify duplicate semester observations sharing the same (student_ref, academic_year, semester) key.

    Returns a list of duplicate occurrences with index and key details.
    """
    seen_keys: Dict[Tuple[str, int, int], List[int]] = {}
    for idx, obs in enumerate(observations):
        key = obs.observation_key
        if key not in seen_keys:
            seen_keys[key] = []
        seen_keys[key].append(idx)

    duplicates = []
    for key, indices in seen_keys.items():
        if len(indices) > 1:
            duplicates.append({
                "student_ref": key[0],
                "academic_year": key[1],
                "semester": key[2],
                "occurrences": len(indices),
                "row_indices": indices,
            })
    return duplicates


def detect_target_leakage_risks(field_names: List[str]) -> List[Dict[str, str]]:
    """Inspect input feature column names for future-information or post-examination leakage.

    Returns:
        List of flagged features with leakage explanation and mitigation advice.
    """
    flagged = []
    for field in field_names:
        clean_field = field.strip().lower()
        for pattern, explanation in SUSPICIOUS_LEAKAGE_PATTERNS.items():
            if pattern in clean_field:
                flagged.append({
                    "feature_name": field,
                    "matched_pattern": pattern,
                    "leakage_risk": "HIGH",
                    "explanation": explanation,
                    "mitigation": "Exclude this field from early-warning feature matrix (X).",
                })
                break
    return flagged


def check_class_balance(observations: List[CollegeAcademicObservation]) -> Dict[str, Any]:
    """Calculate class balance and label distribution for records with verified ground-truth."""
    labeled_records = [obs for obs in observations if obs.is_at_risk_label is not None]
    outcome_records = [obs for obs in observations if obs.verified_outcome is not None]

    total_records = len(observations)
    labeled_count = len(labeled_records)

    binary_counts = Counter(obs.is_at_risk_label for obs in labeled_records)
    outcome_counts = Counter(obs.verified_outcome for obs in outcome_records)

    at_risk_count = binary_counts.get(True, 0)
    passing_count = binary_counts.get(False, 0)

    return {
        "total_records": total_records,
        "labeled_records_count": labeled_count,
        "unlabeled_records_count": total_records - labeled_count,
        "labeling_rate": round(labeled_count / total_records, 4) if total_records > 0 else 0.0,
        "binary_risk_distribution": {
            "at_risk_true_count": at_risk_count,
            "at_risk_false_count": passing_count,
            "at_risk_ratio": round(at_risk_count / labeled_count, 4) if labeled_count > 0 else 0.0,
            "passing_ratio": round(passing_count / labeled_count, 4) if labeled_count > 0 else 0.0,
        },
        "verified_outcome_breakdown": dict(outcome_counts),
    }


def analyze_college_dataset(
    raw_records: List[Dict[str, Any]],
    dataset_name: str = "College Academic Observations Batch",
) -> Dict[str, Any]:
    """Execute a comprehensive, privacy-preserving data quality audit and ML readiness assessment.

    Args:
        raw_records: List of dictionary records representing student semester observations.
        dataset_name: Descriptive name for the dataset/audit.

    Returns:
        Structured dictionary containing:
        - Validation errors and success rate
        - Duplicate detection
        - Missing values by field
        - Inconsistent semester records
        - Target leakage risks
        - Class balance
        - ML readiness checklist and decision
    """
    total_records = len(raw_records)
    if total_records == 0:
        return {
            "dataset_name": dataset_name,
            "total_records": 0,
            "is_ready_for_training": False,
            "blocking_reasons": ["Dataset contains 0 records."],
        }

    # 1. Feature names inspection for leakage
    all_keys: Set[str] = set()
    for r in raw_records:
        all_keys.update(r.keys())
    leakage_warnings = detect_target_leakage_risks(list(all_keys))

    # 2. Validation and consistency checking
    valid_observations: List[CollegeAcademicObservation] = []
    validation_failures: List[Dict[str, Any]] = []

    for idx, r in enumerate(raw_records):
        obs, errors = validate_college_observation(r)
        if obs is not None:
            valid_observations.append(obs)
        else:
            validation_failures.append({
                "row_index": idx,
                "errors": errors,
            })

    valid_count = len(valid_observations)
    invalid_count = len(validation_failures)
    error_rate = invalid_count / total_records if total_records > 0 else 0.0

    # 3. Duplicate observations detection
    duplicate_info = detect_duplicate_observations(valid_observations)
    total_duplicate_rows = sum(d["occurrences"] for d in duplicate_info)

    # 4. Missing values by field across raw records
    missing_by_field: Dict[str, int] = {}
    for key in all_keys:
        missing_count = sum(1 for r in raw_records if r.get(key) is None or r.get(key) == "")
        if missing_count > 0:
            missing_by_field[key] = missing_count

    # 5. Class balance analysis
    class_balance_info = check_class_balance(valid_observations)

    # 6. ML Readiness Criteria Evaluation
    blocking_reasons = []

    if valid_count < MIN_REQUIRED_SAMPLES:
        blocking_reasons.append(
            f"Insufficient sample size: {valid_count} valid records found; minimum required is {MIN_REQUIRED_SAMPLES}."
        )

    labeled_count = class_balance_info["labeled_records_count"]
    if labeled_count < MIN_LABELED_SAMPLES:
        blocking_reasons.append(
            f"Insufficient verified ground-truth labels: {labeled_count} labeled records; minimum required is {MIN_LABELED_SAMPLES}."
        )

    minority_count = min(
        class_balance_info["binary_risk_distribution"]["at_risk_true_count"],
        class_balance_info["binary_risk_distribution"]["at_risk_false_count"],
    )
    if labeled_count > 0 and minority_count < MIN_MINORITY_CLASS_SAMPLES:
        blocking_reasons.append(
            f"Severe class scarcity: minority class has only {minority_count} samples; minimum required is {MIN_MINORITY_CLASS_SAMPLES}."
        )

    if len(leakage_warnings) > 0:
        blocking_reasons.append(
            f"Target leakage detected in {len(leakage_warnings)} field(s): {[w['feature_name'] for w in leakage_warnings]}. These must be excluded."
        )

    if len(duplicate_info) > 0:
        blocking_reasons.append(
            f"Dataset contains {len(duplicate_info)} set(s) of duplicate semester observations ({total_duplicate_rows} rows). Must be deduplicated."
        )

    if error_rate > MAX_ALLOWABLE_ERROR_RATE:
        blocking_reasons.append(
            f"High validation failure rate ({error_rate * 100:.1f}% > {MAX_ALLOWABLE_ERROR_RATE * 100:.1f}% allowable limit)."
        )

    is_ready_for_training = len(blocking_reasons) == 0

    return {
        "dataset_name": dataset_name,
        "total_records": total_records,
        "valid_records_count": valid_count,
        "invalid_records_count": invalid_count,
        "validation_error_rate": round(error_rate, 4),
        "validation_failures_sample": validation_failures[:10],  # Capped sample for debugging without PII
        "duplicate_observations_count": len(duplicate_info),
        "duplicate_details": duplicate_info[:10],
        "missing_values_by_field": missing_by_field,
        "target_leakage_warnings": leakage_warnings,
        "class_balance": class_balance_info,
        "ml_readiness": {
            "is_ready_for_training": is_ready_for_training,
            "status": "READY_FOR_COLLEGE_MODEL_TRAINING" if is_ready_for_training else "TRAINING_BLOCKED",
            "blocking_reasons": blocking_reasons,
            "criteria_checklist": {
                f"sample_size_ge_{MIN_REQUIRED_SAMPLES}": valid_count >= MIN_REQUIRED_SAMPLES,
                f"labeled_samples_ge_{MIN_LABELED_SAMPLES}": labeled_count >= MIN_LABELED_SAMPLES,
                f"minority_class_ge_{MIN_MINORITY_CLASS_SAMPLES}": minority_count >= MIN_MINORITY_CLASS_SAMPLES,
                "zero_target_leakage_features": len(leakage_warnings) == 0,
                "zero_duplicate_observations": len(duplicate_info) == 0,
                f"error_rate_le_{int(MAX_ALLOWABLE_ERROR_RATE*100)}pct": error_rate <= MAX_ALLOWABLE_ERROR_RATE,
            },
        },
        "database_storage_action": "NONE_INSPECTED_ONLY",
        "training_action": "NONE_COLLEGE_TRAINING_BLOCKED",
        "privacy_guarantee": "Evaluated pseudonymously in-memory. Zero records persisted to MongoDB.",
    }


MAX_CSV_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
REQUIRED_COLLEGE_CSV_HEADERS = [
    "student_ref",
    "branch",
    "academic_year",
    "semester",
    "attendance_pct",
    "cie_marks_obtained",
]


def parse_college_csv_rows(
    file_bytes_or_str: Union[bytes, str],
    filename: str = "college_dataset.csv",
    max_file_size_bytes: int = MAX_CSV_FILE_SIZE_BYTES,
) -> Tuple[List[Dict[str, Any]], str]:
    """Validate format/size and parse CSV rows into typed dictionaries.

    Safe, memory-only parser shared by Phase 7 audit and Phase 8 analysis pipelines.
    Enforces file size limit, .csv extension, UTF-8/Latin-1 decoding, required headers,
    and type coercion without persisting anything to disk or database.
    """
    # 1. Validate filename extension
    if not filename.lower().endswith(".csv"):
        raise ValueError("Only .csv files are supported for college dataset import.")

    # 2. Extract and validate raw bytes / text length
    if isinstance(file_bytes_or_str, str):
        raw_bytes = file_bytes_or_str.encode("utf-8")
        raw_text = file_bytes_or_str
    elif isinstance(file_bytes_or_str, (bytes, bytearray)):
        raw_bytes = bytes(file_bytes_or_str)
        try:
            raw_text = raw_bytes.decode("utf-8-sig")
        except UnicodeDecodeError:
            try:
                raw_text = raw_bytes.decode("latin-1")
            except Exception:
                raise ValueError("Unable to decode CSV file content with UTF-8 or Latin-1 encoding.")
    else:
        raise ValueError("Invalid file content type. Expected bytes or string.")

    # Check for null bytes or binary corruption
    if b"\x00" in raw_bytes or "\x00" in raw_text:
        raise ValueError("Binary or non-text content detected. Uploaded file must be a valid plain-text CSV.")

    # Strip UTF-8 BOM character if still present in string
    raw_text = raw_text.lstrip("\ufeff")

    if len(raw_bytes) > max_file_size_bytes:
        max_mb = max_file_size_bytes // (1024 * 1024)
        raise ValueError(
            f"File size ({len(raw_bytes)} bytes) exceeds maximum allowable limit of {max_mb} MB."
        )

    if not raw_text.strip():
        raise ValueError("Uploaded CSV file is empty.")

    # 3. Parse CSV rows using DictReader with safe error handling
    try:
        f_stream = io.StringIO(raw_text)
        reader = csv.DictReader(f_stream, strict=True)

        if not reader.fieldnames:
            raise ValueError("CSV file has no header row.")

        # Check for duplicate column headers (case-insensitive detection)
        raw_headers = [col.strip().lstrip("\ufeff") for col in reader.fieldnames if col is not None]
        seen_headers = set()
        duplicate_headers = []
        for col in raw_headers:
            normalized = col.lower()
            if normalized in seen_headers:
                if col not in duplicate_headers:
                    duplicate_headers.append(col)
            else:
                seen_headers.add(normalized)

        if duplicate_headers:
            raise ValueError(
                f"Duplicate column header(s) detected in CSV: {', '.join(duplicate_headers)}. "
                "Column headers must be unique."
            )

        # Check for required headers (case-insensitive mapping with BOM stripped)
        header_map = {col.strip().lstrip("\ufeff").lower(): col for col in reader.fieldnames if col}
        missing_required = [req for req in REQUIRED_COLLEGE_CSV_HEADERS if req.lower() not in header_map]
        if missing_required:
            raise ValueError(
                f"CSV is missing required column(s): {', '.join(missing_required)}. "
                f"Required columns are: {', '.join(REQUIRED_COLLEGE_CSV_HEADERS)}."
            )

        # Convert rows to typed dictionaries
        parsed_records: List[Dict[str, Any]] = []
        int_fields = {"academic_year", "semester", "active_backlogs"}
        float_fields = {
            "attendance_pct",
            "cie_marks_obtained",
            "cie_max_marks",
            "assignment_score_avg",
            "previous_sgpa",
            "cumulative_cgpa",
            "gpa_scale_max",
            "credits_registered",
            "credits_earned_prior",
            "study_hours_per_week",
        }
        bool_fields = {"is_at_risk_label"}

        for row in reader:
            typed_row: Dict[str, Any] = {}
            for raw_k, raw_v in row.items():
                if raw_k is None:
                    continue
                k = raw_k.strip().lstrip("\ufeff").lower()
                val = raw_v.strip() if raw_v is not None else ""

                if val == "":
                    typed_row[k] = None
                    continue

                if k in int_fields:
                    try:
                        typed_row[k] = int(float(val))
                    except ValueError:
                        typed_row[k] = val  # Keep original string so Pydantic records a clean validation error
                    continue
                elif k in float_fields:
                    try:
                        typed_row[k] = float(val)
                    except ValueError:
                        typed_row[k] = val
                    continue
                elif k in bool_fields:
                    low_val = val.lower()
                    if low_val in ("true", "1", "yes", "t", "y"):
                        typed_row[k] = True
                    elif low_val in ("false", "0", "no", "f", "n"):
                        typed_row[k] = False
                    else:
                        typed_row[k] = val
                    continue
                else:
                    typed_row[k] = val

            parsed_records.append(typed_row)

    except csv.Error as ce:
        raise ValueError(f"Malformed CSV content: {str(ce)}")

    return parsed_records, filename


def parse_and_audit_college_csv(
    file_bytes_or_str: Union[bytes, str],
    filename: str = "college_dataset.csv",
    max_file_size_bytes: int = MAX_CSV_FILE_SIZE_BYTES,
) -> Dict[str, Any]:
    """Parse, validate, and audit a CSV file containing de-identified college academic observations (Phase 7)."""
    parsed_records, clean_filename = parse_college_csv_rows(
        file_bytes_or_str=file_bytes_or_str,
        filename=filename,
        max_file_size_bytes=max_file_size_bytes,
    )

    # Run the comprehensive audit
    audit_report = analyze_college_dataset(parsed_records, dataset_name=clean_filename)

    # Attach privacy and database action guarantees
    audit_report["database_storage_action"] = "NONE_INSPECTED_ONLY"
    audit_report["training_action"] = "NONE_COLLEGE_TRAINING_BLOCKED"
    audit_report["privacy_guarantee"] = "Evaluated pseudonymously in-memory. Zero records persisted to MongoDB."

    return audit_report


# =========================================================================
# Phase 8: Extended Dataset Analysis and Model Readiness Pipeline
# =========================================================================

COLLEGE_NUMERIC_FIELDS = [
    "attendance_pct",
    "cie_marks_obtained",
    "cie_max_marks",
    "assignment_score_avg",
    "previous_sgpa",
    "cumulative_cgpa",
    "gpa_scale_max",
    "active_backlogs",
    "credits_registered",
    "credits_earned_prior",
    "study_hours_per_week",
]

DATASET_ANALYSIS_DISCLAIMER = (
    "DATA QUALITY AND READINESS ASSESSMENT DISCLAIMER: This report evaluates structural data quality, "
    "schema integrity, and statistical readiness for prospective machine learning experimentation. "
    "It is NOT an academic risk prediction or evaluation of individual students' performance. "
    "College model training remains blocked pending authorized institutional review and experimental evaluation protocol sign-off."
)


def calculate_numeric_summary_statistics(
    observations: List[CollegeAcademicObservation],
) -> Dict[str, Dict[str, Any]]:
    """Compute summary statistics (count, min, max, mean, median, std) for continuous/integer features."""
    summary: Dict[str, Dict[str, Any]] = {}
    for field in COLLEGE_NUMERIC_FIELDS:
        vals = [
            float(getattr(obs, field))
            for obs in observations
            if getattr(obs, field) is not None
        ]
        if vals:
            count = len(vals)
            min_val = round(min(vals), 2)
            max_val = round(max(vals), 2)
            mean_val = round(sum(vals) / count, 2)
            median_val = round(float(statistics.median(vals)), 2)
            std_val = round(float(statistics.stdev(vals)), 2) if count > 1 else 0.0
            summary[field] = {
                "count": count,
                "min": min_val,
                "max": max_val,
                "mean": mean_val,
                "median": median_val,
                "std": std_val,
            }
        else:
            summary[field] = {
                "count": 0,
                "min": None,
                "max": None,
                "mean": None,
                "median": None,
                "std": None,
            }
    return summary


def analyze_college_dataset_readiness(
    raw_records: List[Dict[str, Any]],
    dataset_name: str = "College Academic Observations Cohort",
) -> Dict[str, Any]:
    """Execute deep data quality analysis, missing-value profiling, and 7-point ML readiness assessment.

    Operates strictly in memory with zero student PII in output reports.
    Returns clear readiness status: 'READY_FOR_REVIEW' or 'TRAINING_BLOCKED'.
    """
    total_records = len(raw_records)
    if total_records == 0:
        return {
            "dataset_name": dataset_name,
            "total_records": 0,
            "valid_records_count": 0,
            "invalid_records_count": 0,
            "validation_error_rate": 0.0,
            "validation_failures_sample": [],
            "student_metrics": {
                "total_valid_observations": 0,
                "unique_pseudonymous_students": 0,
                "observations_per_student_avg": 0.0,
                "pseudonymity_status": "VERIFIED_NO_RAW_PII",
            },
            "duplicate_observations_count": 0,
            "duplicate_details": [],
            "missing_values_summary": {},
            "numeric_summary_statistics": {},
            "categorical_distributions": {
                "branch_distribution": {},
                "academic_year_distribution": {},
                "semester_distribution": {},
                "program_distribution": {},
            },
            "outcome_and_class_balance": {
                "labeled_records_count": 0,
                "unlabeled_records_count": 0,
                "labeling_rate": 0.0,
                "at_risk_count": 0,
                "passing_count": 0,
                "at_risk_ratio": 0.0,
                "passing_ratio": 0.0,
                "imbalance_ratio": "No records",
                "verified_outcome_breakdown": {},
                "outcome_sources": [],
            },
            "target_leakage_warnings": [],
            "readiness_assessment": {
                "status": "TRAINING_BLOCKED",
                "is_ready_for_review": False,
                "is_ready_for_training": False,
                "defensible_split_possible": False,
                "readiness_blockers": ["Dataset contains 0 records."],
                "warnings": [],
                "checks": {
                    "data_quality_and_schema": {
                        "check_name": "Data Quality and Schema Validity",
                        "passed": False,
                        "severity": "BLOCKER",
                        "details": "Dataset contains zero rows.",
                        "metrics": {"total_records": 0},
                    }
                },
                "recommendations": ["Upload a non-empty CSV containing authorized de-identified college academic observations."],
            },
            "disclaimer": DATASET_ANALYSIS_DISCLAIMER,
            "database_storage_action": "NONE_INSPECTED_ONLY",
            "training_action": "NONE_COLLEGE_TRAINING_BLOCKED",
            "privacy_guarantee": "Evaluated pseudonymously in-memory. Zero records persisted to MongoDB. Zero student PII exposed.",
        }

    # 1. Feature names inspection for target leakage
    all_keys: Set[str] = set()
    for r in raw_records:
        all_keys.update(r.keys())
    leakage_warnings = detect_target_leakage_risks(list(all_keys))

    # 2. Validation and consistency checking
    valid_observations: List[CollegeAcademicObservation] = []
    validation_failures: List[Dict[str, Any]] = []

    for idx, r in enumerate(raw_records):
        obs, errors = validate_college_observation(r)
        if obs is not None:
            valid_observations.append(obs)
        else:
            validation_failures.append({
                "row_index": idx,
                "errors": errors,
            })

    valid_count = len(valid_observations)
    invalid_count = len(validation_failures)
    error_rate = round(invalid_count / total_records, 4) if total_records > 0 else 0.0

    # 3. Unique pseudonymous student reference counts
    student_refs = [obs.student_ref for obs in valid_observations]
    unique_students = set(student_refs)
    unique_count = len(unique_students)
    obs_per_student = round(valid_count / unique_count, 2) if unique_count > 0 else 0.0
    student_metrics = {
        "total_valid_observations": valid_count,
        "unique_pseudonymous_students": unique_count,
        "observations_per_student_avg": obs_per_student,
        "pseudonymity_status": "VERIFIED_NO_RAW_PII",
    }

    # 4. Duplicate observations detection
    duplicate_info = detect_duplicate_observations(valid_observations)
    total_duplicate_rows = sum(d["occurrences"] for d in duplicate_info)

    # 5. Missing values per field across raw records
    missing_values_summary: Dict[str, Dict[str, Any]] = {}
    for key in sorted(all_keys):
        missing_count = sum(1 for r in raw_records if r.get(key) is None or r.get(key) == "")
        missing_pct = round((missing_count / total_records) * 100.0, 2)
        present_count = total_records - missing_count
        missing_values_summary[key] = {
            "missing_count": missing_count,
            "missing_pct": missing_pct,
            "present_count": present_count,
        }

    # 6. Numeric field summary statistics
    numeric_summary = calculate_numeric_summary_statistics(valid_observations)

    # 7. Categorical & Cohort distributions
    branch_counts = Counter(obs.branch for obs in valid_observations)
    year_counts = Counter(str(obs.academic_year) for obs in valid_observations)
    sem_counts = Counter(str(obs.semester) for obs in valid_observations)
    prog_counts = Counter(obs.program for obs in valid_observations)

    categorical_distributions = {
        "branch_distribution": dict(branch_counts),
        "academic_year_distribution": dict(year_counts),
        "semester_distribution": dict(sem_counts),
        "program_distribution": dict(prog_counts),
    }

    # 8. Verified academic outcome & class balance analysis
    class_balance_info = check_class_balance(valid_observations)
    labeled_count = class_balance_info["labeled_records_count"]
    unlabeled_count = class_balance_info["unlabeled_records_count"]
    at_risk_count = class_balance_info["binary_risk_distribution"]["at_risk_true_count"]
    passing_count = class_balance_info["binary_risk_distribution"]["at_risk_false_count"]
    at_risk_ratio = class_balance_info["binary_risk_distribution"]["at_risk_ratio"]
    passing_ratio = class_balance_info["binary_risk_distribution"]["passing_ratio"]
    minority_count = min(at_risk_count, passing_count) if labeled_count > 0 else 0

    outcome_sources = sorted(list({obs.outcome_source for obs in valid_observations if obs.outcome_source}))
    imbalance_ratio_str = f"1:{round(passing_count / at_risk_count, 2)}" if at_risk_count > 0 else "No at-risk observations"

    outcome_and_class_balance = {
        "labeled_records_count": labeled_count,
        "unlabeled_records_count": unlabeled_count,
        "labeling_rate": class_balance_info["labeling_rate"],
        "at_risk_count": at_risk_count,
        "passing_count": passing_count,
        "at_risk_ratio": at_risk_ratio,
        "passing_ratio": passing_ratio,
        "imbalance_ratio": imbalance_ratio_str,
        "verified_outcome_breakdown": class_balance_info["verified_outcome_breakdown"],
        "outcome_sources": outcome_sources,
    }

    # 9. Explicit 7-Point ML Readiness Assessment
    checks: Dict[str, Dict[str, Any]] = {}
    readiness_blockers: List[str] = []
    warnings: List[str] = []
    recommendations: List[str] = []

    # Check 1: Data quality and schema validity
    check1_passed = (error_rate <= MAX_ALLOWABLE_ERROR_RATE and valid_count > 0)
    check1_details = (
        f"Validation failure rate is {error_rate * 100:.1f}%, conforming to strict <= {MAX_ALLOWABLE_ERROR_RATE * 100:.1f}% limit."
        if check1_passed
        else f"High validation failure rate ({error_rate * 100:.1f}% > {MAX_ALLOWABLE_ERROR_RATE * 100:.1f}% allowable limit) or zero valid records."
    )
    if not check1_passed:
        readiness_blockers.append(check1_details)
    checks["data_quality_and_schema"] = {
        "check_name": "Data Quality and Schema Validity",
        "passed": check1_passed,
        "severity": "BLOCKER",
        "details": check1_details,
        "metrics": {
            "total_records": total_records,
            "valid_records": valid_count,
            "invalid_records": invalid_count,
            "error_rate": error_rate,
            "max_allowable_error_rate": MAX_ALLOWABLE_ERROR_RATE,
        },
    }

    # Check 2: Duplicate records and missing values
    critical_cols = ["student_ref", "branch", "academic_year", "semester", "attendance_pct", "cie_marks_obtained"]
    critical_missing = {
        col: missing_values_summary.get(col, {}).get("missing_count", 0)
        for col in critical_cols
        if missing_values_summary.get(col, {}).get("missing_count", 0) > 0
    }
    check2_passed = (len(duplicate_info) == 0 and len(critical_missing) == 0)
    check2_details_list = []
    if len(duplicate_info) > 0:
        check2_details_list.append(
            f"{len(duplicate_info)} set(s) of duplicate semester observations found ({total_duplicate_rows} rows)."
        )
    if critical_missing:
        check2_details_list.append(
            f"Missing values detected in mandatory columns: {critical_missing}."
        )
    if check2_passed:
        check2_details = "Zero duplicate student-semester observations and zero missing values in mandatory columns."
    else:
        check2_details = " ".join(check2_details_list)
        readiness_blockers.append(check2_details)
    checks["duplicates_and_missing_values"] = {
        "check_name": "Duplicate Records and Missing Values",
        "passed": check2_passed,
        "severity": "BLOCKER",
        "details": check2_details,
        "metrics": {
            "duplicate_observation_clusters": len(duplicate_info),
            "duplicate_rows_total": total_duplicate_rows,
            "critical_missing_fields": critical_missing,
        },
    }

    # Check 3: Availability of verified ground-truth labels
    unverified_outcomes_count = sum(1 for obs in valid_observations if obs.verified_outcome is not None and not obs.outcome_source)
    check3_passed = (labeled_count >= MIN_LABELED_SAMPLES and unverified_outcomes_count == 0)
    check3_details = (
        f"{labeled_count} verified ground-truth labels available (minimum required: {MIN_LABELED_SAMPLES}) backed by documented examination authority."
        if check3_passed
        else f"Insufficient verified ground-truth labels: {labeled_count} found; minimum required is {MIN_LABELED_SAMPLES}."
    )
    if not check3_passed:
        readiness_blockers.append(check3_details)
    checks["ground_truth_labels_availability"] = {
        "check_name": "Availability of Verified Ground-Truth Labels",
        "passed": check3_passed,
        "severity": "BLOCKER",
        "details": check3_details,
        "metrics": {
            "labeled_records_count": labeled_count,
            "min_required_labeled_samples": MIN_LABELED_SAMPLES,
            "outcome_sources": outcome_sources,
        },
    }

    # Check 4: Number of verified labeled observations and at-risk examples
    check4_passed = (valid_count >= MIN_REQUIRED_SAMPLES and at_risk_count >= MIN_MINORITY_CLASS_SAMPLES)
    check4_details = (
        f"Cohort size is sufficient: {valid_count} valid records (min {MIN_REQUIRED_SAMPLES}) with {at_risk_count} at-risk positive instances (min {MIN_MINORITY_CLASS_SAMPLES})."
        if check4_passed
        else f"Sample size criteria unmet: {valid_count}/{MIN_REQUIRED_SAMPLES} valid records, {at_risk_count}/{MIN_MINORITY_CLASS_SAMPLES} at-risk observations."
    )
    if not check4_passed:
        readiness_blockers.append(check4_details)
    checks["sample_size_and_at_risk_counts"] = {
        "check_name": "Sample Size and At-Risk Example Counts",
        "passed": check4_passed,
        "severity": "BLOCKER",
        "details": check4_details,
        "metrics": {
            "valid_records_count": valid_count,
            "min_required_samples": MIN_REQUIRED_SAMPLES,
            "at_risk_count": at_risk_count,
            "min_at_risk_samples": MIN_MINORITY_CLASS_SAMPLES,
        },
    }

    # Check 5: Class imbalance and whether a defensible evaluation split is possible
    defensible_split_possible = (minority_count >= MIN_MINORITY_CLASS_SAMPLES and labeled_count >= MIN_LABELED_SAMPLES)
    check5_passed = defensible_split_possible
    check5_details = (
        f"Defensible evaluation split is statistically viable: minority class has {minority_count} samples (>= {MIN_MINORITY_CLASS_SAMPLES}), permitting 5-fold stratified cross-validation or holdout evaluation."
        if check5_passed
        else f"Class imbalance prevents defensible evaluation split: minority class has only {minority_count} samples (minimum {MIN_MINORITY_CLASS_SAMPLES} required to prevent degenerate evaluation folds)."
    )
    if not check5_passed:
        readiness_blockers.append(check5_details)
    checks["class_imbalance_and_defensible_split"] = {
        "check_name": "Class Imbalance and Defensible Evaluation Split",
        "passed": check5_passed,
        "severity": "BLOCKER",
        "details": check5_details,
        "metrics": {
            "minority_class_count": minority_count,
            "min_minority_samples": MIN_MINORITY_CLASS_SAMPLES,
            "defensible_split_possible": defensible_split_possible,
        },
    }

    # Check 6: Potential target leakage
    check6_passed = (len(leakage_warnings) == 0)
    check6_details = (
        "Zero post-examination, circular, or future-information target leakage features detected."
        if check6_passed
        else f"Potential target leakage detected in {len(leakage_warnings)} field(s): {[w['feature_name'] for w in leakage_warnings]}. These must be excluded prior to model training."
    )
    if not check6_passed:
        readiness_blockers.append(check6_details)
    checks["potential_target_leakage"] = {
        "check_name": "Potential Target Leakage Inspection",
        "passed": check6_passed,
        "severity": "BLOCKER",
        "details": check6_details,
        "metrics": {
            "leakage_warnings_count": len(leakage_warnings),
            "flagged_features": [w["feature_name"] for w in leakage_warnings],
        },
    }

    # Check 7: Population representation (Engineering College Context)
    branches = list(branch_counts.keys())
    years_valid = all(1 <= int(y) <= 5 for y in year_counts.keys())
    sems_valid = all(1 <= int(s) <= 10 for s in sem_counts.keys())
    check7_passed = (len(branches) > 0 and years_valid and sems_valid)
    check7_details = (
        f"Cohort represents engineering degree students across {len(branches)} department(s) ({', '.join(sorted(branches)[:5])}) and {len(year_counts)} study year(s) on standard 10-point GPA scale."
        if check7_passed
        else "Dataset does not reflect standard engineering degree academic cohort structure."
    )
    if not check7_passed:
        readiness_blockers.append(check7_details)
    checks["population_representation"] = {
        "check_name": "Engineering College Population Representation",
        "passed": check7_passed,
        "severity": "BLOCKER" if len(branches) == 0 else "WARNING",
        "details": check7_details,
        "metrics": {
            "branch_count": len(branches),
            "branches": sorted(branches),
            "study_years": sorted(list(year_counts.keys())),
        },
    }

    # Additional advisory warnings (non-blocking)
    if passing_count > 0 and at_risk_count > 0 and (passing_count / at_risk_count > 5):
        warnings.append(
            f"Moderate to high class skew: passing students outnumber at-risk students {round(passing_count / at_risk_count, 1)}:1. Use class-weighted loss or stratified sampling."
        )

    high_missing_fields = [
        f"{col} ({info['missing_pct']}%)"
        for col, info in missing_values_summary.items()
        if info["missing_pct"] > 40.0 and col not in critical_cols
    ]
    if high_missing_fields:
        warnings.append(
            f"High missingness (>40%) in optional features: {', '.join(high_missing_fields[:4])}. Imputation or exclusion is advisable."
        )

    # Determine overall status
    is_ready_for_review = len(readiness_blockers) == 0
    readiness_status = "READY_FOR_REVIEW" if is_ready_for_review else "TRAINING_BLOCKED"

    # Actionable recommendations
    if is_ready_for_review:
        recommendations = [
            "Submit the readiness report for institutional academic advisory and examination cell sign-off.",
            "Design a leak-free evaluation protocol (e.g., student-stratified 5-fold cross-validation or temporal semester-holdout).",
            "Establish benchmark performance with interpretable linear models (e.g. Logistic Regression) before proceeding to tree-based ensembles.",
            "Do not train or deploy models to production without documented human review and algorithmic impact assessment.",
        ]
    else:
        if len(leakage_warnings) > 0:
            recommendations.append(f"Remove post-examination leakage columns ({', '.join(w['feature_name'] for w in leakage_warnings)}) from feature matrix.")
        if len(duplicate_info) > 0:
            recommendations.append("Deduplicate student-semester records sharing identical (student_ref, academic_year, semester) keys.")
        if valid_count < MIN_REQUIRED_SAMPLES:
            recommendations.append(f"Collect additional validated observations to reach minimum sample threshold of {MIN_REQUIRED_SAMPLES} records.")
        if labeled_count < MIN_LABELED_SAMPLES:
            recommendations.append(f"Obtain official examination ground-truth outcomes to reach minimum {MIN_LABELED_SAMPLES} labeled observations.")
        if minority_count < MIN_MINORITY_CLASS_SAMPLES:
            recommendations.append(f"Acquire at least {MIN_MINORITY_CLASS_SAMPLES} verified at-risk student observations to prevent degenerate evaluation folds.")
        if error_rate > MAX_ALLOWABLE_ERROR_RATE:
            recommendations.append(f"Correct schema/bounds errors to lower validation error rate below {MAX_ALLOWABLE_ERROR_RATE * 100:.1f}%.")

    return {
        "dataset_name": dataset_name,
        "total_records": total_records,
        "valid_records_count": valid_count,
        "invalid_records_count": invalid_count,
        "validation_error_rate": error_rate,
        "validation_failures_sample": validation_failures[:10],
        "student_metrics": student_metrics,
        "duplicate_observations_count": len(duplicate_info),
        "duplicate_details": duplicate_info[:10],
        "missing_values_summary": missing_values_summary,
        "numeric_summary_statistics": numeric_summary,
        "categorical_distributions": categorical_distributions,
        "outcome_and_class_balance": outcome_and_class_balance,
        "target_leakage_warnings": leakage_warnings,
        "readiness_assessment": {
            "status": readiness_status,
            "is_ready_for_review": is_ready_for_review,
            "is_ready_for_training": False,
            "defensible_split_possible": defensible_split_possible,
            "readiness_blockers": readiness_blockers,
            "warnings": warnings,
            "checks": checks,
            "recommendations": recommendations,
        },
        "disclaimer": DATASET_ANALYSIS_DISCLAIMER,
        "database_storage_action": "NONE_INSPECTED_ONLY",
        "training_action": "NONE_COLLEGE_TRAINING_BLOCKED",
        "privacy_guarantee": "Evaluated pseudonymously in-memory. Zero records persisted to MongoDB. Zero student PII exposed.",
    }


def parse_and_analyze_college_csv(
    file_bytes_or_str: Union[bytes, str],
    filename: str = "college_dataset.csv",
    max_file_size_bytes: int = MAX_CSV_FILE_SIZE_BYTES,
) -> Dict[str, Any]:
    """Parse, profile, and perform full ML readiness assessment on uploaded college CSV (Phase 8).

    Reuses the safe CSV row parsing pipeline. Operates strictly in memory without database persistence.
    """
    parsed_records, clean_filename = parse_college_csv_rows(
        file_bytes_or_str=file_bytes_or_str,
        filename=filename,
        max_file_size_bytes=max_file_size_bytes,
    )
    analysis_report = analyze_college_dataset_readiness(parsed_records, dataset_name=clean_filename)
    return analysis_report
