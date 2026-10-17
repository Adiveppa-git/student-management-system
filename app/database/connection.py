"""Database connection and MongoDB client configuration.

Manages connection to MongoDB instance with environment-variable-driven
configuration, supporting safe local .env loading with backward-compatible
database name resolution.
"""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pymongo import MongoClient

# Determine project root and safely load .env if present.
# override=False guarantees existing system / container environment variables are preserved.
ROOT_DIR = Path(__file__).resolve().parent.parent.parent


def load_environment(dotenv_path: Optional[Path] = None, override: bool = False) -> bool:
    """Safely load environment variables from .env file if present.

    Preserves existing system and container environment variables by default
    using override=False.
    """
    target = dotenv_path or (ROOT_DIR / ".env")
    return load_dotenv(dotenv_path=target, override=override)


# Load environment variables at module import time
load_environment()


def get_database_name() -> str:
    """Resolve database name with documented precedence:
    1. DATABASE_NAME takes primary precedence if explicitly set and non-empty.
    2. DB_NAME is supported as a backward-compatible fallback.
    3. Defaults to 'student_db' if neither environment variable is set.
    """
    return os.getenv("DATABASE_NAME") or os.getenv("DB_NAME", "student_db")


# Configuration with documented precedence:
# 1. DATABASE_NAME takes primary precedence if explicitly set.
# 2. DB_NAME is supported as a backward-compatible fallback.
# 3. Defaults to "student_db" if neither environment variable is set.
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DATABASE_NAME = get_database_name()
DB_NAME = DATABASE_NAME

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db["students"]
