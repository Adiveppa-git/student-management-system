"""Predictor interface for Student Academic Risk Early Warning System.

Loads the saved Scikit-learn pipeline, handles input validation and missing value imputation,
and returns structured risk predictions with probabilities and tiered risk levels.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import joblib
import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline

ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"
DEFAULT_MODEL_PATH = ARTIFACTS_DIR / "student_risk_pipeline.joblib"
METADATA_PATH = ARTIFACTS_DIR / "metadata.json"
METRICS_PATH = ARTIFACTS_DIR / "metrics.json"

_CACHED_PIPELINE: Optional[Pipeline] = None
_CACHED_METADATA: Optional[Dict[str, Any]] = None
_CACHED_METRICS: Optional[Dict[str, Any]] = None


def get_metadata() -> Dict[str, Any]:
    """Retrieve the cached or loaded metadata for the ML model."""
    global _CACHED_METADATA
    if _CACHED_METADATA is None:
        if not METADATA_PATH.exists():
            raise FileNotFoundError(
                "Metadata file not found. Run app/ml/train.py first."
            )
        with open(METADATA_PATH, "r", encoding="utf-8") as f:
            _CACHED_METADATA = json.load(f)
    return _CACHED_METADATA


def get_metrics() -> Dict[str, Any]:
    """Retrieve the cached or loaded evaluation metrics for the ML model."""
    global _CACHED_METRICS
    if _CACHED_METRICS is None:
        if not METRICS_PATH.exists():
            raise FileNotFoundError(
                "Metrics file not found. Run app/ml/train.py first."
            )
        with open(METRICS_PATH, "r", encoding="utf-8") as f:
            _CACHED_METRICS = json.load(f)
    return _CACHED_METRICS


def check_model_health() -> Dict[str, Any]:
    """Check health and integrity of the saved ML pipeline and artifacts."""
    try:
        pipeline = load_model_pipeline()
        metadata = get_metadata()
        _ = get_metrics()
        clf = pipeline.named_steps.get("clf")
        clf_name = type(clf).__name__ if clf else "Unknown"
        features_count = len(metadata["experiment"]["input_features"])
        return {
            "status": "healthy",
            "model_loaded": True,
            "model_type": clf_name,
            "features_count": features_count,
            "artifacts_intact": True,
            "message": "Academic risk machine learning pipeline is loaded and operational.",
        }
    except Exception:
        return {
            "status": "unavailable",
            "model_loaded": False,
            "model_type": None,
            "features_count": None,
            "artifacts_intact": False,
            "message": "Model artifacts are missing or unavailable.",
        }



def load_model_pipeline(
    model_path: Optional[Union[str, Path]] = None, reload: bool = False
) -> Pipeline:
    """Load and return the fitted Scikit-learn Pipeline from disk."""
    global _CACHED_PIPELINE
    if _CACHED_PIPELINE is not None and not reload and model_path is None:
        return _CACHED_PIPELINE

    target_path = Path(model_path) if model_path else DEFAULT_MODEL_PATH
    if not target_path.exists():
        raise FileNotFoundError(
            f"Trained model artifact not found at {target_path}. "
            "Please run `python -m app.ml.train` to train and save the pipeline."
        )

    pipeline = joblib.load(target_path)
    if model_path is None:
        _CACHED_PIPELINE = pipeline
    return pipeline


def _determine_risk_level(risk_prob: float) -> str:
    """Determine risk tier based on predicted risk probability."""
    if risk_prob >= 0.65:
        return "High"
    elif risk_prob >= 0.40:
        return "Medium"
    else:
        return "Low"


def predict_student_risk(
    features: Dict[str, Any],
    pipeline: Optional[Pipeline] = None,
) -> Dict[str, Any]:
    """Generate risk prediction and probability for a single student.
    
    Args:
        features: Dictionary containing student attributes (e.g. G1, studytime, failures, absences, etc.).
        pipeline: Optional pre-loaded pipeline. If None, uses cached default.
        
    Returns:
        Dictionary containing:
            - is_at_risk (bool)
            - risk_status ("At-Risk" | "Normal")
            - risk_probability (float, 0.0 to 1.0)
            - confidence (float, 0.0 to 1.0)
            - risk_level ("High" | "Medium" | "Low")
    """
    model = pipeline or load_model_pipeline()
    metadata = get_metadata()
    expected_cols = metadata["experiment"]["input_features"]

    # Construct single-row DataFrame matching training feature columns
    df_row = pd.DataFrame([features])

    # Ensure all expected columns are present (missing will be None/NaN, handled by SimpleImputer)
    for col in expected_cols:
        if col not in df_row.columns:
            df_row[col] = np.nan

    # Order columns exactly as in training
    df_row = df_row[expected_cols]

    # Predict
    pred = int(model.predict(df_row)[0])
    prob_array = model.predict_proba(df_row)[0]
    risk_prob = float(prob_array[1])
    predicted_prob = float(prob_array[pred])

    is_at_risk = pred == 1
    risk_level = _determine_risk_level(risk_prob)

    return {
        "is_at_risk": is_at_risk,
        "risk_status": "At-Risk" if is_at_risk else "Normal",
        "risk_probability": round(risk_prob, 4),
        "confidence": round(predicted_prob, 4),
        "risk_level": risk_level,
        "evaluated_features_count": len(expected_cols),
    }


def batch_predict_student_risk(
    students: List[Dict[str, Any]],
    pipeline: Optional[Pipeline] = None,
) -> List[Dict[str, Any]]:
    """Generate predictions for a batch of student records."""
    model = pipeline or load_model_pipeline()
    return [predict_student_risk(s, pipeline=model) for s in students]
