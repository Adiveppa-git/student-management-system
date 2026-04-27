from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware   # 👈 ADD THIS
from app.routes.student_routes import router

app = FastAPI()

# 👇 ADD THIS BLOCK
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.get("/")
def home():
    return {"message": "Student Management System API"}