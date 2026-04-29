# dashboard/main.py

import streamlit as st

# Force refresh when data changes
if "refresh_dashboard" not in st.session_state:
    st.session_state["refresh_dashboard"] = 0

st.set_page_config(
    page_title="Expense Intelligence System",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    /* ── Global ── */
    html, body, [class*="css"] {
        font-family: 'Segoe UI', sans-serif;
    }

    /* ── Hide Streamlit default elements ── */
    #MainMenu { visibility: hidden; }
    footer     { visibility: hidden; }
    header     { visibility: hidden; }

    /* ── Animated gradient background ── */
    .main {
        background: linear-gradient(135deg, #0F1117 0%, #1E2130 50%, #0F1117 100%);
        background-size: 400% 400%;
        animation: gradientShift 15s ease infinite;
    }

    @keyframes gradientShift {
        0%   { background-position: 0% 50%; }
        50%  { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }

    /* ── Metric cards ── */
    div[data-testid="metric-container"] {
        background: linear-gradient(135deg, #1E2130, #252A40);
        border: 1px solid #6C63FF44;
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 4px 20px rgba(108, 99, 255, 0.15);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }

    div[data-testid="metric-container"]:hover {
        transform: translateY(-4px);
        box-shadow: 0 8px 30px rgba(108, 99, 255, 0.3);
    }

    div[data-testid="metric-container"] label {
        color: #A0AEC0 !important;
        font-size: 13px !important;
        font-weight: 600 !important;
        letter-spacing: 0.5px;
    }

    div[data-testid="metric-container"] [data-testid="stMetricValue"] {
        color: #FAFAFA !important;
        font-size: 26px !important;
        font-weight: 700 !important;
    }

    /* ── Sidebar ── */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #13152A 0%, #1A1D2E 100%);
        border-right: 1px solid #6C63FF33;
    }

    section[data-testid="stSidebar"] .stRadio label {
        color: #CBD5E0 !important;
        font-size: 15px !important;
        padding: 8px 0 !important;
    }

    /* ── Buttons ── */
    .stButton > button {
        background: linear-gradient(135deg, #6C63FF, #4ECDC4);
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 10px 24px !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 15px rgba(108, 99, 255, 0.3) !important;
    }

    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 25px rgba(108, 99, 255, 0.5) !important;
    }

    /* ── Primary button ── */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #6C63FF, #9B59B6) !important;
        font-size: 16px !important;
        padding: 14px 28px !important;
    }

    /* ── DataFrames ── */
    .stDataFrame {
        border-radius: 12px !important;
        overflow: hidden;
        border: 1px solid #6C63FF22 !important;
    }

    /* ── Headers ── */
    h1 {
        background: linear-gradient(135deg, #6C63FF, #4ECDC4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.5rem !important;
        font-weight: 800 !important;
        margin-bottom: 0.5rem !important;
    }

    h2, h3 {
        color: #CBD5E0 !important;
        font-weight: 700 !important;
    }

    /* ── Alert boxes ── */
    .success-box {
        background: linear-gradient(135deg, #0D4F3F, #0A3D2E);
        border-left: 4px solid #10B981;
        border-radius: 8px;
        padding: 14px 18px;
        margin: 8px 0;
        color: #6EE7B7;
        font-weight: 500;
    }

    .warning-box {
        background: linear-gradient(135deg, #4A3000, #3D2800);
        border-left: 4px solid #F59E0B;
        border-radius: 8px;
        padding: 14px 18px;
        margin: 8px 0;
        color: #FCD34D;
        font-weight: 500;
    }

    .danger-box {
        background: linear-gradient(135deg, #4A0000, #3D0000);
        border-left: 4px solid #EF4444;
        border-radius: 8px;
        padding: 14px 18px;
        margin: 8px 0;
        color: #FCA5A5;
        font-weight: 500;
    }

    .info-box {
        background: linear-gradient(135deg, #1A237E22, #1A237E11);
        border-left: 4px solid #6C63FF;
        border-radius: 8px;
        padding: 14px 18px;
        margin: 8px 0;
        color: #A5B4FC;
        font-weight: 500;
    }

    /* ── Progress bar ── */
    .stProgress > div > div {
        background: linear-gradient(90deg, #6C63FF, #4ECDC4) !important;
        border-radius: 10px !important;
    }

    /* ── Divider ── */
    hr {
        border: none !important;
        border-top: 1px solid #6C63FF33 !important;
        margin: 24px 0 !important;
    }

    /* ── Selectbox ── */
    .stSelectbox > div > div {
        background: #1E2130 !important;
        border: 1px solid #6C63FF44 !important;
        border-radius: 10px !important;
        color: #FAFAFA !important;
    }

    /* ── File uploader ── */
    .stFileUploader > div {
        background: #1E2130 !important;
        border: 2px dashed #6C63FF66 !important;
        border-radius: 16px !important;
        transition: border-color 0.3s ease !important;
    }

    .stFileUploader > div:hover {
        border-color: #6C63FF !important;
    }

    /* ── Spinner ── */
    .stSpinner > div {
        border-top-color: #6C63FF !important;
    }

    /* ── Checkbox ── */
    .stCheckbox > label > div[data-testid="stCheckbox"] {
        border-color: #6C63FF !important;
    }

    /* ── Tab styling ── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: #1E2130;
        padding: 8px;
        border-radius: 12px;
    }

    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: 8px;
        color: #A0AEC0;
        font-weight: 600;
        padding: 8px 16px;
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #6C63FF, #4ECDC4) !important;
        color: white !important;
    }

    /* ── Multiselect ── */
    .stMultiSelect > div {
        background: #1E2130 !important;
        border: 1px solid #6C63FF44 !important;
        border-radius: 10px !important;
    }

    /* ── Glowing card effect ── */
    .glow-card {
        background: linear-gradient(135deg, #1E2130, #252A40);
        border: 1px solid #6C63FF33;
        border-radius: 16px;
        padding: 20px;
        margin: 10px 0;
        box-shadow: 0 0 20px rgba(108, 99, 255, 0.1);
        transition: box-shadow 0.3s ease;
    }

    .glow-card:hover {
        box-shadow: 0 0 40px rgba(108, 99, 255, 0.25);
    }

    /* ── Pulse animation for anomaly badge ── */
    @keyframes pulse {
        0%   { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7); }
        70%  { box-shadow: 0 0 0 10px rgba(239, 68, 68, 0); }
        100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
    }

    .pulse-badge {
        display: inline-block;
        background: #EF4444;
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 13px;
        animation: pulse 2s infinite;
    }

    /* ── Fade in animation ── */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to   { opacity: 1; transform: translateY(0); }
    }

    .fade-in {
        animation: fadeIn 0.5s ease forwards;
    }
</style>
""", unsafe_allow_html=True)


# ── Sidebar ────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='text-align:center; padding: 20px 0;'>
        <div style='font-size: 3rem;'>💰</div>
        <h2 style='background: linear-gradient(135deg, #6C63FF, #4ECDC4);
                   -webkit-background-clip: text;
                   -webkit-text-fill-color: transparent;
                   font-weight: 800; margin: 8px 0;'>
            Expense AI
        </h2>
        <p style='color: #718096; font-size: 13px; margin: 0;'>
            Intelligent Financial Analytics
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    page = st.radio(
        "Navigation",
        options=[
            "📤 Upload Transactions",
            "📊 Dashboard",
            "🚨 Anomalies",
            "📈 Forecast",
        ],
        label_visibility="collapsed",
    )

    st.divider()

    st.markdown("### ⚡ Quick Actions")

    if st.button("🤖 Re-run ML Classifier", use_container_width=True):
        from app.ml.classifier import update_transactions_in_db
        with st.spinner("Running classifier..."):
            result = update_transactions_in_db()
        st.success(f"✅ Updated {result['updated']} transactions")

    if st.button("🔍 Re-run Anomaly Detection", use_container_width=True):
        from app.ml.anomaly import run_anomaly_detection
        with st.spinner("Detecting anomalies..."):
            result = run_anomaly_detection()
        st.success(f"🚨 Found {result['total_flagged']} anomalies")

    if st.button("📈 Re-run Forecast", use_container_width=True):
        from app.ml.forecaster import run_forecast
        with st.spinner("Forecasting..."):
            result = run_forecast()
        st.success("✅ Forecast updated!")

    if st.button("🗑️ Clear Cache", use_container_width=True):
        st.cache_data.clear()
        st.success("Cache cleared!")

    st.divider()

    st.markdown("""
    <div style='text-align:center; padding: 10px 0;'>
        <p style='color: #4A5568; font-size: 11px; margin: 0;'>
            Expense Intelligence System<br>
            <span style='color: #6C63FF;'>v2.0 Professional</span><br>
            Python · PostgreSQL · ML · AI
        </p>
    </div>
    """, unsafe_allow_html=True)


# ── Page Routing ────────────────────────────────────────
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if "Upload" in page:
    from pages.upload import show_upload_page
    show_upload_page()

elif "Dashboard" in page:
    from pages.dashboard import show_dashboard_page
    show_dashboard_page()

elif "Anomalies" in page:
    from pages.anomalies import show_anomalies_page
    show_anomalies_page()

elif "Forecast" in page:
    from pages.forecast import show_forecast_page
    show_forecast_page()