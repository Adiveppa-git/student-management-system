"""Model Training and Evaluation Pipeline for Student Academic Risk Prediction.

Implements Scikit-learn pipelines comparing Logistic Regression and Random Forest
with stratified splitting, leak-free preprocessing, class imbalance handling,
comprehensive metrics calculation, model persistence via joblib, and metadata tracking.
"""

import json
from pathlib import Path
from typing import Any, Dict, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from app.ml.dataset import (
    DATASET_METADATA,
    inspect_dataset,
    load_raw_dataset,
    prepare_features_and_target,
)

ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"
RANDOM_SEED = 42
TEST_SIZE = 0.20


def build_preprocessor(
    numeric_features: list[str], categorical_features: list[str]
) -> ColumnTransformer:
    """Build a leak-free ColumnTransformer for numeric and categorical features."""
    numeric_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )

    categorical_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            (
                "encoder",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
            ),
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, numeric_features),
            ("cat", categorical_transformer, categorical_features),
        ]
    )
    return preprocessor


def evaluate_pipeline(
    pipeline: Pipeline, X_test: pd.DataFrame, y_test: pd.Series
) -> Dict[str, Any]:
    """Calculate actual test-set evaluation metrics for a fitted model pipeline."""
    y_pred = pipeline.predict(X_test)
    y_prob = pipeline.predict_proba(X_test)[:, 1]

    cm = confusion_matrix(y_test, y_pred).tolist()
    tn, fp, fn, tp = int(cm[0][0]), int(cm[0][1]), int(cm[1][0]), int(cm[1][1])

    acc = float(accuracy_score(y_test, y_pred))
    prec = float(precision_score(y_test, y_pred, zero_division=0))
    rec = float(recall_score(y_test, y_pred, zero_division=0))
    f1 = float(f1_score(y_test, y_pred, zero_division=0))
    auc = float(roc_auc_score(y_test, y_prob))
    report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)

    return {
        "accuracy": round(acc, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1_score": round(f1, 4),
        "roc_auc": round(auc, 4),
        "confusion_matrix": {
            "matrix": cm,
            "true_negatives": tn,
            "false_positives": fp,
            "false_negatives": fn,
            "true_positives": tp,
            "description": f"TN={tn} (Passing classified as Passing), FP={fp} (Passing falsely flagged as At-Risk), FN={fn} (At-Risk students missed!), TP={tp} (At-Risk students successfully flagged)"
        },
        "classification_report": report,
    }


def train_and_compare_models(
    include_g1: bool = True, save_artifacts: bool = True
) -> Tuple[Dict[str, Any], Pipeline, Pipeline]:
    """Train, evaluate, and compare Logistic Regression vs Random Forest on the UCI dataset.
    
    Args:
        include_g1: True to include early term 1 assessment score (Early Warning model),
                    False for pure pre-enrollment indicators (Baseline model).
        save_artifacts: Whether to persist fitted pipelines and JSON metadata to disk.
        
    Returns:
        (results_summary, logistic_regression_pipeline, random_forest_pipeline)
    """
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Load and inspect dataset
    df = load_raw_dataset()
    inspection = inspect_dataset(df)

    # 2. Separate features and target while enforcing leakage prevention
    X, y, num_cols, cat_cols = prepare_features_and_target(df, include_g1=include_g1)

    # 3. Stratified split into training (80%) and test (20%) sets
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=TEST_SIZE,
        random_state=RANDOM_SEED,
        stratify=y,
    )

    # 4. Construct pipelines with class-weight='balanced' to handle imbalance
    preprocessor = build_preprocessor(num_cols, cat_cols)

    lr_pipeline = Pipeline(
        steps=[
            ("prep", preprocessor),
            (
                "clf",
                LogisticRegression(
                    random_state=RANDOM_SEED,
                    class_weight="balanced",
                    max_iter=1000,
                    C=1.0,
                ),
            ),
        ]
    )

    rf_pipeline = Pipeline(
        steps=[
            ("prep", preprocessor),
            (
                "clf",
                RandomForestClassifier(
                    random_state=RANDOM_SEED,
                    class_weight="balanced",
                    n_estimators=100,
                    min_samples_leaf=2,
                ),
            ),
        ]
    )

    # 5. Fit pipelines on training split only
    lr_pipeline.fit(X_train, y_train)
    rf_pipeline.fit(X_train, y_train)

    # 6. Evaluate actual test-set metrics
    lr_metrics = evaluate_pipeline(lr_pipeline, X_test, y_test)
    rf_metrics = evaluate_pipeline(rf_pipeline, X_test, y_test)

    # 7. Model comparison and recommendation rationale
    # In an academic early warning system, missing an at-risk student (False Negative)
    # carries a high penalty: failure or dropout without intervention.
    # Therefore, Recall on class 1 is the primary clinical metric, complemented by F1-score.
    if lr_metrics["recall"] > rf_metrics["recall"]:
        recommended_model = "Logistic Regression"
        preferred_rationale = (
            f"Logistic Regression achieved substantially higher Recall ({lr_metrics['recall']} vs {rf_metrics['recall']}), "
            f"identifying {lr_metrics['confusion_matrix']['true_positives']} out of {lr_metrics['confusion_matrix']['true_positives'] + lr_metrics['confusion_matrix']['false_negatives']} "
            f"at-risk students (only {lr_metrics['confusion_matrix']['false_negatives']} false negatives vs {rf_metrics['confusion_matrix']['false_negatives']} missed by Random Forest). "
            f"In an Early Warning System, false negatives result in unassisted student failure, making high recall paramount."
        )
        winning_pipeline = lr_pipeline
    else:
        recommended_model = "Random Forest"
        preferred_rationale = (
            f"Random Forest achieved higher Recall ({rf_metrics['recall']} vs {lr_metrics['recall']}) "
            f"and F1-score ({rf_metrics['f1_score']} vs {lr_metrics['f1_score']})."
        )
        winning_pipeline = rf_pipeline

    results = {
        "dataset_inspection": inspection,
        "experiment_config": {
            "include_g1": include_g1,
            "target_leakage_prevention": "G3 and G2 strictly excluded from feature inputs",
            "test_size": TEST_SIZE,
            "random_seed": RANDOM_SEED,
            "train_samples": len(X_train),
            "test_samples": len(X_test),
            "feature_counts": {
                "total_features": len(X.columns),
                "numeric_features": len(num_cols),
                "categorical_features": len(cat_cols),
            },
        },
        "models": {
            "logistic_regression": {
                "algorithm": "LogisticRegression(class_weight='balanced', max_iter=1000, C=1.0)",
                "metrics": lr_metrics,
            },
            "random_forest": {
                "algorithm": "RandomForestClassifier(class_weight='balanced', n_estimators=100, min_samples_leaf=2)",
                "metrics": rf_metrics,
            },
        },
        "model_selection": {
            "recommended_model": recommended_model,
            "rationale": preferred_rationale,
            "primary_decision_metric": "Recall (at-risk class 1) & F1-score",
        },
    }

    # 8. Persistence
    if save_artifacts:
        # Save winning pipeline
        winning_model_path = ARTIFACTS_DIR / "student_risk_pipeline.joblib"
        joblib.dump(winning_pipeline, winning_model_path)

        # Also save alternative pipeline for transparency and comparative audits
        alt_name = (
            "random_forest_pipeline.joblib"
            if recommended_model == "Logistic Regression"
            else "logistic_regression_pipeline.joblib"
        )
        alt_pipeline = (
            rf_pipeline
            if recommended_model == "Logistic Regression"
            else lr_pipeline
        )
        joblib.dump(alt_pipeline, ARTIFACTS_DIR / alt_name)

        # Save metrics separately
        metrics_file = ARTIFACTS_DIR / "metrics.json"
        with open(metrics_file, "w") as f:
            json.dump(results, f, indent=2)

        # Save comprehensive feature and experiment metadata
        metadata = {
            **DATASET_METADATA,
            "experiment": {
                "random_seed": RANDOM_SEED,
                "test_size": TEST_SIZE,
                "stratified_split": True,
                "include_g1": include_g1,
                "input_features": X.columns.tolist(),
                "numeric_features": num_cols,
                "categorical_features": cat_cols,
                "best_model": recommended_model,
                "winning_model_artifact": "student_risk_pipeline.joblib",
            },
            "evaluation_methodology": (
                "Stratified 80/20 train/test split with fixed random seed (42). "
                "Feature preprocessing fitted strictly on training fold via Scikit-learn ColumnTransformer. "
                "Both models fitted with class_weight='balanced' to address ~2:1 class imbalance. "
                "Final evaluation computed on holdout test set using Accuracy, Precision, Recall, F1, and Confusion Matrix."
            ),
        }
        metadata_file = ARTIFACTS_DIR / "metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)

    return results, lr_pipeline, rf_pipeline


if __name__ == "__main__":
    print("=" * 70)
    print("AI Student Success & Early Warning System - ML Model Training (Phase 3)")
    print("=" * 70)

    # 1. Evaluate baseline without G1 (Pre-assessment)
    print("\n[1/2] Evaluating Baseline Setup (Pre-assessment: Excluding G1, G2, G3)...")
    baseline_results, _, _ = train_and_compare_models(include_g1=False, save_artifacts=False)
    lr_base = baseline_results["models"]["logistic_regression"]["metrics"]
    rf_base = baseline_results["models"]["random_forest"]["metrics"]
    print(f"  Logistic Regression -> Acc: {lr_base['accuracy']}, Rec: {lr_base['recall']}, Prec: {lr_base['precision']}, F1: {lr_base['f1_score']}")
    print(f"  Random Forest       -> Acc: {rf_base['accuracy']}, Rec: {rf_base['recall']}, Prec: {rf_base['precision']}, F1: {rf_base['f1_score']}")

    # 2. Evaluate and persist Early-Warning Setup with G1 (Excluding G2, G3)
    print("\n[2/2] Evaluating Early-Warning Setup (Term-1 Grade G1 included, G2 and G3 excluded)...")
    ew_results, _, _ = train_and_compare_models(include_g1=True, save_artifacts=True)
    lr_ew = ew_results["models"]["logistic_regression"]["metrics"]
    rf_ew = ew_results["models"]["random_forest"]["metrics"]
    print(f"  Logistic Regression -> Acc: {lr_ew['accuracy']}, Rec: {lr_ew['recall']}, Prec: {lr_ew['precision']}, F1: {lr_ew['f1_score']}")
    print(f"  Random Forest       -> Acc: {rf_ew['accuracy']}, Rec: {rf_ew['recall']}, Prec: {rf_ew['precision']}, F1: {rf_ew['f1_score']}")

    print("\nRecommended Model:", ew_results["model_selection"]["recommended_model"])
    print("Rationale:", ew_results["model_selection"]["rationale"])
    print("\nArtifacts saved successfully to:", ARTIFACTS_DIR)
