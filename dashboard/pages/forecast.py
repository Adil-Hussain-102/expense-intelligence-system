# dashboard/pages/forecast.py

import streamlit as st
import pandas as pd
from app.ml.forecaster import run_forecast, get_forecast_summary
from app.reports.charts import forecast_bar_chart


def show_forecast_page():

    st.markdown("""
    <div class='fade-in'>
        <h1>📈 Spending Forecast</h1>
        <p style='color:#718096; font-size:16px; margin-bottom:24px;'>
            AI-powered next month predictions using
            <b style='color:#6C63FF;'>Linear Regression</b>
            on your historical spending patterns
        </p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([6, 1])
    with col2:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()

    # ── How it works ──────────────────────────────────
    st.markdown("""
    <div class='glow-card'>
        <h3 style='margin-top:0; color:#A5B4FC;'>🧠 How Forecasting Works</h3>
        <div style='display:flex; gap:16px; flex-wrap:wrap;'>
            <div style='flex:1; min-width:120px;'>
                <div style='color:#6C63FF; font-weight:700;'>📊 Data Collection</div>
                <div style='color:#718096; font-size:13px;'>
                    Aggregates monthly spending per category from all transactions
                </div>
            </div>
            <div style='flex:1; min-width:120px;'>
                <div style='color:#4ECDC4; font-weight:700;'>📐 Linear Regression</div>
                <div style='color:#718096; font-size:13px;'>
                    Fits y=mx+b to find the spending trend line per category
                </div>
            </div>
            <div style='flex:1; min-width:120px;'>
                <div style='color:#F59E0B; font-weight:700;'>🔮 Prediction</div>
                <div style='color:#718096; font-size:13px;'>
                    Extends the trend line to predict next month's amount
                </div>
            </div>
            <div style='flex:1; min-width:120px;'>
                <div style='color:#10B981; font-weight:700;'>📏 R² Score</div>
                <div style='color:#718096; font-size:13px;'>
                    Measures reliability — higher R² = more accurate prediction
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    col1, col2 = st.columns([2, 5])
    with col1:
        if st.button("🔄 Refresh Forecast", type="primary",
                     use_container_width=True):
            with st.spinner("Running Linear Regression..."):
                result = run_forecast(save_to_db=True)
            st.success(f"✅ Updated! Total: Rs {result['total_predicted']:,.0f}")
            st.rerun()

    forecast_df = get_forecast_summary()

    if forecast_df.empty:
        st.markdown("""
        <div class='glow-card' style='text-align:center; padding:40px;'>
            <div style='font-size:4rem;'>🔮</div>
            <h3 style='color:#A5B4FC;'>No Forecasts Yet</h3>
            <p style='color:#718096;'>
                Click <b>Refresh Forecast</b> above to generate
                next month's spending predictions
            </p>
        </div>
        """, unsafe_allow_html=True)
        return

    # ── Metrics ──────────────────────────────────────
    total_predicted = forecast_df["predicted"].sum()
    highest_row     = forecast_df.loc[forecast_df["predicted"].idxmax()]
    lowest_row      = forecast_df.loc[forecast_df["predicted"].idxmin()]
    num_categories  = len(forecast_df)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("💰 Total Predicted",   f"Rs {total_predicted:,.0f}")
    col2.metric("🔝 Highest Category",  highest_row["category"])
    col3.metric("💸 Highest Amount",    f"Rs {highest_row['predicted']:,.0f}")
    col4.metric("✅ Categories",         num_categories)

    # ── Budget warning ────────────────────────────────
    if total_predicted > 200000:
        st.markdown(f"""
        <div class='danger-box'>
            ⚠️ <b>High Spending Alert!</b> Predicted total of
            <b>Rs {total_predicted:,.0f}</b> next month is above Rs 200,000.
            Consider reviewing your {highest_row["category"]} expenses.
        </div>
        """, unsafe_allow_html=True)
    elif total_predicted > 100000:
        st.markdown(f"""
        <div class='warning-box'>
            💡 <b>Moderate Spending:</b> Predicted Rs {total_predicted:,.0f}
            next month. Your biggest category is {highest_row["category"]}.
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class='success-box'>
            ✅ <b>Good spending pattern!</b> Predicted Rs {total_predicted:,.0f}
            next month looks healthy.
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # ── Forecast chart ────────────────────────────────
    forecast_list = forecast_df.to_dict("records")
    for row in forecast_list:
        row["trend"]      = "stable"
        row["trend_note"] = "Based on historical linear trend"

    st.plotly_chart(
        forecast_bar_chart(forecast_list),
        use_container_width=True
    )

    st.divider()

    # ── Category forecast cards ───────────────────────
    st.markdown("### 📋 Category Breakdown")

    sorted_df = forecast_df.sort_values("predicted", ascending=False)

    cols = st.columns(3)
    for i, (_, row) in enumerate(sorted_df.iterrows()):
        col = cols[i % 3]

        pct_of_total = (row["predicted"] / total_predicted * 100) if total_predicted > 0 else 0

        if pct_of_total > 30:
            bar_color = "#EF4444"
        elif pct_of_total > 15:
            bar_color = "#F59E0B"
        else:
            bar_color = "#10B981"

        with col:
            st.markdown(f"""
            <div class='glow-card' style='margin:8px 0;'>
                <div style='color:#A0AEC0; font-size:12px;
                            font-weight:600; margin-bottom:4px;'>
                    {row["category"].upper()}
                </div>
                <div style='color:#FAFAFA; font-size:20px;
                            font-weight:700; margin-bottom:8px;'>
                    Rs {row["predicted"]:,.0f}
                </div>
                <div style='background:#252A40; border-radius:6px;
                            height:6px; margin-bottom:6px;'>
                    <div style='background:{bar_color}; width:{min(pct_of_total, 100):.0f}%;
                                height:6px; border-radius:6px;
                                transition: width 1s ease;'>
                    </div>
                </div>
                <div style='color:#718096; font-size:12px;'>
                    {pct_of_total:.1f}% of total budget ·
                    {row["forecast_month"]}
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.divider()

    # ── Detailed table ────────────────────────────────
    st.markdown("### 📊 Detailed Predictions Table")

    display = forecast_df.copy()
    display["predicted"] = display["predicted"].apply(
        lambda x: f"Rs {x:,.0f}"
    )
    display["actual"] = display["actual"].apply(
        lambda x: f"Rs {x:,.0f}" if pd.notna(x) else "⏳ Pending"
    )
    display.columns = [
        "Category", "Forecast Month",
        "Predicted Amount", "Actual Amount", "Generated At"
    ]
    st.dataframe(display, use_container_width=True, hide_index=True)

    st.divider()

    st.markdown("""
    <div class='info-box'>
        📖 <b>Reading your forecast:</b>
        Higher R² = more reliable prediction ·
        Actual amounts fill in at month end ·
        Click Refresh after uploading new transactions ·
        Categories with less than 3 months history are excluded
    </div>
    """, unsafe_allow_html=True)