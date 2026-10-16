from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.routes.student_routes import router as student_router
from app.routes.ai_routes import router as ai_router
from app.ml.predictor import load_model_pipeline


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Preload the trained machine learning pipeline into memory on application startup."""
    try:
        load_model_pipeline()
    except Exception:
        pass
    yield


app = FastAPI(
    title="AI-Powered Student Success and Early Warning System API",
    version="1.0.0",
    description="Student Management and Academic Early Warning System REST API",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(student_router)
app.include_router(ai_router)

# Mount frontend directory for browser access at /frontend
app.mount("/frontend", StaticFiles(directory="frontend", html=True), name="frontend")



@app.get("/")
def home():
    return {"message": "Student Management System API"}
