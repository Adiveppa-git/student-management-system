"""Pydantic schemas for AI Academic Risk Prediction and Model Inspection endpoints.

Enforces strict type and range validation matching the trained UCI benchmark dataset,
and defines explicit response structures including mandatory experimental disclaimers.
"""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class UCIBenchmarkStudentInput(BaseModel):
    """Input features required by the trained UCI Student Performance model.
    
    All 31 features are strictly validated to prevent invalid inferences.
    This schema reflects secondary school education in Portugal (Cortez & Silva, 2008).
    It is NOT compatible with college engineering metrics (CGPA, backlogs, branch, etc.).
    """
    school: Literal["GP", "MS"] = Field(
        ..., description="Student school: 'GP' (Gabriel Pereira) or 'MS' (Mousinho da Silveira)"
    )
    sex: Literal["F", "M"] = Field(
        ..., description="Student sex: 'F' (female) or 'M' (male)"
    )
    age: int = Field(
        ..., ge=12, le=30, description="Age in years (12-30)"
    )
    address: Literal["U", "R"] = Field(
        ..., description="Home address type: 'U' (urban) or 'R' (rural)"
    )
    famsize: Literal["LE3", "GT3"] = Field(
        ..., description="Family size: 'LE3' (<=3) or 'GT3' (>3)"
    )
    Pstatus: Literal["T", "A"] = Field(
        ..., description="Parent's cohabitation status: 'T' (together) or 'A' (apart)"
    )
    Medu: int = Field(
        ..., ge=0, le=4, description="Mother's education: 0-none, 1-primary, 2-5th-9th grade, 3-secondary, 4-higher"
    )
    Fedu: int = Field(
        ..., ge=0, le=4, description="Father's education: 0-none, 1-primary, 2-5th-9th grade, 3-secondary, 4-higher"
    )
    Mjob: Literal["teacher", "health", "services", "at_home", "other"] = Field(
        ..., description="Mother's job category"
    )
    Fjob: Literal["teacher", "health", "services", "at_home", "other"] = Field(
        ..., description="Father's job category"
    )
    reason: Literal["home", "reputation", "course", "other"] = Field(
        ..., description="Reason to choose this school"
    )
    guardian: Literal["mother", "father", "other"] = Field(
        ..., description="Student's legal guardian"
    )
    traveltime: int = Field(
        ..., ge=1, le=4, description="Home to school travel time: 1 (<15 min), 2 (15-30 min), 3 (30-60 min), 4 (>60 min)"
    )
    studytime: int = Field(
        ..., ge=1, le=4, description="Weekly study time: 1 (<2 hours), 2 (2-5 hours), 3 (5-10 hours), 4 (>10 hours)"
    )
    failures: int = Field(
        ..., ge=0, le=4, description="Number of past class failures (0 to 4)"
    )
    schoolsup: Literal["yes", "no"] = Field(
        ..., description="Extra educational support from school"
    )
    famsup: Literal["yes", "no"] = Field(
        ..., description="Family educational support"
    )
    paid: Literal["yes", "no"] = Field(
        ..., description="Extra paid classes within the course subject"
    )
    activities: Literal["yes", "no"] = Field(
        ..., description="Extracurricular activities"
    )
    nursery: Literal["yes", "no"] = Field(
        ..., description="Attended nursery school"
    )
    higher: Literal["yes", "no"] = Field(
        ..., description="Wants to take higher education"
    )
    internet: Literal["yes", "no"] = Field(
        ..., description="Internet access at home"
    )
    romantic: Literal["yes", "no"] = Field(
        ..., description="In a romantic relationship"
    )
    famrel: int = Field(
        ..., ge=1, le=5, description="Quality of family relationships: 1 (very bad) to 5 (excellent)"
    )
    freetime: int = Field(
        ..., ge=1, le=5, description="Free time after school: 1 (very low) to 5 (very high)"
    )
    goout: int = Field(
        ..., ge=1, le=5, description="Going out with friends: 1 (very low) to 5 (very high)"
    )
    Dalc: int = Field(
        ..., ge=1, le=5, description="Workday alcohol consumption: 1 (very low) to 5 (very high)"
    )
    Walc: int = Field(
        ..., ge=1, le=5, description="Weekend alcohol consumption: 1 (very low) to 5 (very high)"
    )
    health: int = Field(
        ..., ge=1, le=5, description="Current health status: 1 (very bad) to 5 (very good)"
    )
    absences: int = Field(
        ..., ge=0, le=93, description="Number of school absences (0 to 93)"
    )
    G1: float = Field(
        ..., ge=0.0, le=20.0, description="First-period evaluation grade (0.0 to 20.0 scale)"
    )


class BenchmarkPredictionResponse(BaseModel):
    """Structured response for benchmark prediction."""
    is_at_risk: bool = Field(..., description="True if student is predicted to fail final grade (G3 < 10)")
    risk_status: Literal["At-Risk", "Normal"] = Field(..., description="High-level categorical risk status")
    risk_probability: float = Field(..., ge=0.0, le=1.0, description="Calibrated probability of academic risk (0.0-1.0)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence of the predicted class")
    risk_level: Literal["High", "Medium", "Low"] = Field(..., description="Risk tier based on predicted risk probability")
    model_name: str = Field(..., description="Name of the fitted machine learning model")
    dataset_source: str = Field(..., description="Benchmark dataset origin")
    disclaimer: str = Field(..., description="Mandatory experimental usage notice")
    domain_applicability_note: str = Field(..., description="Explanation of demographic/institutional domain bounds")
    evaluated_features_count: int = Field(..., description="Number of features evaluated by the pipeline")


class ModelMetricsResponse(BaseModel):
    """Response containing model performance metrics and limitations."""
    model_name: str
    dataset_source: str
    citation: str
    license: str
    target_definition: str
    passing_threshold: int
    grade_scale: str
    test_metrics: Dict[str, Any]
    comparison_metrics: Dict[str, Any]
    evaluation_limitations: List[str]


class ModelHealthResponse(BaseModel):
    """Response indicating the operational readiness of the ML pipeline."""
    status: Literal["healthy", "unavailable"]
    model_loaded: bool
    model_type: Optional[str] = None
    features_count: Optional[int] = None
    artifacts_intact: bool
    message: str
