"""Dataset acquisition and inspection module for Student Academic Risk Prediction.

Source Dataset:
- Name: Student Performance Dataset (Math Course - student-mat.csv)
- Authors: Paulo Cortez and Alice Silva (University of Minho, Portugal, 2008)
- Source URL: https://archive.ics.uci.edu/dataset/320/student+performance
- License: Creative Commons Attribution 4.0 International (CC BY 4.0)
- Target Definition: In Portuguese secondary education, grades range from 0 to 20.
  A score below 10 is the established failing threshold. Academic risk is defined
  as binary: at_risk = 1 (G3 < 10), passing / not at-risk = 0 (G3 >= 10).

Target Leakage Prevention:
- G3 (final grade) is the direct ground truth from which the target is derived.
  It MUST be excluded from feature inputs.
- G2 (second-period grade) is recorded at the end of the second term, right before
  the final exam. It is excluded from inputs to maintain an early-warning horizon.
- G1 (first-period grade) represents the first term assessment marks, functioning
  as the earliest continuous assessment grade available during the academic year.
"""

import io
import os
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pandas as pd
import requests

DATA_DIR = Path(__file__).resolve().parent / "data"
UCI_DATASET_URL = "https://archive.ics.uci.edu/static/public/320/student+performance.zip"
LOCAL_CSV_PATH = DATA_DIR / "student-mat.csv"

# Dataset Documentation and Citation
DATASET_METADATA = {
    "name": "UCI Student Performance Dataset (Math)",
    "source_url": "https://archive.ics.uci.edu/dataset/320/student+performance",
    "citation": "Cortez, P., & Silva, A. (2008). Using data mining to predict secondary school student performance. In Proceedings of 5th Annual Future Business Technology Conference (FUBUTEC 2008), pp. 5-12, Porto, Portugal.",
    "license": "Creative Commons Attribution 4.0 International (CC BY 4.0)",
    "target_column": "at_risk",
    "target_definition": "Binary risk indicator where 1 = at-risk (final grade G3 < 10 on a 0-20 scale) and 0 = passing (G3 >= 10).",
    "passing_threshold": 10,
    "grade_scale": "0 to 20",
    "target_leakage_policy": {
        "excluded_columns": ["G3", "G2"],
        "rationale": "G3 is the source of the target label and must never be in X. G2 is a late-stage term-2 grade, excluded to ensure predictions represent an early-warning signal."
    },
    "feature_mismatch_documentation": {
        "existing_app_schema": [
            "name (identifier)",
            "usn (identifier)",
            "branch (higher-ed engineering department)",
            "year (higher-ed study year 1-8)",
            "email (identifier)",
            "attendance_pct (0-100%)",
            "internal_marks_avg (0-100)",
            "assignment_score_avg (0-100)",
            "study_hours_per_week (0-60)",
            "previous_gpa (0-10 scale)",
            "backlog_count (0-20)"
        ],
        "uci_dataset_schema": [
            "Demographics/Social: school, sex, age, address, famsize, Pstatus, Medu, Fedu, Mjob, Fjob, reason, guardian",
            "Academic/Behavioral: traveltime, studytime (1-4 categorical scale), failures (past failed classes 0-4), schoolsup, famsup, paid, activities, nursery, higher, internet, romantic, famrel, freetime, goout, Dalc, Walc, health, absences (total missed classes 0-93)",
            "Assessment grades: G1 (term 1 score 0-20), G2 (term 2 score 0-20), G3 (final score 0-20)"
        ],
        "domain_gap_analysis": (
            "The UCI benchmark reflects Portuguese secondary school education with detailed familial, "
            "behavioral, and absence count variables, whereas the current application schema captures "
            "college-level engineering metrics (USN, branch, percentage attendance, 10-point GPA scale, backlogs). "
            "Features are NOT silently substituted. The ML pipeline is trained on genuine UCI benchmark data "
            "with full feature traceability."
        )
    }
}


def download_uci_dataset(dest_dir: Optional[Path] = None, timeout: int = 30) -> Path:
    """Download the official UCI Student Performance dataset and extract student-mat.csv."""
    target_dir = dest_dir or DATA_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    csv_file = target_dir / "student-mat.csv"

    if csv_file.exists():
        return csv_file

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) StudentManagementSystem/1.0"}
    response = requests.get(UCI_DATASET_URL, headers=headers, timeout=timeout)
    response.raise_for_status()

    # Outer zip contains student.zip
    with zipfile.ZipFile(io.BytesIO(response.content)) as outer_zip:
        inner_zip_bytes = outer_zip.read("student.zip")
        with zipfile.ZipFile(io.BytesIO(inner_zip_bytes)) as inner_zip:
            csv_content = inner_zip.read("student-mat.csv")
            with open(csv_file, "wb") as f:
                f.write(csv_content)

    return csv_file


def load_raw_dataset(csv_path: Optional[Path] = None) -> pd.DataFrame:
    """Load the raw student performance dataframe from CSV."""
    path = csv_path or LOCAL_CSV_PATH
    if not path.exists():
        path = download_uci_dataset()
    df = pd.read_csv(path, sep=";")
    return df


def inspect_dataset(df: pd.DataFrame) -> Dict:
    """Compute summary inspection statistics for the dataset."""
    total_records = len(df)
    missing_values = df.isnull().sum().to_dict()
    total_missing = sum(missing_values.values())
    duplicate_count = int(df.duplicated().sum())

    # Academic risk target inspection
    at_risk_series = df["G3"] < 10
    at_risk_count = int(at_risk_series.sum())
    passing_count = total_records - at_risk_count
    at_risk_ratio = round(at_risk_count / total_records, 4)

    return {
        "total_records": total_records,
        "total_columns": len(df.columns),
        "total_missing_values": total_missing,
        "duplicate_rows": duplicate_count,
        "class_balance": {
            "at_risk_count": at_risk_count,
            "passing_count": passing_count,
            "at_risk_ratio": at_risk_ratio,
            "passing_ratio": round(passing_count / total_records, 4)
        },
        "target_stats": {
            "min_g3": float(df["G3"].min()),
            "max_g3": float(df["G3"].max()),
            "mean_g3": float(df["G3"].mean()),
            "median_g3": float(df["G3"].median()),
            "std_g3": float(df["G3"].std())
        }
    }


def prepare_features_and_target(
    df: pd.DataFrame, include_g1: bool = True
) -> Tuple[pd.DataFrame, pd.Series, List[str], List[str]]:
    """Separate target from input features and enforce strict target leakage prevention.
    
    Args:
        df: Raw student dataframe containing G1, G2, G3 and background features.
        include_g1: If True, include G1 (term 1 continuous assessment) as an early indicator.
                    If False, exclude G1 for a pure pre-assessment baseline.
                    In both cases, G2 and G3 are strictly excluded.
                    
    Returns:
        (X, y, numeric_features, categorical_features)
    """
    # Define binary academic risk target
    y = (df["G3"] < 10).astype(int)

    # Prevent target leakage: exclude final grade G3 and intermediate 2nd term grade G2
    drop_columns = ["G3", "G2"]
    if not include_g1:
        drop_columns.append("G1")

    X = df.drop(columns=drop_columns).copy()

    categorical_features = X.select_dtypes(include=["object"]).columns.tolist()
    numeric_features = X.select_dtypes(include=["int64", "float64"]).columns.tolist()

    return X, y, numeric_features, categorical_features
