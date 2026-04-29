# app/config.py

import os
from dotenv import load_dotenv

load_dotenv()

try:
    import streamlit as st
    DB_HOST     = st.secrets.get("DB_HOST",     os.getenv("DB_HOST",     "localhost"))
    DB_PORT     = st.secrets.get("DB_PORT",     os.getenv("DB_PORT",     "5432"))
    DB_NAME     = st.secrets.get("DB_NAME",     os.getenv("DB_NAME",     "expense_db"))
    DB_USER     = st.secrets.get("DB_USER",     os.getenv("DB_USER",     "postgres"))
    DB_PASSWORD = st.secrets.get("DB_PASSWORD", os.getenv("DB_PASSWORD", ""))
    APP_ENV     = st.secrets.get("APP_ENV",     os.getenv("APP_ENV",     "development"))
    DEBUG       = str(st.secrets.get("APP_DEBUG", os.getenv("APP_DEBUG", "True"))) == "True"
except Exception:
    DB_HOST     = os.getenv("DB_HOST",     "localhost")
    DB_PORT     = os.getenv("DB_PORT",     "5432")
    DB_NAME     = os.getenv("DB_NAME",     "expense_db")
    DB_USER     = os.getenv("DB_USER",     "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    APP_ENV     = os.getenv("APP_ENV",     "development")
    DEBUG       = os.getenv("APP_DEBUG",   "True") == "True"


class Config:
    DB_HOST     = DB_HOST
    DB_PORT     = DB_PORT
    DB_NAME     = DB_NAME
    DB_USER     = DB_USER
    DB_PASSWORD = DB_PASSWORD

    DATABASE_URL = (
        f"postgresql://{DB_USER}:{DB_PASSWORD}"
        f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )

    APP_ENV = APP_ENV
    DEBUG   = DEBUG

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