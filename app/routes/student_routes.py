from fastapi import APIRouter
from app.database.connection import collection
router = APIRouter()

def student_helper(student):
    return {
        "id": str(student["_id"]),
        "name": student["name"],
        "usn": student["usn"],
        "branch": student["branch"],
        "year": student["year"],
        "email": student["email"]
    }

@router.post("/students")
def add_student(student: dict):
    result = collection.insert_one(student)
    return {"message": "Student added", "id": str(result.inserted_id)}

@router.get("/students")
def get_students():
    return [student_helper(s) for s in collection.find()]

@router.get("/students/{usn}")
def get_student(usn: str):
    student = collection.find_one({"usn": usn})
    if student:
        return student_helper(student)
    return {"error": "Not found"}

@router.put("/students/{usn}")
def update_student(usn: str, data: dict):
    collection.update_one({"usn": usn}, {"$set": data})
    return {"message": "Updated"}

from bson import ObjectId

@router.delete("/delete-student/{id}")
def delete_student_by_id(id: str):
    try:
        obj_id = ObjectId(id)
    except:
        return {"error": "Invalid ID"}

    result = collection.delete_one({"_id": obj_id})

    if result.deleted_count == 1:
        return {"message": "Student deleted"}
    else:
        return {"error": "Not found"}