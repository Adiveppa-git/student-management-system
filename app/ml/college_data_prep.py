"""Engineering College Academic Data Preparation and ML Readiness Utilities.

Provides reusable data validation, quality auditing, duplicate detection,
target-leakage inspection, class-balance analysis, and ML readiness evaluation.
Operates independently of database storage and preserves student privacy.
"""

from collections import Counter
from typing import Any, Dict, List, Optional, Set, Tuple
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
    }
