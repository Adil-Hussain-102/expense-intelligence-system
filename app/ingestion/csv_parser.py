# app/ingestion/csv_parser.py

import pandas as pd
from app.ingestion.validator import validate_dataframe, ValidationError
from app.database.db import get_session
from app.database.models import Transaction, Category

COLUMN_MAP = {
    "transaction date": "date",
    "trans date":       "date",
    "txn date":         "date",
    "value date":       "date",
    "posting date":     "date",
    "dt":               "date",
    "transaction description": "description",
    "narration":               "description",
    "particulars":             "description",
    "remarks":                 "description",
    "details":                 "description",
    "memo":                    "description",
    "debit amount":       "amount",
    "credit amount":      "amount",
    "transaction amount": "amount",
    "txn amount":         "amount",
    "withdrawl":          "amount",
    "withdrawal":         "amount",
}


def normalise_column_names(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [col.strip().lower() for col in df.columns]
    df = df.rename(columns=COLUMN_MAP)
    return df


def remove_duplicates(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    original_count = len(df)

    df = df.drop_duplicates(
        subset=["date", "amount", "description"],
        keep="first"
    )

    removed = original_count - len(df)

    if removed > 0:
        print(f"  ⚠ {removed} duplicate rows removed")

    return df, removed


def select_final_columns(df: pd.DataFrame) -> pd.DataFrame:
    keep      = ["date", "description", "amount", "raw_text"]
    available = [col for col in keep if col in df.columns]
    return df[available]


def save_to_database(records: list[dict], session=None) -> dict:
    close_session = False
    if session is None:
        session = get_session()
        close_session = True

    inserted = 0
    skipped  = 0

    try:
        for record in records:
            existing = session.query(Transaction).filter_by(
                date=record["date"],
                amount=record["amount"],
                description=record["description"],
            ).first()

            if existing:
                skipped += 1
                continue

            txn = Transaction(
                date=record["date"],
                description=record["description"],
                amount=record["amount"],
                raw_text=record.get("raw_text", record["description"]),
                category_id=None,
                is_anomaly=False,
                confidence=None,
            )
            session.add(txn)
            inserted += 1

        session.commit()

    except Exception as e:
        session.rollback()
        raise e
    finally:
        if close_session:
            session.close()

    return {"inserted": inserted, "skipped": skipped}


def ingest_csv(filepath: str, save_to_db: bool = True) -> dict:
    print(f"\n{'='*50}")
    print(f"  Ingesting: {filepath}")
    print(f"{'='*50}")

    # Step 1: Read the CSV
    try:
        df = pd.read_csv(
            filepath,
            encoding="utf-8-sig",
            on_bad_lines="skip",
        )
        print(f"\n[1/5] File read: {len(df)} rows found")
    except FileNotFoundError:
        raise FileNotFoundError(f"CSV file not found: {filepath}")
    except Exception as e:
        raise ValidationError(f"Could not read CSV file: {e}")

    # Keep raw description before cleaning
    if "description" in [col.strip().lower() for col in df.columns]:
        df_temp = df.copy()
        df_temp.columns = [col.strip().lower() for col in df_temp.columns]
        df["_raw_description"] = df_temp.get(
            "description",
            df_temp.get("narration",
            df_temp.get("particulars", ""))
        )

    # Step 2: Normalise column names
    print(f"\n[2/5] Normalising column names...")
    df = normalise_column_names(df)
    print(f"  Columns after normalisation: {list(df.columns)}")

    if "_raw_description" in df.columns:
        df["raw_text"] = df["_raw_description"]
        df = df.drop(columns=["_raw_description"])

    # Step 3: Validate and clean
    print(f"\n[3/5] Validating and cleaning data...")
    df, validation_report = validate_dataframe(df)

    # Step 4: Remove duplicates
    print(f"\n[4/5] Removing duplicates...")
    df, duplicates_removed = remove_duplicates(df)

    # Step 5: Select final columns
    df = select_final_columns(df)
    records = df.to_dict("records")

    # Step 6: Save to database
    db_result = {"inserted": 0, "skipped": 0}
    if save_to_db and len(records) > 0:
        print(f"\n[5/5] Saving {len(records)} records to database...")
        db_result = save_to_database(records)
        print(f"  ✓ Inserted: {db_result['inserted']}, Skipped (already exist): {db_result['skipped']}")

    summary = {
        "records":            records,
        "total_read":         validation_report["original_rows"],
        "total_clean":        len(records),
        "total_dropped":      validation_report["dropped_rows"],
        "drop_rate":          validation_report["drop_rate"],
        "duplicates_removed": duplicates_removed,
        "db_inserted":        db_result["inserted"],
        "db_skipped":         db_result["skipped"],
        "validation_report":  validation_report,
    }

    print(f"\n{'='*50}")
    print(f"  INGESTION COMPLETE")
    print(f"  Original rows:   {summary['total_read']}")
    print(f"  Clean rows:      {summary['total_clean']}")
    print(f"  Dropped rows:    {summary['total_dropped']} ({summary['drop_rate']}%)")
    print(f"  Duplicates:      {summary['duplicates_removed']}")
    print(f"  DB inserted:     {summary['db_inserted']}")
    print(f"{'='*50}\n")

    return summary