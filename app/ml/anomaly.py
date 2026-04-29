# app/ml/anomaly.py
#
# Detects anomalous transactions using two methods:
#
# Method 1: Z-score (statistical)
#   - Per category: compute mean and std deviation of amounts
#   - Flag transactions where amount is more than N std deviations from mean
#   - Simple, fast, highly explainable
#   - Best for: catching obviously large individual transactions
#
# Method 2: Isolation Forest (ML-based, unsupervised)
#   - Learns the "normal" pattern from all transactions together
#   - Flags points that are isolated quickly by random partitioning
#   - Catches multi-dimensional outliers Z-score might miss
#   - Best for: finding subtle patterns across amount + time + frequency
#
# Both methods write results to the anomalies table.

import numpy as np
import pandas as pd
from datetime import datetime
from scipy import stats
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from app.database.db import get_session
from app.database.models import Transaction, Anomaly, Category


# ── Configuration ─────────────────────────────────────────
# Z-score threshold: how many std deviations = anomaly
# 2.0 = catches top ~5% of transactions per category (more sensitive)
# 3.0 = catches top ~0.3% (more conservative)
# Start with 2.5 — a good balance for financial data
ZSCORE_THRESHOLD = 2.5

# Isolation Forest contamination: expected proportion of anomalies
# 0.05 means we expect ~5% of transactions to be anomalous
# Adjust based on your data — more conservative = lower value
IF_CONTAMINATION = 0.05


def get_transactions_df(session) -> pd.DataFrame:
    """
    Loads all transactions from the database into a pandas DataFrame.
    Adds engineered features that help anomaly detection:
      - day_of_week: 0=Monday, 6=Sunday (weekend transactions can be unusual)
      - day_of_month: 1-31 (salary on 1st, rent on 5th = expected patterns)
      - month: 1-12 (seasonal patterns)
      - amount_log: log of amount (reduces scale impact of very large values)

    Args:
        session: active SQLAlchemy session

    Returns:
        DataFrame with one row per transaction + engineered features
    """
    transactions = session.query(Transaction).all()

    if not transactions:
        return pd.DataFrame()

    rows = []
    for t in transactions:
        rows.append({
            "id":          t.id,
            "date":        t.date,
            "description": t.description,
            "amount":      float(t.amount),
            "category_id": t.category_id,
            "category":    t.category.name if t.category else "Uncategorized",
            "is_anomaly":  t.is_anomaly,
        })

    df = pd.DataFrame(rows)

    # ── Feature engineering ────────────────────────────────
    df["date"] = pd.to_datetime(df["date"])

    # Time-based features
    df["day_of_week"]  = df["date"].dt.dayofweek    # 0=Mon, 6=Sun
    df["day_of_month"] = df["date"].dt.day          # 1–31
    df["month"]        = df["date"].dt.month        # 1–12

    # Log-transform amount: reduces impact of extreme outliers on scaling
    # Adding 1 prevents log(0) error
    df["amount_log"] = np.log1p(df["amount"])

    return df


def zscore_detection(df: pd.DataFrame, threshold: float = ZSCORE_THRESHOLD) -> list[dict]:
    """
    Detects anomalies using Z-score per category.

    Z-score formula:
        z = (x - mean) / std_deviation

    If z > threshold, the transaction is flagged.
    Example: mean food spending = Rs 1,200, std = Rs 400
    A Rs 8,000 food transaction has z = (8000-1200)/400 = 17.0 → anomaly

    Why per category?
    A Rs 50,000 transaction in 'Rent & Housing' is completely normal.
    The same amount in 'Food & Dining' is extremely suspicious.
    Computing Z-score within each category catches this correctly.

    Args:
        df:        DataFrame with all transactions
        threshold: Z-score above this value = flagged as anomaly

    Returns:
        List of dicts, one per detected anomaly
    """
    anomalies = []

    # Process each category separately
    for category, group in df.groupby("category"):

        # Need at least 3 transactions to compute meaningful statistics
        if len(group) < 3:
            continue

        amounts = group["amount"].values
        mean    = amounts.mean()
        std     = amounts.std()

        # If all transactions have the same amount, std=0 → skip
        if std == 0:
            continue

        # Compute Z-score for each transaction in this category
        z_scores = np.abs(stats.zscore(amounts))

        # Find transactions above threshold
        anomaly_indices = np.where(z_scores > threshold)[0]

        for idx in anomaly_indices:
            row       = group.iloc[idx]
            z         = z_scores[idx]
            deviation = row["amount"] - mean

            # Determine severity based on how extreme the Z-score is
            if z > 5.0:
                severity = "high"
            elif z > 3.5:
                severity = "medium"
            else:
                severity = "low"

            anomalies.append({
                "transaction_id": int(row["id"]),
                "method":         "zscore",
                "severity":       severity,
                "reason": (
                    f"Amount Rs {row['amount']:,.0f} is {z:.1f} standard deviations "
                    f"above the {category} category mean of Rs {mean:,.0f}. "
                    f"Deviation: Rs {deviation:+,.0f}."
                ),
                "z_score": round(z, 2),
            })

    return anomalies


def isolation_forest_detection(df: pd.DataFrame,
                                contamination: float = IF_CONTAMINATION) -> list[dict]:
    """
    Detects anomalies using Isolation Forest.

    This algorithm works by:
    1. Randomly selecting a feature (e.g. amount)
    2. Randomly selecting a split value between min and max
    3. Repeating until each point is isolated
    4. Anomalies are isolated in fewer steps (shorter path length)
    5. The anomaly score = average path length across many trees

    Features used:
    - amount_log:   the transaction amount (log-scaled)
    - day_of_week:  unusual day patterns (3am Saturday ATM withdrawal)
    - day_of_month: unexpected timing within month

    Args:
        df:            DataFrame with all transactions + engineered features
        contamination: expected proportion of anomalies in the dataset

    Returns:
        List of dicts, one per detected anomaly
    """
    # Need enough transactions for Isolation Forest to learn patterns
    if len(df) < 10:
        print("  Too few transactions for Isolation Forest (need at least 10)")
        return []

    # Select features for anomaly detection
    feature_cols = ["amount_log", "day_of_week", "day_of_month"]
    X = df[feature_cols].fillna(0)  # fill any NaN with 0

    # Standardise features so amount doesn't dominate just because it's larger
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Train Isolation Forest
    # n_estimators=100: build 100 isolation trees
    # random_state=42:  reproducible results
    model = IsolationForest(
        n_estimators=100,
        contamination=contamination,
        random_state=42,
        n_jobs=-1,
    )
    predictions = model.fit_predict(X_scaled)
    scores      = model.decision_function(X_scaled)

    # Isolation Forest returns:
    # +1 = normal transaction
    # -1 = anomaly
    anomaly_mask = predictions == -1
    anomaly_rows = df[anomaly_mask]

    anomalies = []
    for _, row in anomaly_rows.iterrows():
        score = scores[df.index.get_loc(row.name)]

        # More negative score = more anomalous
        if score < -0.2:
            severity = "high"
        elif score < -0.1:
            severity = "medium"
        else:
            severity = "low"

        anomalies.append({
            "transaction_id": int(row["id"]),
            "method":         "isolation_forest",
            "severity":       severity,
            "reason": (
                f"Isolation Forest detected unusual pattern. "
                f"Transaction amount Rs {row['amount']:,.0f} on "
                f"{row['date'].strftime('%Y-%m-%d')} "
                f"shows abnormal behaviour across multiple dimensions. "
                f"Anomaly score: {score:.4f}."
            ),
            "z_score": None,
        })

    return anomalies


def merge_anomaly_results(zscore_results: list[dict],
                           iforest_results: list[dict]) -> list[dict]:
    """
    Merges results from both methods, removing duplicates.

    Logic:
    - If BOTH methods flag the same transaction → severity = 'high'
      (two independent methods agreeing = very strong signal)
    - If only ONE method flags it → keep original severity
    - Deduplicate by transaction_id, keeping highest severity

    Args:
        zscore_results:  anomalies from Z-score method
        iforest_results: anomalies from Isolation Forest method

    Returns:
        Merged, deduplicated list of anomalies
    """
    severity_rank = {"low": 1, "medium": 2, "high": 3}

    # Build dict: transaction_id → best anomaly record so far
    merged = {}

    all_results = zscore_results + iforest_results

    for anomaly in all_results:
        txn_id = anomaly["transaction_id"]

        if txn_id not in merged:
            merged[txn_id] = anomaly
        else:
            existing = merged[txn_id]

            # Both methods detected this — upgrade to high severity
            if existing["method"] != anomaly["method"]:
                merged[txn_id] = {
                    **anomaly,
                    "severity": "high",
                    "reason": (
                        f"CONFIRMED by both Z-score and Isolation Forest. "
                        f"{existing['reason']}"
                    ),
                    "method": "both",
                }
            else:
                # Same method, keep highest severity
                if severity_rank.get(anomaly["severity"], 0) > \
                   severity_rank.get(existing["severity"], 0):
                    merged[txn_id] = anomaly

    return list(merged.values())


def save_anomalies_to_db(anomalies: list[dict], session) -> int:
    """
    Saves detected anomalies to the database.

    Updates two things:
    1. transactions.is_anomaly = True  (flag on the transaction itself)
    2. Inserts a row in anomalies table (with reason and severity)

    Skips transactions that already have an anomaly record to avoid duplicates.

    Args:
        anomalies: list of anomaly dicts from detection functions
        session:   active SQLAlchemy session

    Returns:
        Number of new anomaly records inserted
    """
    inserted = 0

    for anom in anomalies:
        txn_id = anom["transaction_id"]

        # Check if anomaly record already exists for this transaction
        existing = session.query(Anomaly).filter_by(
            transaction_id=txn_id
        ).first()

        if existing:
            continue  # already flagged, skip

        # Update the transaction's is_anomaly flag
        txn = session.query(Transaction).get(txn_id)
        if txn:
            txn.is_anomaly = True

        # Create the anomaly detail record
        anomaly_record = Anomaly(
            transaction_id=txn_id,
            reason=anom["reason"],
            severity=anom["severity"],
        )
        session.add(anomaly_record)
        inserted += 1

    session.commit()
    return inserted


def run_anomaly_detection(zscore_threshold: float = ZSCORE_THRESHOLD,
                           if_contamination: float = IF_CONTAMINATION) -> dict:
    """
    MASTER FUNCTION — runs the complete anomaly detection pipeline.

    Steps:
    1. Load all transactions from DB into DataFrame
    2. Run Z-score detection per category
    3. Run Isolation Forest detection across all transactions
    4. Merge results from both methods
    5. Save flagged transactions to DB
    6. Return summary report

    Args:
        zscore_threshold: Z-score cutoff (default 2.5)
        if_contamination: expected anomaly proportion (default 0.05)

    Returns:
        dict with detection summary
    """
    print(f"\n{'='*50}")
    print("  Running Anomaly Detection")
    print(f"{'='*50}\n")

    session = get_session()

    try:
        # ── Step 1: Load data ──────────────────────────────
        print("[1/5] Loading transactions...")
        df = get_transactions_df(session)

        if df.empty:
            print("No transactions found in database.")
            return {"total_flagged": 0}

        print(f"  Loaded {len(df)} transactions")

        # ── Step 2: Z-score detection ──────────────────────
        print(f"\n[2/5] Running Z-score detection (threshold={zscore_threshold})...")
        zscore_anomalies = zscore_detection(df, threshold=zscore_threshold)
        print(f"  Z-score flagged: {len(zscore_anomalies)} transactions")

        # ── Step 3: Isolation Forest ───────────────────────
        print(f"\n[3/5] Running Isolation Forest (contamination={if_contamination})...")
        iforest_anomalies = isolation_forest_detection(df, contamination=if_contamination)
        print(f"  Isolation Forest flagged: {len(iforest_anomalies)} transactions")

        # ── Step 4: Merge results ──────────────────────────
        print(f"\n[4/5] Merging results from both methods...")
        merged = merge_anomaly_results(zscore_anomalies, iforest_anomalies)
        print(f"  Total unique anomalies: {len(merged)}")

        # Show breakdown by severity
        severities = {}
        for a in merged:
            s = a["severity"]
            severities[s] = severities.get(s, 0) + 1
        for s, count in sorted(severities.items()):
            print(f"  {s.upper():6}: {count}")

        # ── Step 5: Save to database ───────────────────────
        print(f"\n[5/5] Saving anomalies to database...")
        inserted = save_anomalies_to_db(merged, session)
        print(f"  ✓ {inserted} new anomaly records saved")

        # Build summary
        summary = {
            "total_transactions":  len(df),
            "zscore_flagged":      len(zscore_anomalies),
            "iforest_flagged":     len(iforest_anomalies),
            "total_flagged":       len(merged),
            "new_db_records":      inserted,
            "severity_breakdown":  severities,
            "anomalies":           merged,
        }

        print(f"\n{'='*50}")
        print(f"  Detection Complete")
        print(f"  Total transactions: {len(df)}")
        print(f"  Anomalies found:    {len(merged)}")
        print(f"{'='*50}\n")

        return summary

    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def get_anomaly_summary(session=None) -> pd.DataFrame:
    """
    Returns a DataFrame of all anomalous transactions with their details.
    Used by the Streamlit dashboard to display the anomaly table.

    Args:
        session: SQLAlchemy session (creates one if None)

    Returns:
        DataFrame with transaction + anomaly details
    """
    close = False
    if session is None:
        session = get_session()
        close = True

    try:
        anomalies = session.query(Anomaly).all()

        rows = []
        for a in anomalies:
            txn = a.transaction
            if not txn:
                continue
            rows.append({
                "id":          txn.id,
                "date":        str(txn.date),
                "description": txn.description,
                "amount":      float(txn.amount),
                "category":    txn.category.name if txn.category else "Unknown",
                "severity":    a.severity,
                "reason":      a.reason,
                "detected_at": str(a.detected_at),
            })

        return pd.DataFrame(rows)

    finally:
        if close:
            session.close()