"""Engineering College Academic Observation Schemas for Future ML Readiness.

Defines Pydantic schemas for college-level engineering academic records (AICTE / VTU model).
Explicitly documents grading scales (10-point CGPA), mark maxima (CIE out of explicit max marks),
attendance thresholds, and semester consistency rules without silent assumptions.
"""

from typing import Any, Dict, List, Literal, Optional, Tuple
from pydantic import BaseModel, Field, field_validator, model_validator


class CollegeAcademicObservation(BaseModel):
    """Represents a single student's academic observation for a given semester in an engineering program.
    
    Adheres to the Indian engineering education framework (AICTE / VTU / autonomous colleges):
    - Uses pseudonymous student identifiers to protect student privacy.
    - Explicitly records Continuous Internal Evaluation (CIE) obtained and maximum marks.
    - Explicitly records 10-point grading scale for SGPA and CGPA.
    - Verified outcome labels are strictly optional and must be backed by an audit source.
    """

    # Pseudonymous identifier (hashed USN, institutional token, or masked student ID)
    student_ref: str = Field(
        ...,
        min_length=3,
        max_length=64,
        description="Pseudonymous or institutional student identifier (no raw PII)",
        examples=["STU_HASH_1001", "ANON_ISE_2024_045"],
    )

    # Academic program context
    program: str = Field(
        default="B.Tech",
        min_length=2,
        max_length=50,
        description="Degree program (e.g. B.E., B.Tech, M.Tech)",
    )
    branch: str = Field(
        ...,
        min_length=2,
        max_length=50,
        description="Department / Engineering Branch (e.g. CSE, ISE, ECE, MECH, AIML)",
    )
    academic_year: int = Field(
        ...,
        ge=1,
        le=5,
        description="Academic year of study (1 to 4 for standard B.E./B.Tech, up to 5 for dual degree)",
    )
    semester: int = Field(
        ...,
        ge=1,
        le=10,
        description="Current semester number (1 to 8 for B.E./B.Tech)",
    )

    # Continuous Academic Metrics
    attendance_pct: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Semester cumulative attendance percentage (0.0 to 100.0). In Indian universities, < 75% is the condonation threshold.",
    )
    cie_marks_obtained: float = Field(
        ...,
        ge=0.0,
        description="Continuous Internal Evaluation (CIE) marks obtained up to prediction checkpoint.",
    )
    cie_max_marks: float = Field(
        default=50.0,
        gt=0.0,
        description="Maximum possible marks for Continuous Internal Evaluation (explicitly documented, e.g. 50.0 or 100.0).",
    )
    assignment_score_avg: Optional[float] = Field(
        None,
        ge=0.0,
        le=100.0,
        description="Average assignment / coursework percentage (0.0 to 100.0 scale).",
    )

    # Historical Academic Track Record (10-Point GPA Scale)
    previous_sgpa: Optional[float] = Field(
        None,
        ge=0.0,
        le=10.0,
        description="Semester Grade Point Average of preceding semester (0.0 to 10.0 scale; None for Semester 1).",
    )
    cumulative_cgpa: Optional[float] = Field(
        None,
        ge=0.0,
        le=10.0,
        description="Cumulative Grade Point Average prior to current semester (0.0 to 10.0 scale; None for Semester 1).",
    )
    gpa_scale_max: float = Field(
        default=10.0,
        gt=0.0,
        description="Maximum GPA scale (10.0 standard in Indian engineering colleges under AICTE).",
    )

    # Arrears and Credit Metrics
    active_backlogs: int = Field(
        default=0,
        ge=0,
        le=30,
        description="Number of uncleared backlogs / course arrears prior to the current semester.",
    )
    credits_registered: Optional[float] = Field(
        default=20.0,
        ge=1.0,
        le=40.0,
        description="Total academic credits enrolled in the current semester.",
    )
    credits_earned_prior: Optional[float] = Field(
        None,
        ge=0.0,
        le=250.0,
        description="Total cumulative credits earned in prior semesters.",
    )

    # Behavioral Study Metrics
    study_hours_per_week: Optional[float] = Field(
        None,
        ge=0.0,
        le=80.0,
        description="Estimated self-study hours per week outside classroom instruction.",
    )

    # Verified Ground-Truth Outcome (Strictly optional, only populated for post-hoc verified training data)
    verified_outcome: Optional[Literal["PASS", "FAIL_OR_DETAINED", "ACADEMIC_PROBATION", "WITHDRAWN"]] = Field(
        None,
        description="Verified end-of-semester ground-truth outcome from official examination cell.",
    )
    is_at_risk_label: Optional[bool] = Field(
        None,
        description="Ground-truth binary academic risk label (True if failed/detained/probation; False if passed cleanly).",
    )
    outcome_source: Optional[str] = Field(
        None,
        description="Institutional source verifying the ground-truth label (e.g. 'OFFICIAL_CONTROLLER_OF_EXAMINATIONS').",
    )

    @property
    def observation_key(self) -> Tuple[str, int, int]:
        """Composite key uniquely identifying an observation for duplicate detection."""
        return (self.student_ref.strip().upper(), self.academic_year, self.semester)

    @property
    def normalized_cie_pct(self) -> float:
        """Normalized Continuous Internal Evaluation percentage."""
        return (self.cie_marks_obtained / self.cie_max_marks) * 100.0

    @field_validator("student_ref")
    @classmethod
    def normalize_student_ref(cls, v: str) -> str:
        clean = v.strip().upper()
        if len(clean) < 3:
            raise ValueError("Student reference must be at least 3 characters long")
        return clean

    @field_validator("branch")
    @classmethod
    def normalize_branch(cls, v: str) -> str:
        clean = v.strip().upper()
        if not clean:
            raise ValueError("Branch cannot be empty")
        return clean

    @model_validator(mode="after")
    def validate_domain_consistency(self) -> "CollegeAcademicObservation":
        """Enforce domain-specific consistency checks across engineering academic variables."""
        # 1. CIE marks obtained cannot exceed CIE max marks
        if self.cie_marks_obtained > self.cie_max_marks:
            raise ValueError(
                f"CIE marks obtained ({self.cie_marks_obtained}) cannot exceed maximum CIE marks ({self.cie_max_marks})"
            )

        # 2. Semester vs Academic Year consistency (assuming 2 semesters per academic year)
        expected_min_sem = (self.academic_year - 1) * 2 + 1
        expected_max_sem = self.academic_year * 2
        if not (expected_min_sem <= self.semester <= expected_max_sem):
            raise ValueError(
                f"Inconsistent semester ({self.semester}) for academic year {self.academic_year}. "
                f"Expected semester {expected_min_sem} or {expected_max_sem}."
            )

        # 3. First semester students cannot have a prior college SGPA or CGPA
        if self.semester == 1:
            if self.previous_sgpa is not None and self.previous_sgpa > 0.0:
                raise ValueError("First semester students cannot have a prior college SGPA")
            if self.cumulative_cgpa is not None and self.cumulative_cgpa > 0.0:
                raise ValueError("First semester students cannot have a prior college CGPA")
            if self.active_backlogs > 0:
                raise ValueError("First semester students cannot have prior college backlogs")

        # 4. Verified outcome auditability
        if self.verified_outcome is not None and self.outcome_source is None:
            raise ValueError(
                "When verified_outcome is provided, outcome_source must be documented to prevent unverified labels"
            )

        return self


class CollegeDatasetAuditResponse(BaseModel):
    """Structured response for college academic dataset audit and ML readiness assessment."""
    dataset_name: str = Field(..., description="Name or identifier of the audited dataset/file")
    total_records: int = Field(..., description="Total rows parsed from the dataset")
    valid_records_count: int = Field(..., description="Count of records conforming strictly to the schema")
    invalid_records_count: int = Field(..., description="Count of records with schema or domain validation failures")
    validation_error_rate: float = Field(..., description="Ratio of invalid records to total records (0.0 to 1.0)")
    validation_failures_sample: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Sample of validation failure details (row numbers and error messages, without student PII)",
    )
    duplicate_observations_count: int = Field(
        ..., description="Count of duplicate student-semester observation clusters"
    )
    duplicate_details: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Details of duplicate student-semester occurrences",
    )
    missing_values_by_field: Dict[str, int] = Field(
        default_factory=dict,
        description="Count of missing/null values identified per field",
    )
    target_leakage_warnings: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Features flagged as potential future-information or post-exam target leakage",
    )
    class_balance: Dict[str, Any] = Field(
        ..., description="Label distribution, class counts, and ratios for verified ground truth"
    )
    ml_readiness: Dict[str, Any] = Field(
        ..., description="ML training readiness decision, status, blocking reasons, and criteria checklist"
    )
    database_storage_action: str = Field(
        default="NONE_INSPECTED_ONLY",
        description="Confirmation of non-persistence (records are never inserted into MongoDB)",
    )
    training_action: str = Field(
        default="NONE_COLLEGE_TRAINING_BLOCKED",
        description="Confirmation that model training remains disabled until verified real data is provided",
    )
    privacy_guarantee: str = Field(
        default="Evaluated pseudonymously in-memory. Zero records persisted to MongoDB.",
        description="Guarantee of student privacy and data protection",
    )

