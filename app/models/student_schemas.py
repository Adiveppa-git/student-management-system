import re
from typing import Optional
from pydantic import BaseModel, Field, field_validator


EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class StudentBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Full name of student")
    usn: str = Field(..., min_length=3, max_length=30, description="University Seat Number")
    branch: str = Field(..., min_length=2, max_length=50, description="Department / Branch")
    year: int = Field(..., ge=1, le=8, description="Academic year (1-8)")
    email: str = Field(..., min_length=5, max_length=120, description="Email address")

    # Optional academic performance indicators for AI Early Warning System
    attendance_pct: Optional[float] = Field(
        None, ge=0.0, le=100.0, description="Attendance percentage (0-100)"
    )
    internal_marks_avg: Optional[float] = Field(
        None, ge=0.0, le=100.0, description="Average continuous internal assessment marks (0-100)"
    )
    assignment_score_avg: Optional[float] = Field(
        None, ge=0.0, le=100.0, description="Average assignment / coursework score (0-100)"
    )
    study_hours_per_week: Optional[float] = Field(
        None, ge=0.0, le=60.0, description="Self-study hours per week"
    )
    previous_gpa: Optional[float] = Field(
        None, ge=0.0, le=10.0, description="Previous cumulative GPA / CGPA (0-10 scale)"
    )
    backlog_count: Optional[int] = Field(
        0, ge=0, le=20, description="Number of uncleared backlogs / subject arrears"
    )

    @field_validator("usn")
    @classmethod
    def validate_and_normalize_usn(cls, v: str) -> str:
        clean = v.strip().upper()
        if len(clean) < 3:
            raise ValueError("USN must be at least 3 characters long")
        return clean

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        clean = v.strip().lower()
        if not EMAIL_REGEX.match(clean):
            raise ValueError("Invalid email format")
        return clean

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Name cannot be empty or whitespace only")
        return clean


class StudentCreate(StudentBase):
    """Schema used when registering / creating a new student record."""
    pass


class StudentUpdate(BaseModel):
    """Schema used when updating an existing student record (all fields optional)."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    usn: Optional[str] = Field(None, min_length=3, max_length=30)
    branch: Optional[str] = Field(None, min_length=2, max_length=50)
    year: Optional[int] = Field(None, ge=1, le=8)
    email: Optional[str] = Field(None, min_length=5, max_length=120)

    # Academic metrics
    attendance_pct: Optional[float] = Field(None, ge=0.0, le=100.0)
    internal_marks_avg: Optional[float] = Field(None, ge=0.0, le=100.0)
    assignment_score_avg: Optional[float] = Field(None, ge=0.0, le=100.0)
    study_hours_per_week: Optional[float] = Field(None, ge=0.0, le=60.0)
    previous_gpa: Optional[float] = Field(None, ge=0.0, le=10.0)
    backlog_count: Optional[int] = Field(None, ge=0, le=20)

    @field_validator("email")
    @classmethod
    def validate_email_optional(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        clean = v.strip().lower()
        if not EMAIL_REGEX.match(clean):
            raise ValueError("Invalid email format")
        return clean

    @field_validator("name")
    @classmethod
    def validate_name_optional(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        clean = v.strip()
        if not clean:
            raise ValueError("Name cannot be empty or whitespace only")
        return clean


class StudentResponse(StudentBase):
    """Schema returned by student API endpoints."""
    id: str
