# dashboard/pages/dashboard.py

import streamlit as st
import pandas as pd
from app.database.db import get_session
from app.database.models import Transaction, Category
from app.reports.charts import (
    spending_pie_chart,
    monthly_trend_chart,
    total_monthly_bar_chart,
    category_bar_chart,
)


def load_transactions() -> pd.DataFrame:
    session = get_session()
    try:
        txns = session.query(Transaction).all()
        rows = [t.to_dict() for t in txns]
        return pd.DataFrame(rows) if rows else pd.DataFrame()
    finally:
        session.close()


def show_dashboard_page():

    st.markdown("""
    <div class='fade-in'>
        <h1>📊 Expense Dashboard</h1>
        <p style='color:#718096; font-size:16px; margin-bottom:24px;'>
            Real-time financial analytics powered by Machine Learning
        </p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([6, 1])
    with col2:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()

    df = load_transactions()

    if df.empty:
        st.markdown("""
        <div class='glow-card' style='text-align:center; padding:40px;'>
            <div style='font-size:4rem;'>📭</div>
            <h3 style='color:#A5B4FC;'>No transactions found</h3>
            <p style='color:#718096;'>Upload a CSV file from the Upload page to get started</p>
        </div>
        """, unsafe_allow_html=True)
        return

    df["date"]   = pd.to_datetime(df["date"])
    df["amount"] = pd.to_numeric(df["amount"])

    expense_df = df[~df["category"].isin(["Salary & Income", "Transfer"])]
    income_df  = df[df["category"] == "Salary & Income"]

    total_expense = expense_df["amount"].sum()
    total_income  = income_df["amount"].sum()
    net_balance   = total_income - total_expense
    total_txns    = len(df)
    anomaly_count = int(df["is_anomaly"].sum()) if "is_anomaly" in df.columns else 0
    avg_txn       = expense_df["amount"].mean() if not expense_df.empty else 0
    top_category  = expense_df.groupby("category")["amount"].sum().idxmax() \
                    if not expense_df.empty else "N/A"

    # ── Metrics ──────────────────────────────────────
    st.markdown("### 📌 Key Metrics")

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("💸 Total Expenses",   f"Rs {total_expense:,.0f}")
    col2.metric("💰 Total Income",     f"Rs {total_income:,.0f}")
    col3.metric(
        "📊 Net Balance",
        f"Rs {net_balance:,.0f}",
        delta=f"Rs {net_balance:,.0f}",
        delta_color="normal"
    )
    col4.metric("🔢 Transactions",     total_txns)
    col5.metric("🚨 Anomalies",        anomaly_count)
    col6.metric("📈 Avg Transaction",  f"Rs {avg_txn:,.0f}")

    # ── Top category highlight ────────────────────────
    st.markdown(f"""
    <div class='glow-card' style='display:flex; align-items:center; gap:16px;'>
        <div style='font-size:2.5rem;'>🏆</div>
        <div>
            <div style='color:#A0AEC0; font-size:13px; font-weight:600;'>
                TOP SPENDING CATEGORY
            </div>
            <div style='color:#FAFAFA; font-size:22px; font-weight:700;'>
                {top_category}
            </div>
            <div style='color:#6C63FF; font-size:14px;'>
                Rs {expense_df.groupby("category")["amount"].sum().max():,.0f} total spent
            </div>
        </div>
        <div style='margin-left:auto; text-align:right;'>
            <div style='color:#A0AEC0; font-size:13px;'>ANOMALY RATE</div>
            <div style='color:{"#EF4444" if anomaly_count > 0 else "#10B981"};
                        font-size:22px; font-weight:700;'>
                {(anomaly_count/total_txns*100):.1f}%
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # ── Charts Row 1 ─────────────────────────────────
    col1, col2 = st.columns([1, 1])
    with col1:
        st.plotly_chart(
            spending_pie_chart(df),
            use_container_width=True,
        )
    with col2:
        st.plotly_chart(
            total_monthly_bar_chart(df),
            use_container_width=True,
        )

    # ── Charts Row 2 ─────────────────────────────────
    st.plotly_chart(monthly_trend_chart(df), use_container_width=True)
    st.plotly_chart(category_bar_chart(df),  use_container_width=True)

    st.divider()

    # ── Transactions table ────────────────────────────
    st.markdown("### 🧾 Transaction Explorer")

    col1, col2, col3 = st.columns(3)
    with col1:
        category_filter = st.selectbox(
            "Filter by Category",
            ["All"] + sorted(df["category"].unique().tolist())
        )
    with col2:
        anomaly_filter = st.selectbox(
            "Filter by Status",
            ["All", "Normal Only", "Anomalies Only"]
        )
    with col3:
        sort_filter = st.selectbox(
            "Sort by",
            ["Date (Newest)", "Amount (Highest)", "Amount (Lowest)"]
        )

    filtered = df.copy()

    if category_filter != "All":
        filtered = filtered[filtered["category"] == category_filter]

    if anomaly_filter == "Normal Only":
        filtered = filtered[filtered["is_anomaly"] == False]
    elif anomaly_filter == "Anomalies Only":
        filtered = filtered[filtered["is_anomaly"] == True]

    if sort_filter == "Date (Newest)":
        filtered = filtered.sort_values("date", ascending=False)
    elif sort_filter == "Amount (Highest)":
        filtered = filtered.sort_values("amount", ascending=False)
    elif sort_filter == "Amount (Lowest)":
        filtered = filtered.sort_values("amount", ascending=True)

    display_df = filtered.head(30)[[
        "date", "description", "amount", "category", "confidence", "is_anomaly"
    ]].copy()

    display_df["amount"]     = display_df["amount"].apply(lambda x: f"Rs {x:,.0f}")
    display_df["confidence"] = display_df["confidence"].apply(
        lambda x: f"{x:.0%}" if pd.notna(x) else "N/A"
    )
    display_df["is_anomaly"] = display_df["is_anomaly"].apply(
        lambda x: "🚨 Anomaly" if x else "✅ Normal"
    )
    display_df.columns = ["Date", "Description", "Amount", "Category", "ML Confidence", "Status"]

    st.dataframe(display_df, use_container_width=True, hide_index=True)

    st.markdown(f"""
    <p style='color:#4A5568; font-size:13px; text-align:right;'>
        Showing {min(30, len(filtered))} of {len(filtered)} transactions
    </p>
    """, unsafe_allow_html=True)

    st.divider()

    # ── Top 5 expenses ────────────────────────────────
    st.markdown("### 🔝 Top 5 Biggest Expenses")

    top5 = expense_df.nlargest(5, "amount")[
        ["date", "description", "amount", "category"]
    ].copy()

    for i, (_, row) in enumerate(top5.iterrows()):
        rank_colors = ["#FFD700", "#C0C0C0", "#CD7F32", "#6C63FF", "#4ECDC4"]
        st.markdown(f"""
        <div class='glow-card' style='display:flex; align-items:center;
                    gap:16px; margin:8px 0; padding:16px;'>
            <div style='font-size:1.8rem; font-weight:800;
                        color:{rank_colors[i]};'>#{i+1}</div>
            <div style='flex:1;'>
                <div style='color:#FAFAFA; font-weight:600;'>
                    {row["description"].title()}
                </div>
                <div style='color:#718096; font-size:13px;'>
                    {row["category"]} · {str(row["date"])[:10]}
                </div>
            </div>
            <div style='color:#6C63FF; font-size:20px; font-weight:700;'>
                Rs {row["amount"]:,.0f}
            </div>
        </div>
        """, unsafe_allow_html=True)