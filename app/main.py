from contextlib import asynccontextmanager
import logging
import os
from pathlib import Path
from typing import List, Tuple

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.ml.predictor import load_model_pipeline
from app.routes.ai_routes import router as ai_router
from app.routes.student_routes import router as student_router

# Determine project root and safely load .env if present without overriding existing environment variables
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=ROOT_DIR / ".env", override=False)

logger = logging.getLogger("uvicorn.error")

DEFAULT_CORS_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
]


def get_cors_configuration() -> Tuple[List[str], bool]:
    """Parse and validate CORS origins from the CORS_ORIGINS environment variable.

    Returns:
        Tuple[List[str], bool]: (allowed_origins, allow_credentials)
        - If CORS_ORIGINS is unset or empty, returns default explicit local-development origins
          with credentials enabled.
        - If wildcard '*' is specified, allow_credentials is set to False to comply with
          modern browser security policies prohibiting wildcard origins with credentials.
        - Otherwise returns the parsed, trimmed origin list with credentials enabled.
    """
    raw_origins = os.getenv("CORS_ORIGINS")
    if not raw_origins:
        return list(DEFAULT_CORS_ORIGINS), True

    parsed = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
    if not parsed:
        return list(DEFAULT_CORS_ORIGINS), True

    if "*" in parsed:
        # Combining wildcard origins with credentials is forbidden by browser security specifications.
        return ["*"], False

    return parsed, True


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Preload the trained machine learning pipeline into memory on application startup.

    Replaces silent exception suppression with structured logging while preserving
    fault-tolerant startup if model artifacts are missing or unreadable.
    """
    try:
        load_model_pipeline()
        logger.info("AI benchmark ML pipeline preloaded successfully into memory.")
    except Exception as exc:
        logger.warning(
            "Benchmark ML model pipeline could not be preloaded on startup (%s). "
            "Application startup will proceed; model health endpoint will report service unavailable.",
            type(exc).__name__,
        )
    yield


app = FastAPI(
    title="AI-Powered Student Success and Early Warning System API",
    version="1.0.0",
    description="Student Management and Academic Early Warning System REST API",
    lifespan=lifespan,
)

# CORS configuration with configurable origins and strict credential handling
allowed_origins, allow_credentials = get_cors_configuration()
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=allow_credentials,
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
