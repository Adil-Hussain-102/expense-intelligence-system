# app/ml/forecaster.py
#
# Predicts next month's spending per category using Linear Regression
# on historical monthly spending data stored in PostgreSQL.
#
# Pipeline:
#   1. Aggregate transactions by month + category from DB
#   2. Build a time-series feature (month number: 1, 2, 3...)
#   3. Train Linear Regression per category
#   4. Predict next month's amount
#   5. Save forecasts to the forecasts table
#   6. Return results for dashboard display

import numpy as np
import pandas as pd
from datetime import date, timedelta
from calendar import monthrange
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score

from app.database.db import get_session
from app.database.models import Transaction, Category, Forecast


def get_monthly_spending(session) -> pd.DataFrame:
    """
    Aggregates all transactions by month and category.

    Groups the transactions table:
      - By calendar month (year + month together)
      - By category name
      - Summing amounts within each group

    Excludes income categories (Salary & Income) because
    we are forecasting EXPENSES, not income.

    Also excludes transactions with no category assigned yet.

    Args:
        session: active SQLAlchemy session

    Returns:
        DataFrame with columns:
          year_month  (e.g. '2024-01')
          category    (e.g. 'Food & Dining')
          total       (e.g. 45230.50)
          month_num   (1, 2, 3... for regression)
    """
    # Load all categorized transactions excluding income
    transactions = (
        session.query(Transaction)
        .filter(Transaction.category_id != None)  # noqa
        .all()
    )

    if not transactions:
        return pd.DataFrame()

    # Build DataFrame from transaction objects
    rows = []
    for t in transactions:
        # Skip income — we forecast expenses only
        if t.category and t.category.name in ("Salary & Income", "Transfer"):
            continue

        rows.append({
            "date":     t.date,
            "category": t.category.name if t.category else "Other",
            "amount":   float(t.amount),
        })

    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame()

    df["date"] = pd.to_datetime(df["date"])

    # Create year_month column: '2024-01', '2024-02', etc.
    df["year_month"] = df["date"].dt.to_period("M").astype(str)

    # Group by month + category, sum amounts
    monthly = (
        df.groupby(["year_month", "category"])["amount"]
        .sum()
        .reset_index()
        .rename(columns={"amount": "total"})
    )

    # Sort chronologically
    monthly = monthly.sort_values("year_month").reset_index(drop=True)

    # Add sequential month number for Linear Regression
    # Regression needs numeric X values, not string dates
    # '2024-01' → 1, '2024-02' → 2, '2024-03' → 3, etc.
    unique_months = sorted(monthly["year_month"].unique())
    month_to_num  = {m: i + 1 for i, m in enumerate(unique_months)}
    monthly["month_num"] = monthly["year_month"].map(month_to_num)

    return monthly


def forecast_category(monthly_df: pd.DataFrame,
                       category: str) -> dict | None:
    """
    Trains a Linear Regression model on one category's monthly history
    and predicts the next month's spending.

    Why Linear Regression?
    - Simple and interpretable (can explain the math to teacher)
    - Works well for short time series (6 months of data)
    - Positive slope = spending trend going up (warn user)
    - Negative slope = spending trend going down (good news)
    - Easy to add confidence intervals

    Minimum data requirement: at least 3 months of history.
    With fewer than 3 data points, regression is unreliable.

    Args:
        monthly_df: DataFrame with all categories' monthly totals
        category:   name of the category to forecast

    Returns:
        dict with forecast details, or None if insufficient data
    """
    # Filter to this category only
    cat_data = monthly_df[monthly_df["category"] == category].copy()
    cat_data = cat_data.sort_values("month_num")

    if len(cat_data) < 3:
        return None  # not enough history for a reliable forecast

    # X = month numbers as column vector (required by sklearn)
    # y = spending amounts
    X = cat_data["month_num"].values.reshape(-1, 1)
    y = cat_data["total"].values

    # Train Linear Regression
    # This finds the line y = m*x + b that minimises sum of squared errors
    model = LinearRegression()
    model.fit(X, y)

    # Predict for next month (max month number + 1)
    next_month_num = int(cat_data["month_num"].max()) + 1
    predicted = float(model.predict([[next_month_num]])[0])

    # Predicted spending cannot be negative
    predicted = max(0, predicted)

    # ── Model quality metrics ──────────────────────────────
    y_pred_train = model.predict(X)

    # R² score: 1.0 = perfect fit, 0.0 = no better than using the mean
    # Negative = model is worse than just predicting the average
    r2 = r2_score(y, y_pred_train)

    # MAE: average error in Rs — easy to understand
    mae = mean_absolute_error(y, y_pred_train)

    # ── Trend analysis ─────────────────────────────────────
    slope     = float(model.coef_[0])
    intercept = float(model.intercept_)

    # What does the slope mean in plain language?
    if slope > 500:
        trend = "increasing"
        trend_note = f"Spending is rising by ~Rs {slope:,.0f} per month"
    elif slope < -500:
        trend = "decreasing"
        trend_note = f"Spending is falling by ~Rs {abs(slope):,.0f} per month"
    else:
        trend = "stable"
        trend_note = "Spending is relatively stable month to month"

    # ── Confidence interval ────────────────────────────────
    # Simple ±1 MAE interval — tells user the prediction uncertainty
    lower_bound = max(0, predicted - mae)
    upper_bound = predicted + mae

    # ── Determine next month date ──────────────────────────
    # Find the latest year_month in this category's data
    last_month_str = cat_data["year_month"].max()   # e.g. '2024-04'
    last_period    = pd.Period(last_month_str, freq="M")
    next_period    = last_period + 1
    # first day of next month as Python date
    next_month_date = date(next_period.year, next_period.month, 1)

    return {
        "category":        category,
        "predicted":       round(predicted, 2),
        "lower_bound":     round(lower_bound, 2),
        "upper_bound":     round(upper_bound, 2),
        "trend":           trend,
        "trend_note":      trend_note,
        "slope":           round(slope, 2),
        "r2_score":        round(r2, 4),
        "mae":             round(mae, 2),
        "forecast_month":  next_month_date,
        "history_months":  len(cat_data),
        "history":         cat_data[["year_month", "total"]].to_dict("records"),
    }


def run_forecast(save_to_db: bool = True) -> dict:
    """
    MASTER FUNCTION — generates forecasts for all expense categories.

    Steps:
    1. Load and aggregate monthly spending from DB
    2. For each category with sufficient history, run Linear Regression
    3. Collect all predictions
    4. Optionally save to forecasts table
    5. Return complete results for dashboard

    Args:
        save_to_db: whether to persist forecasts to PostgreSQL

    Returns:
        dict with all category forecasts + total predicted spending
    """
    print(f"\n{'='*50}")
    print("  Running Spending Forecaster")
    print(f"{'='*50}\n")

    session = get_session()

    try:
        # ── Step 1: Get monthly spending history ───────────
        print("[1/3] Aggregating monthly spending from database...")
        monthly_df = get_monthly_spending(session)

        if monthly_df.empty:
            print("No transaction data found for forecasting.")
            return {"forecasts": [], "total_predicted": 0}

        unique_months     = monthly_df["year_month"].nunique()
        unique_categories = monthly_df["category"].nunique()
        print(f"  Found {unique_months} months of data across {unique_categories} categories")

        # Show monthly totals
        monthly_totals = (
            monthly_df.groupby("year_month")["total"]
            .sum()
            .reset_index()
        )
        print("\n  Monthly spending history:")
        for _, row in monthly_totals.iterrows():
            print(f"    {row['year_month']}: Rs {row['total']:>10,.0f}")

        # ── Step 2: Forecast each category ────────────────
        print(f"\n[2/3] Forecasting per category...")
        categories  = monthly_df["category"].unique()
        forecasts   = []
        skipped     = []

        for cat in sorted(categories):
            result = forecast_category(monthly_df, cat)
            if result:
                forecasts.append(result)
                trend_icon = "↑" if result["trend"] == "increasing" else \
                             "↓" if result["trend"] == "decreasing" else "→"
                print(
                    f"  {cat:20} → Rs {result['predicted']:>9,.0f} "
                    f"{trend_icon}  (R²={result['r2_score']:.2f})"
                )
            else:
                skipped.append(cat)

        if skipped:
            print(f"\n  Skipped (insufficient data): {skipped}")

        # Total predicted spending next month
        total_predicted = sum(f["predicted"] for f in forecasts)
        print(f"\n  Total predicted next month: Rs {total_predicted:,.0f}")

        # ── Step 3: Save to database ───────────────────────
        saved = 0
        if save_to_db and forecasts:
            print(f"\n[3/3] Saving forecasts to database...")

            # Get category lookup dict
            db_categories = session.query(Category).all()
            cat_id_lookup = {c.name: c.id for c in db_categories}

            for f in forecasts:
                cat_id = cat_id_lookup.get(f["category"])
                if not cat_id:
                    continue

                # Check if forecast already exists for this month + category
                existing = session.query(Forecast).filter_by(
                    category_id=cat_id,
                    forecast_month=f["forecast_month"],
                ).first()

                if existing:
                    # Update existing forecast
                    existing.predicted_amount = f["predicted"]
                else:
                    # Create new forecast record
                    session.add(Forecast(
                        category_id=cat_id,
                        forecast_month=f["forecast_month"],
                        predicted_amount=f["predicted"],
                    ))
                saved += 1

            session.commit()
            print(f"  ✓ {saved} forecasts saved to database")

        summary = {
            "forecasts":       forecasts,
            "total_predicted": round(total_predicted, 2),
            "months_of_data":  unique_months,
            "categories_forecast": len(forecasts),
            "categories_skipped":  len(skipped),
        }

        print(f"\n{'='*50}")
        print(f"  Forecast Complete")
        print(f"  Categories forecast: {len(forecasts)}")
        print(f"  Total predicted:     Rs {total_predicted:,.0f}")
        print(f"{'='*50}\n")

        return summary

    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def get_forecast_summary(session=None) -> pd.DataFrame:
    """
    Loads all saved forecasts from the database into a DataFrame.
    Used by the Streamlit dashboard to display the forecast page.

    Returns:
        DataFrame with category name, month, predicted amount, actual amount
    """
    close = False
    if session is None:
        session = get_session()
        close = True

    try:
        forecasts = session.query(Forecast).all()
        rows = []
        for f in forecasts:
            rows.append({
                "category":        f.category.name if f.category else "Unknown",
                "forecast_month":  str(f.forecast_month),
                "predicted":       float(f.predicted_amount) if f.predicted_amount else 0,
                "actual":          float(f.actual_amount) if f.actual_amount else None,
                "created_at":      str(f.created_at),
            })
        return pd.DataFrame(rows)
    finally:
        if close:
            session.close()