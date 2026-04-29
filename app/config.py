# app/config.py

import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """
    Central configuration class.
    All settings come from environment variables — never hardcoded.
    """

    DB_HOST     = os.getenv("DB_HOST", "localhost")
    DB_PORT     = os.getenv("DB_PORT", "5432")
    DB_NAME     = os.getenv("DB_NAME", "expense_db")
    DB_USER     = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")

    DATABASE_URL = (
        f"postgresql://{DB_USER}:{DB_PASSWORD}"
        f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )

    APP_ENV   = os.getenv("APP_ENV", "development")
    DEBUG     = os.getenv("APP_DEBUG", "True") == "True"

    MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "models")

    CATEGORIES = [
        "Food & Dining",
        "Transport",
        "Utilities",
        "Rent & Housing",
        "Shopping",
        "Healthcare",
        "Entertainment",
        "Education",
        "Salary & Income",
        "Transfer",
        "Other",
    ]