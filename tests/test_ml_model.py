"""Automated Test Suite for Academic Risk Prediction Machine Learning Pipeline (Phase 3).

Validates:
1. Model and metadata artifact presence and schema.
2. Leakage-free preprocessing and pipeline component integrity.
3. Single and batch inference output format and probability bounds.
4. Sensitivity to high-risk struggling vs low-risk thriving student profiles.
5. Robustness to missing input features (SimpleImputer).
6. Robustness to unseen categorical levels (OneHotEncoder handle_unknown='ignore').
7. Deterministic reproducibility across repeated inferences.
8. Alternative model pipeline loading and prediction verification.
"""

import json
from pathlib import Path
import pytest
from sklearn.pipeline import Pipeline

from app.ml.predictor import (
    batch_predict_student_risk,
    get_metadata,
    load_model_pipeline,
    predict_student_risk,
)

ARTIFACTS_DIR = Path(__file__).resolve().parent.parent / "app" / "ml" / "artifacts"
JOB_MODEL_PATH = ARTIFACTS_DIR / "student_risk_pipeline.joblib"
METADATA_PATH = ARTIFACTS_DIR / "metadata.json"
METRICS_PATH = ARTIFACTS_DIR / "metrics.json"


@pytest.fixture(scope="module")
def pipeline() -> Pipeline:
    """Fixture providing the loaded production model pipeline."""
    return load_model_pipeline(JOB_MODEL_PATH)


@pytest.fixture(scope="module")
def sample_struggling_student() -> dict:
    """Feature dict representing an academically struggling student."""
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
        "studytime": 1,  # <2 hours
        "failures": 3,   # 3 past failures
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
        "G1": 4,         # very low term-1 assessment (4 / 20)
    }


@pytest.fixture(scope="module")
def sample_thriving_student() -> dict:
    """Feature dict representing a high-performing student."""
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
        "studytime": 4,  # >10 hours weekly
        "failures": 0,   # zero failures
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
        "G1": 18,        # exceptional term-1 score (18 / 20)
    }


# =========================================================================
# Artifact and Metadata Integrity Tests
# =========================================================================

def test_artifacts_exist_on_disk():
    """Verify all required ML model and metadata artifacts exist."""
    assert JOB_MODEL_PATH.exists(), f"Model pipeline artifact missing at {JOB_MODEL_PATH}"
    assert METADATA_PATH.exists(), f"Metadata JSON missing at {METADATA_PATH}"
    assert METRICS_PATH.exists(), f"Metrics JSON missing at {METRICS_PATH}"


def test_metadata_contents_and_documentation():
    """Verify metadata contains complete dataset lineage, leakage rules, and schema mismatch doc."""
    metadata = get_metadata()
    assert metadata["name"] == "UCI Student Performance Dataset (Math)"
    assert "https://archive.ics.uci.edu" in metadata["source_url"]
    assert metadata["target_column"] == "at_risk"
    assert metadata["passing_threshold"] == 10
    assert "G3" in metadata["target_leakage_policy"]["excluded_columns"]
    assert "G2" in metadata["target_leakage_policy"]["excluded_columns"]
    assert "feature_mismatch_documentation" in metadata
    assert len(metadata["experiment"]["input_features"]) == 31
    assert metadata["experiment"]["random_seed"] == 42


def test_metrics_contents_and_validity():
    """Verify saved metrics record non-zero, genuine evaluation numbers."""
    with open(METRICS_PATH, "r", encoding="utf-8") as f:
        metrics_data = json.load(f)

    assert "models" in metrics_data
    assert "logistic_regression" in metrics_data["models"]
    assert "random_forest" in metrics_data["models"]

    for model_key in ["logistic_regression", "random_forest"]:
        m = metrics_data["models"][model_key]["metrics"]
        assert 0.0 <= m["accuracy"] <= 1.0
        assert 0.0 <= m["precision"] <= 1.0
        assert 0.0 <= m["recall"] <= 1.0
        assert 0.0 <= m["f1_score"] <= 1.0
        assert 0.0 <= m["roc_auc"] <= 1.0

        cm = m["confusion_matrix"]
        assert cm["true_positives"] > 0
        assert cm["true_negatives"] > 0


# =========================================================================
# Pipeline Component and Loading Tests
# =========================================================================

def test_model_pipeline_loading(pipeline):
    """Verify that load_model_pipeline correctly returns a fitted Scikit-learn Pipeline."""
    assert isinstance(pipeline, Pipeline)
    assert "prep" in pipeline.named_steps
    assert "clf" in pipeline.named_steps
    assert hasattr(pipeline, "predict")
    assert hasattr(pipeline, "predict_proba")


# =========================================================================
# Prediction and Output Format Tests
# =========================================================================

def test_valid_single_prediction_format(pipeline, sample_struggling_student):
    """Verify predict_student_risk returns the expected keys, types, and value bounds."""
    result = predict_student_risk(sample_struggling_student, pipeline=pipeline)

    assert isinstance(result, dict)
    for key in ["is_at_risk", "risk_status", "risk_probability", "confidence", "risk_level", "evaluated_features_count"]:
        assert key in result, f"Missing key '{key}' in prediction response"

    assert isinstance(result["is_at_risk"], bool)
    assert result["risk_status"] in ["At-Risk", "Normal"]
    assert 0.0 <= result["risk_probability"] <= 1.0
    assert 0.0 <= result["confidence"] <= 1.0
    assert result["risk_level"] in ["High", "Medium", "Low"]
    assert result["evaluated_features_count"] == 31


def test_struggling_student_flagged_at_risk(pipeline, sample_struggling_student):
    """Verify that an academically struggling student is flagged as At-Risk."""
    result = predict_student_risk(sample_struggling_student, pipeline=pipeline)
    assert result["is_at_risk"] is True
    assert result["risk_status"] == "At-Risk"
    assert result["risk_probability"] >= 0.50
    assert result["risk_level"] in ["High", "Medium"]


def test_thriving_student_flagged_normal(pipeline, sample_thriving_student):
    """Verify that a high-performing student is classified as Normal / Low-Risk."""
    result = predict_student_risk(sample_thriving_student, pipeline=pipeline)
    assert result["is_at_risk"] is False
    assert result["risk_status"] == "Normal"
    assert result["risk_probability"] < 0.50
    assert result["risk_level"] == "Low"


def test_batch_prediction(pipeline, sample_struggling_student, sample_thriving_student):
    """Verify batch inference handles lists of records correctly."""
    batch = [sample_struggling_student, sample_thriving_student]
    results = batch_predict_student_risk(batch, pipeline=pipeline)

    assert len(results) == 2
    assert results[0]["is_at_risk"] is True
    assert results[1]["is_at_risk"] is False


# =========================================================================
# Robustness & Imputation Tests (Handling Partial or Invalid Inputs)
# =========================================================================

def test_missing_features_handled_by_imputer(pipeline):
    """Verify that an incomplete input missing most columns is imputed without failing."""
    sparse_input = {
        "G1": 8,
        "studytime": 2,
        "failures": 1
        # All other 28 features intentionally omitted
    }
    result = predict_student_risk(sparse_input, pipeline=pipeline)
    assert isinstance(result, dict)
    assert "is_at_risk" in result
    assert 0.0 <= result["risk_probability"] <= 1.0


def test_unseen_categorical_values_handled_gracefully(pipeline, sample_struggling_student):
    """Verify that unknown/unseen categorical values do not throw encoder errors."""
    perturbed = sample_struggling_student.copy()
    perturbed["school"] = "UNKNOWN_HIGH_SCHOOL_XYZ"
    perturbed["Mjob"] = "cybersecurity_analyst"
    perturbed["reason"] = "unprecedented_reason"

    result = predict_student_risk(perturbed, pipeline=pipeline)
    assert isinstance(result, dict)
    assert 0.0 <= result["risk_probability"] <= 1.0


# =========================================================================
# Reproducibility Tests
# =========================================================================

def test_prediction_reproducibility(pipeline, sample_struggling_student):
    """Verify that identical inputs produce bitwise deterministic predictions."""
    first = predict_student_risk(sample_struggling_student, pipeline=pipeline)
    for _ in range(10):
        subsequent = predict_student_risk(sample_struggling_student, pipeline=pipeline)
        assert first["is_at_risk"] == subsequent["is_at_risk"]
        assert first["risk_probability"] == subsequent["risk_probability"]
        assert first["confidence"] == subsequent["confidence"]
        assert first["risk_level"] == subsequent["risk_level"]


# =========================================================================
# Alternative Model Verification
# =========================================================================

def test_alternative_logistic_regression_pipeline_loads():
    """Verify that the alternative saved model (Logistic Regression) is functional."""
    alt_path = ARTIFACTS_DIR / "logistic_regression_pipeline.joblib"
    assert alt_path.exists(), f"Alternative model missing at {alt_path}"
    alt_pipeline = load_model_pipeline(alt_path, reload=True)
    assert isinstance(alt_pipeline, Pipeline)
