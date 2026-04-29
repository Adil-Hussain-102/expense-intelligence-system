# app/ingestion/validator.py

import pandas as pd
import numpy as np

REQUIRED_COLUMNS = ["date", "description", "amount"]


class ValidationError(Exception):
    pass


def check_required_columns(df: pd.DataFrame) -> None:
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]

    if missing:
        available = list(df.columns)
        raise ValidationError(
            f"Missing required columns: {missing}\n"
            f"Columns found in your CSV: {available}\n"
            f"Please ensure your CSV has: date, description, amount columns."
        )

    if len(df) == 0:
        raise ValidationError(
            "The CSV file has no data rows. "
            "Please upload a file with at least one transaction."
        )


def parse_dates(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    original_count = len(df)

    df["date"] = pd.to_datetime(
        df["date"],
        errors="coerce",
        dayfirst=True,
    )

    bad_count = df["date"].isna().sum()

    if bad_count > 0:
        print(f"  ⚠ {bad_count} rows dropped — unparseable date values")

    df = df.dropna(subset=["date"])
    df["date"] = df["date"].dt.date

    dropped = original_count - len(df)
    return df, dropped


def clean_amount(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    original_count = len(df)

    # Convert to string
    df["amount"] = df["amount"].astype(str)

    # Strip whitespace
    df["amount"] = df["amount"].str.strip()

    # Handle parentheses as negative
    df["amount"] = df["amount"].str.replace(
        r"^\((.+)\)$",
        r"-\1",
        regex=True
    )

    # Remove currency symbols and spaces but NOT commas yet
    df["amount"] = df["amount"].str.replace(
        r"[Rs\sPKRpkr$£€₹]",
        "",
        regex=True
    )

    # Remove commas separately (thousands separator)
    df["amount"] = df["amount"].str.replace(",", "", regex=False)

    # Convert to numeric
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")

    bad_count = df["amount"].isna().sum()
    if bad_count > 0:
        print(f"  ⚠ {bad_count} rows dropped — invalid amount values")

    df = df.dropna(subset=["amount"])
    df["amount"] = df["amount"].abs()
    df["amount"] = df["amount"].round(2)

    dropped = original_count - len(df)
    return df, dropped


def clean_descriptions(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    original_count = len(df)

    df["description"] = df["description"].replace("", np.nan)
    df = df.dropna(subset=["description"])

    df["description"] = (
        df["description"]
        .astype(str)
        .str.strip()
        .str.lower()
        .str.replace(r"\s+", " ", regex=True)
    )

    df = df[df["description"].str.len() > 0]

    dropped = original_count - len(df)
    if dropped > 0:
        print(f"  ⚠ {dropped} rows dropped — empty description")

    return df, dropped


def validate_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    original_count = len(df)
    total_dropped  = 0

    print(f"  Starting validation: {original_count} rows to process")

    check_required_columns(df)

    df, dropped = parse_dates(df)
    total_dropped += dropped

    df, dropped = clean_amount(df)
    total_dropped += dropped

    df, dropped = clean_descriptions(df)
    total_dropped += dropped

    df = df.reset_index(drop=True)

    clean_count = len(df)
    report = {
        "original_rows": original_count,
        "clean_rows":    clean_count,
        "dropped_rows":  total_dropped,
        "drop_rate":     round((total_dropped / original_count * 100), 1)
                         if original_count > 0 else 0,
    }

    print(f"  Validation complete: {clean_count} clean rows, {total_dropped} dropped")

    return df, report