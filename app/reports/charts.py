# app/reports/charts.py
#
# All Plotly chart functions for the dashboard.
# Each function returns a plotly Figure object that Streamlit
# renders with st.plotly_chart().

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np


# ── Colour palette ─────────────────────────────────────
# Consistent colours across all charts
CATEGORY_COLORS = {
    "Food & Dining":    "#FF6B6B",
    "Transport":        "#4ECDC4",
    "Utilities":        "#45B7D1",
    "Rent & Housing":   "#96CEB4",
    "Shopping":         "#FFEAA7",
    "Healthcare":       "#DDA0DD",
    "Entertainment":    "#98D8C8",
    "Education":        "#F7DC6F",
    "Salary & Income":  "#82E0AA",
    "Transfer":         "#AEB6BF",
    "Other":            "#D7DBDD",
}

ANOMALY_COLORS = {
    "high":   "#E74C3C",
    "medium": "#F39C12",
    "low":    "#F1C40F",
}

CHART_TEMPLATE = "plotly_white"
FONT_FAMILY    = "Arial, sans-serif"


def spending_pie_chart(df: pd.DataFrame) -> go.Figure:
    """
    Pie chart showing spending breakdown by category.
    Excludes income (Salary & Income) so only expenses are shown.

    Args:
        df: DataFrame with columns [category, amount]

    Returns:
        Plotly Figure
    """
    # Aggregate and exclude income categories
    expense_df = df[~df["category"].isin(["Salary & Income", "Transfer"])]
    category_totals = (
        expense_df.groupby("category")["amount"]
        .sum()
        .reset_index()
        .sort_values("amount", ascending=False)
    )

    colors = [CATEGORY_COLORS.get(c, "#CCCCCC") for c in category_totals["category"]]

    fig = go.Figure(data=[go.Pie(
        labels=category_totals["category"],
        values=category_totals["amount"],
        hole=0.4,                    # donut style looks more modern
        marker_colors=colors,
        textinfo="label+percent",
        hovertemplate="<b>%{label}</b><br>Rs %{value:,.0f}<br>%{percent}<extra></extra>",
    )])

    fig.update_layout(
        title=dict(text="Spending by Category", font=dict(size=18)),
        template=CHART_TEMPLATE,
        font=dict(family=FONT_FAMILY),
        showlegend=True,
        legend=dict(orientation="v", x=1.0, y=0.5),
        margin=dict(t=60, b=20, l=20, r=20),
        height=400,
    )

    return fig


def monthly_trend_chart(df: pd.DataFrame) -> go.Figure:
    """
    Line chart showing total monthly spending over time.
    Each category shown as a separate coloured line.

    Args:
        df: DataFrame with columns [date, category, amount]

    Returns:
        Plotly Figure
    """
    df = df.copy()
    df["date"]       = pd.to_datetime(df["date"])
    df["year_month"] = df["date"].dt.to_period("M").astype(str)

    # Exclude income
    df = df[~df["category"].isin(["Salary & Income", "Transfer"])]

    monthly = (
        df.groupby(["year_month", "category"])["amount"]
        .sum()
        .reset_index()
    )

    fig = go.Figure()

    for category in monthly["category"].unique():
        cat_data = monthly[monthly["category"] == category]
        color    = CATEGORY_COLORS.get(category, "#CCCCCC")

        fig.add_trace(go.Scatter(
            x=cat_data["year_month"],
            y=cat_data["amount"],
            mode="lines+markers",
            name=category,
            line=dict(color=color, width=2),
            marker=dict(size=6),
            hovertemplate=(
                f"<b>{category}</b><br>"
                "Month: %{x}<br>"
                "Amount: Rs %{y:,.0f}<extra></extra>"
            ),
        ))

    fig.update_layout(
        title=dict(text="Monthly Spending Trend", font=dict(size=18)),
        xaxis_title="Month",
        yaxis_title="Amount (Rs)",
        template=CHART_TEMPLATE,
        font=dict(family=FONT_FAMILY),
        hovermode="x unified",
        legend=dict(orientation="h", y=-0.2),
        margin=dict(t=60, b=80, l=60, r=20),
        height=420,
    )

    return fig


def total_monthly_bar_chart(df: pd.DataFrame) -> go.Figure:
    """
    Bar chart showing total spending per month (all categories combined).
    Good for showing overall spending trend at a glance.

    Args:
        df: DataFrame with columns [date, amount]

    Returns:
        Plotly Figure
    """
    df = df.copy()
    df["date"]       = pd.to_datetime(df["date"])
    df["year_month"] = df["date"].dt.to_period("M").astype(str)

    # Exclude income
    df = df[~df.get("category", pd.Series(dtype=str)).isin(
        ["Salary & Income", "Transfer"]
    )] if "category" in df.columns else df

    monthly_totals = (
        df.groupby("year_month")["amount"]
        .sum()
        .reset_index()
        .sort_values("year_month")
    )

    fig = go.Figure(data=[go.Bar(
        x=monthly_totals["year_month"],
        y=monthly_totals["amount"],
        marker_color="#4ECDC4",
        hovertemplate="Month: %{x}<br>Total: Rs %{y:,.0f}<extra></extra>",
        text=[f"Rs {v:,.0f}" for v in monthly_totals["amount"]],
        textposition="outside",
    )])

    fig.update_layout(
        title=dict(text="Total Monthly Expenses", font=dict(size=18)),
        xaxis_title="Month",
        yaxis_title="Total Amount (Rs)",
        template=CHART_TEMPLATE,
        font=dict(family=FONT_FAMILY),
        margin=dict(t=60, b=60, l=60, r=20),
        height=380,
    )

    return fig


def anomaly_scatter_chart(df: pd.DataFrame) -> go.Figure:
    """
    Scatter plot: x=date, y=amount, colour=anomaly status.
    Normal transactions shown as small grey dots.
    Anomalies shown as large coloured dots with severity colour coding.

    Args:
        df: DataFrame with columns
            [date, amount, description, category, is_anomaly, severity]

    Returns:
        Plotly Figure
    """
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])

    normal   = df[df["is_anomaly"] == False]
    anomalous = df[df["is_anomaly"] == True]

    fig = go.Figure()

    # Normal transactions — small grey dots
    fig.add_trace(go.Scatter(
        x=normal["date"],
        y=normal["amount"],
        mode="markers",
        name="Normal",
        marker=dict(color="#CCCCCC", size=5, opacity=0.6),
        hovertemplate=(
            "<b>Normal Transaction</b><br>"
            "Date: %{x|%Y-%m-%d}<br>"
            "Amount: Rs %{y:,.0f}<extra></extra>"
        ),
    ))

    # Anomalies — large coloured dots by severity
    if not anomalous.empty:
        severity_col = anomalous.get("severity", pd.Series(["medium"] * len(anomalous)))
        colors = [ANOMALY_COLORS.get(str(s), "#F39C12")
                  for s in anomalous.get("severity", ["medium"] * len(anomalous))]

        fig.add_trace(go.Scatter(
            x=anomalous["date"],
            y=anomalous["amount"],
            mode="markers",
            name="Anomaly",
            marker=dict(
                color=colors,
                size=14,
                symbol="diamond",
                line=dict(color="white", width=1),
            ),
            text=anomalous["description"],
            hovertemplate=(
                "<b>ANOMALY DETECTED</b><br>"
                "Description: %{text}<br>"
                "Date: %{x|%Y-%m-%d}<br>"
                "Amount: Rs %{y:,.0f}<extra></extra>"
            ),
        ))

    fig.update_layout(
        title=dict(text="Transaction Overview — Anomalies Highlighted", font=dict(size=18)),
        xaxis_title="Date",
        yaxis_title="Amount (Rs)",
        template=CHART_TEMPLATE,
        font=dict(family=FONT_FAMILY),
        margin=dict(t=60, b=60, l=60, r=20),
        height=420,
    )

    return fig


def forecast_bar_chart(forecasts: list[dict]) -> go.Figure:
    """
    Horizontal bar chart showing predicted spending per category next month.
    Bars coloured by category with trend arrows in hover text.

    Args:
        forecasts: list of forecast dicts from run_forecast()

    Returns:
        Plotly Figure
    """
    if not forecasts:
        return go.Figure()

    df = pd.DataFrame(forecasts).sort_values("predicted", ascending=True)

    colors = [CATEGORY_COLORS.get(c, "#CCCCCC") for c in df["category"]]

    trend_symbols = {
        "increasing": "↑",
        "decreasing": "↓",
        "stable":     "→",
    }

    hover_texts = [
        f"{trend_symbols.get(row['trend'], '')} {row['trend_note']}"
        for _, row in df.iterrows()
    ]

    fig = go.Figure(data=[go.Bar(
        x=df["predicted"],
        y=df["category"],
        orientation="h",
        marker_color=colors,
        text=[f"Rs {v:,.0f}" for v in df["predicted"]],
        textposition="outside",
        customdata=hover_texts,
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Predicted: Rs %{x:,.0f}<br>"
            "%{customdata}<extra></extra>"
        ),
    )])

    fig.update_layout(
        title=dict(text="Predicted Spending Next Month", font=dict(size=18)),
        xaxis_title="Predicted Amount (Rs)",
        template=CHART_TEMPLATE,
        font=dict(family=FONT_FAMILY),
        margin=dict(t=60, b=60, l=160, r=80),
        height=420,
    )

    return fig


def category_bar_chart(df: pd.DataFrame) -> go.Figure:
    """
    Vertical bar chart — total spending per category over all time.

    Args:
        df: DataFrame with columns [category, amount]

    Returns:
        Plotly Figure
    """
    expense_df = df[~df["category"].isin(["Salary & Income", "Transfer"])]
    totals = (
        expense_df.groupby("category")["amount"]
        .sum()
        .reset_index()
        .sort_values("amount", ascending=False)
    )

    colors = [CATEGORY_COLORS.get(c, "#CCCCCC") for c in totals["category"]]

    fig = go.Figure(data=[go.Bar(
        x=totals["category"],
        y=totals["amount"],
        marker_color=colors,
        hovertemplate="<b>%{x}</b><br>Rs %{y:,.0f}<extra></extra>",
        text=[f"Rs {v:,.0f}" for v in totals["amount"]],
        textposition="outside",
    )])

    fig.update_layout(
        title=dict(text="Total Spending by Category", font=dict(size=18)),
        xaxis_title="Category",
        yaxis_title="Total Amount (Rs)",
        template=CHART_TEMPLATE,
        font=dict(family=FONT_FAMILY),
        xaxis_tickangle=-30,
        margin=dict(t=60, b=100, l=60, r=20),
        height=420,
    )

    return fig