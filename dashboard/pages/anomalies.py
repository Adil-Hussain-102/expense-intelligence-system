# dashboard/pages/anomalies.py

import streamlit as st
import pandas as pd
from app.ml.anomaly import get_anomaly_summary
from app.database.db import get_session
from app.database.models import Transaction
from app.reports.charts import anomaly_scatter_chart


def show_anomalies_page():

    st.markdown("""
    <div class='fade-in'>
        <h1>🚨 Anomaly Detection</h1>
        <p style='color:#718096; font-size:16px; margin-bottom:24px;'>
            Suspicious transactions flagged by <b style='color:#6C63FF;'>Z-score</b>
            and <b style='color:#4ECDC4;'>Isolation Forest</b> algorithms
        </p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([6, 1])
    with col2:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()

    anom_df = get_anomaly_summary()

    if anom_df.empty:
        st.markdown("""
        <div class='glow-card' style='text-align:center; padding:40px;'>
            <div style='font-size:4rem;'>✅</div>
            <h3 style='color:#10B981;'>No Anomalies Detected</h3>
            <p style='color:#718096;'>
                All transactions look normal. Upload more data and
                run anomaly detection to check for suspicious activity.
            </p>
        </div>
        """, unsafe_allow_html=True)
        return

    high   = len(anom_df[anom_df["severity"] == "high"])
    medium = len(anom_df[anom_df["severity"] == "medium"])
    low    = len(anom_df[anom_df["severity"] == "low"])
    total_amount = anom_df["amount"].sum()

    # ── Alert banner for high severity ───────────────
    if high > 0:
        st.markdown(f"""
        <div class='danger-box' style='display:flex; align-items:center; gap:12px;'>
            <span class='pulse-badge'>🔴 ALERT</span>
            <span>
                <b>{high} HIGH severity</b> anomalies detected!
                Immediate review recommended.
                Total suspicious amount: <b>Rs {anom_df[anom_df["severity"]=="high"]["amount"].sum():,.0f}</b>
            </span>
        </div>
        """, unsafe_allow_html=True)

    # ── Metrics ──────────────────────────────────────
    st.markdown("### 📊 Detection Summary")

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("🚨 Total Flagged",    len(anom_df))
    col2.metric("🔴 High Severity",    high)
    col3.metric("🟡 Medium Severity",  medium)
    col4.metric("🟢 Low Severity",     low)
    col5.metric("💰 Suspicious Amount", f"Rs {total_amount:,.0f}")

    # ── Method breakdown ──────────────────────────────
    st.markdown("""
    <div style='display:flex; gap:16px; margin:16px 0;'>
        <div class='glow-card' style='flex:1; text-align:center;'>
            <div style='font-size:2rem;'>📊</div>
            <div style='color:#6C63FF; font-weight:700; font-size:18px;'>Z-Score</div>
            <div style='color:#718096; font-size:13px;'>
                Detects amount outliers<br>per category
            </div>
        </div>
        <div class='glow-card' style='flex:1; text-align:center;'>
            <div style='font-size:2rem;'>🌲</div>
            <div style='color:#4ECDC4; font-weight:700; font-size:18px;'>Isolation Forest</div>
            <div style='color:#718096; font-size:13px;'>
                Detects multi-dimensional<br>outliers
            </div>
        </div>
        <div class='glow-card' style='flex:1; text-align:center;'>
            <div style='font-size:2rem;'>🔗</div>
            <div style='color:#F59E0B; font-weight:700; font-size:18px;'>Combined</div>
            <div style='color:#718096; font-size:13px;'>
                Double-confirmed = HIGH<br>severity automatic
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # ── Scatter chart ─────────────────────────────────
    session = get_session()
    try:
        all_txns = session.query(Transaction).all()
        txn_rows = []
        for t in all_txns:
            txn_rows.append({
                "date":        str(t.date),
                "amount":      float(t.amount),
                "description": t.description,
                "category":    t.category.name if t.category else "Other",
                "is_anomaly":  t.is_anomaly,
                "severity":    "normal",
            })
        all_df = pd.DataFrame(txn_rows)
    finally:
        session.close()

    severity_map = dict(zip(anom_df["id"], anom_df["severity"]))
    all_df["severity"] = all_df.index.map(
        lambda i: severity_map.get(i, "normal")
    )

    st.plotly_chart(
        anomaly_scatter_chart(all_df),
        use_container_width=True
    )

    st.divider()

    # ── Filters ───────────────────────────────────────
    st.markdown("### 🔍 Flagged Transactions")

    col1, col2, col3 = st.columns(3)
    with col1:
        severity_filter = st.multiselect(
            "Severity",
            options=["high", "medium", "low"],
            default=["high", "medium", "low"],
        )
    with col2:
        sort_by = st.selectbox(
            "Sort by",
            ["Amount (High to Low)", "Date (Newest)", "Severity"]
        )
    with col3:
        search = st.text_input("🔎 Search description", "")

    filtered = anom_df[anom_df["severity"].isin(severity_filter)].copy()

    if search:
        filtered = filtered[
            filtered["description"].str.contains(search, case=False, na=False)
        ]

    if sort_by == "Amount (High to Low)":
        filtered = filtered.sort_values("amount", ascending=False)
    elif sort_by == "Date (Newest)":
        filtered = filtered.sort_values("date", ascending=False)
    elif sort_by == "Severity":
        order = {"high": 0, "medium": 1, "low": 2}
        filtered["sev_rank"] = filtered["severity"].map(order)
        filtered = filtered.sort_values("sev_rank")

    # ── Anomaly cards ─────────────────────────────────
    for _, row in filtered.iterrows():
        severity = row["severity"]
        if severity == "high":
            border_color = "#EF4444"
            badge        = "🔴 HIGH"
            bg_color     = "#4A000022"
        elif severity == "medium":
            border_color = "#F59E0B"
            badge        = "🟡 MEDIUM"
            bg_color     = "#4A300022"
        else:
            border_color = "#F1C40F"
            badge        = "🟢 LOW"
            bg_color     = "#4A4A0022"

        st.markdown(f"""
        <div class='glow-card' style='border-left: 4px solid {border_color};
                    background: {bg_color}; margin: 8px 0;'>
            <div style='display:flex; justify-content:space-between;
                        align-items:flex-start;'>
                <div style='flex:1;'>
                    <div style='display:flex; align-items:center; gap:10px;
                                margin-bottom:8px;'>
                        <span style='background:{border_color}22;
                                     color:{border_color}; padding:3px 10px;
                                     border-radius:20px; font-size:12px;
                                     font-weight:700;'>{badge}</span>
                        <span style='color:#A0AEC0; font-size:13px;'>
                            {row["date"]} · {row["category"]}
                        </span>
                    </div>
                    <div style='color:#FAFAFA; font-weight:600;
                                font-size:16px; margin-bottom:6px;'>
                        {str(row["description"]).title()}
                    </div>
                    <div style='color:#718096; font-size:13px;
                                line-height:1.5;'>
                        {row["reason"]}
                    </div>
                </div>
                <div style='text-align:right; margin-left:20px;'>
                    <div style='color:{border_color}; font-size:22px;
                                font-weight:800;'>
                        Rs {row["amount"]:,.0f}
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()
    st.markdown(f"""
    <div class='info-box'>
        📊 Showing <b>{len(filtered)}</b> of <b>{len(anom_df)}</b> anomalies ·
        Total suspicious value: <b>Rs {filtered["amount"].sum():,.0f}</b>
    </div>
    """, unsafe_allow_html=True)