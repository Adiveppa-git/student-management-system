import re
from typing import List, Optional
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException, Query, status

from app.database.connection import collection
from app.models.student_schemas import StudentCreate, StudentUpdate

router = APIRouter()


def student_helper(student: dict) -> dict:
    """Format MongoDB student document to JSON-compatible dictionary."""
    if not student:
        return {}
    return {
        "id": str(student.get("_id", "")),
        "name": student.get("name", ""),
        "usn": student.get("usn", ""),
        "branch": student.get("branch", ""),
        "year": int(student.get("year", 1)),
        "email": student.get("email", ""),
        # Academic indicators (None if not recorded yet)
        "attendance_pct": student.get("attendance_pct"),
        "internal_marks_avg": student.get("internal_marks_avg"),
        "assignment_score_avg": student.get("assignment_score_avg"),
        "study_hours_per_week": student.get("study_hours_per_week"),
        "previous_gpa": student.get("previous_gpa"),
        "backlog_count": student.get("backlog_count", 0),
    }


def find_student_by_usn(usn: str) -> Optional[dict]:
    """Find a student by USN with case-insensitive normalization."""
    clean_usn = usn.strip()
    return collection.find_one({"usn": clean_usn.upper()}) or collection.find_one({"usn": clean_usn})


@router.post("/students", status_code=status.HTTP_201_CREATED)
def add_student(student: StudentCreate):
    """Add a new student record with schema validation and duplicate USN check."""
    normalized_usn = student.usn.strip().upper()
    existing = find_student_by_usn(normalized_usn)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Student with USN '{normalized_usn}' already exists."
        )

    student_dict = student.model_dump()
    result = collection.insert_one(student_dict)
    return {
        "message": "Student added",
        "id": str(result.inserted_id),
        "usn": normalized_usn
    }


@router.get("/students")
def get_students(
    search: Optional[str] = Query(None, description="Search by student name or USN"),
    branch: Optional[str] = Query(None, description="Filter by branch"),
    year: Optional[int] = Query(None, description="Filter by academic year")
):
    """Retrieve students with optional search and filtering."""
    query = {}
    if branch:
        query["branch"] = branch.strip()
    if year:
        query["year"] = int(year)
    if search:
        search_clean = re.escape(search.strip())
        query["$or"] = [
            {"name": {"$regex": search_clean, "$options": "i"}},
            {"usn": {"$regex": search_clean, "$options": "i"}}
        ]

    cursor = collection.find(query)
    return [student_helper(s) for s in cursor]


@router.get("/students/{usn}")
def get_student(usn: str):
    """Fetch single student record by USN."""
    student = find_student_by_usn(usn)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student with USN '{usn}' not found."
        )
    return student_helper(student)


@router.put("/students/{usn}")
def update_student(usn: str, student_update: StudentUpdate):
    """Update student details by USN with validation."""
    existing = find_student_by_usn(usn)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student with USN '{usn}' not found."
        )

    update_data = student_update.model_dump(exclude_unset=True)

    # Protect immutable or conflicting USN
    if "usn" in update_data:
        new_usn = update_data["usn"].strip().upper()
        if new_usn != existing.get("usn"):
            conflict = find_student_by_usn(new_usn)
            if conflict and str(conflict["_id"]) != str(existing["_id"]):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot change USN: '{new_usn}' is already assigned to another student."
                )
            update_data["usn"] = new_usn
        else:
            del update_data["usn"]

    if update_data:
        collection.update_one({"_id": existing["_id"]}, {"$set": update_data})

    updated_record = collection.find_one({"_id": existing["_id"]})
    return {
        "message": "Updated",
        "student": student_helper(updated_record)
    }


@router.delete("/students/{usn}")
def delete_student_by_usn(usn: str):
    """
    Delete student by USN.
    Fixes the endpoint mismatch where the frontend sent DELETE /students/{usn}.
    """
    clean_usn = usn.strip()
    result = collection.delete_one({"usn": clean_usn.upper()})
    if result.deleted_count == 0:
        result = collection.delete_one({"usn": clean_usn})

    if result.deleted_count == 1:
        return {"message": "Student deleted", "usn": usn}

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Student with USN '{usn}' not found."
    )


@router.delete("/delete-student/{id}")
def delete_student_by_id(id: str):
    """Legacy delete endpoint by MongoDB ObjectId preserved for backward compatibility."""
    try:
        obj_id = ObjectId(id)
    except (InvalidId, Exception):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ID format"
        )

    result = collection.delete_one({"_id": obj_id})
    if result.deleted_count == 1:
        return {"message": "Student deleted", "id": id}

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Student not found"
    )