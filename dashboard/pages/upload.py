# dashboard/pages/upload.py

import streamlit as st
import pandas as pd
import tempfile
import os
import io
from app.ingestion.validator import validate_dataframe, ValidationError
from app.ingestion.csv_parser import normalise_column_names, remove_duplicates, select_final_columns, save_to_database
from app.ml.classifier import update_transactions_in_db, load_model
from app.ml.anomaly import run_anomaly_detection
from app.ml.forecaster import run_forecast


def process_uploaded_file(uploaded_file):
    """
    Reads uploaded file directly from Streamlit memory
    without saving to disk — works from any location.
    """
    # Read file bytes directly from Streamlit uploader
    file_bytes = uploaded_file.getvalue()

    # Read into pandas directly from bytes
    df = pd.read_csv(io.BytesIO(file_bytes), encoding="utf-8-sig", on_bad_lines="skip")
    return df


def ingest_from_dataframe(df: pd.DataFrame) -> dict:
    """
    Runs the full ingestion pipeline on a DataFrame
    instead of a file path — fixes the upload issue.
    """
    from app.ingestion.validator import validate_dataframe
    from app.ingestion.csv_parser import (
        normalise_column_names,
        remove_duplicates,
        select_final_columns,
        save_to_database,
    )

    total_read = len(df)

    # Keep raw description
    if "description" in [col.strip().lower() for col in df.columns]:
        df_temp = df.copy()
        df_temp.columns = [col.strip().lower() for col in df_temp.columns]
        df["_raw_description"] = df_temp.get(
            "description",
            df_temp.get("narration",
            df_temp.get("particulars", ""))
        )

    # Normalise column names
    df = normalise_column_names(df)

    if "_raw_description" in df.columns:
        df["raw_text"] = df["_raw_description"]
        df = df.drop(columns=["_raw_description"])

    # Validate and clean
    df, validation_report = validate_dataframe(df)

    # Remove duplicates
    df, duplicates_removed = remove_duplicates(df)

    # Select final columns
    df = select_final_columns(df)
    records = df.to_dict("records")

    # Save to database
    db_result = {"inserted": 0, "skipped": 0}
    if len(records) > 0:
        db_result = save_to_database(records)

    return {
        "records":            records,
        "total_read":         total_read,
        "total_clean":        len(records),
        "total_dropped":      validation_report["dropped_rows"],
        "drop_rate":          validation_report["drop_rate"],
        "duplicates_removed": duplicates_removed,
        "db_inserted":        db_result["inserted"],
        "db_skipped":         db_result["skipped"],
    }


def show_upload_page():

    st.markdown("""
    <div class='fade-in'>
        <h1>📤 Upload Bank Statement</h1>
        <p style='color:#718096; font-size:16px; margin-bottom:24px;'>
            Upload any bank CSV from anywhere on your computer — our AI pipeline
            automatically cleans, categorizes, detects anomalies, and forecasts
            your spending in seconds.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ── Pipeline overview ─────────────────────────────
    st.markdown("""
    <div class='glow-card fade-in'>
        <h3 style='margin-top:0; color:#A5B4FC;'>🔄 AI Pipeline Overview</h3>
        <div style='display:flex; gap:12px; flex-wrap:wrap;'>
            <div style='flex:1; min-width:120px; text-align:center; padding:12px;
                        background:#252A40; border-radius:10px;'>
                <div style='font-size:1.8rem;'>📥</div>
                <div style='color:#6C63FF; font-weight:700; font-size:13px;'>STEP 1</div>
                <div style='color:#CBD5E0; font-size:12px;'>Ingest & Clean</div>
            </div>
            <div style='flex:1; min-width:120px; text-align:center; padding:12px;
                        background:#252A40; border-radius:10px;'>
                <div style='font-size:1.8rem;'>🤖</div>
                <div style='color:#4ECDC4; font-weight:700; font-size:13px;'>STEP 2</div>
                <div style='color:#CBD5E0; font-size:12px;'>ML Categorize</div>
            </div>
            <div style='flex:1; min-width:120px; text-align:center; padding:12px;
                        background:#252A40; border-radius:10px;'>
                <div style='font-size:1.8rem;'>🔍</div>
                <div style='color:#F59E0B; font-weight:700; font-size:13px;'>STEP 3</div>
                <div style='color:#CBD5E0; font-size:12px;'>Detect Anomalies</div>
            </div>
            <div style='flex:1; min-width:120px; text-align:center; padding:12px;
                        background:#252A40; border-radius:10px;'>
                <div style='font-size:1.8rem;'>📈</div>
                <div style='color:#10B981; font-weight:700; font-size:13px;'>STEP 4</div>
                <div style='color:#CBD5E0; font-size:12px;'>Update Forecast</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # ── File uploader ─────────────────────────────────
    uploaded_file = st.file_uploader(
        "Drop your CSV bank statement here — from anywhere on your computer",
        type=["csv"],
        help="Works with any CSV file from Desktop, Downloads, or any folder",
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        run_classifier = st.checkbox("🤖 ML Categorization", value=True)
    with col2:
        run_anomaly    = st.checkbox("🔍 Anomaly Detection", value=True)
    with col3:
        run_fc         = st.checkbox("📈 Update Forecast",   value=True)

    if uploaded_file is not None:

        # ── File info ─────────────────────────────────
        st.markdown(f"""
        <div class='info-box'>
            📁 <b>File loaded:</b> {uploaded_file.name} ·
            Size: {uploaded_file.size / 1024:.1f} KB ·
            Ready to process!
        </div>
        """, unsafe_allow_html=True)

        # ── Preview ───────────────────────────────────
        try:
            preview_df = pd.read_csv(
                io.BytesIO(uploaded_file.getvalue()),
                encoding="utf-8-sig"
            )
            st.markdown("### 👁️ File Preview")
            st.dataframe(preview_df.head(5), use_container_width=True)

            col1, col2, col3 = st.columns(3)
            col1.metric("📄 Total Rows",  len(preview_df))
            col2.metric("📋 Columns",     len(preview_df.columns))
            col3.metric("📁 File",        uploaded_file.name)

        except Exception as e:
            st.error(f"Could not preview file: {e}")
            return

        st.divider()

        if st.button("🚀 Launch AI Pipeline", type="primary", use_container_width=True):

            progress = st.progress(0, text="🚀 Launching AI pipeline...")
            status   = st.empty()

            try:
                # ── Step 1: Ingest ─────────────────────
                status.markdown("""
                <div class='info-box'>
                    📥 <b>Step 1/4</b> — Reading and cleaning CSV data...
                </div>
                """, unsafe_allow_html=True)

                # Read file fresh for processing
                df = pd.read_csv(
                    io.BytesIO(uploaded_file.getvalue()),
                    encoding="utf-8-sig",
                    on_bad_lines="skip"
                )

                result = ingest_from_dataframe(df)

                progress.progress(25, text="✅ Step 1 complete")
                status.markdown(f"""
                <div class='success-box'>
                    ✅ <b>Step 1 Complete</b> — CSV ingested successfully!
                </div>
                """, unsafe_allow_html=True)

                col1, col2, col3, col4 = st.columns(4)
                col1.metric("📄 Rows Read",      result["total_read"])
                col2.metric("✅ Clean Rows",      result["total_clean"])
                col3.metric("🗑️ Dropped",         result["total_dropped"])
                col4.metric("💾 New in Database", result["db_inserted"])

                if result["db_inserted"] == 0:
                    st.markdown("""
                    <div class='warning-box'>
                        ⚠️ <b>No new transactions inserted.</b>
                        These transactions may already exist in the database
                        (duplicate detection working correctly).
                        Try uploading a different CSV file with new transactions.
                    </div>
                    """, unsafe_allow_html=True)

                # ── Step 2: Classify ───────────────────
                if run_classifier:
                    status.markdown("""
                    <div class='info-box'>
                        🤖 <b>Step 2/4</b> — Running ML classifier...
                    </div>
                    """, unsafe_allow_html=True)

                    try:
                        pipeline   = load_model()
                        clf_result = update_transactions_in_db(pipeline)
                        progress.progress(50, text="✅ Step 2 complete")
                        status.markdown(f"""
                        <div class='success-box'>
                            🤖 <b>Step 2 Complete</b> — {clf_result['updated']} transactions categorized!
                        </div>
                        """, unsafe_allow_html=True)
                    except FileNotFoundError:
                        st.warning("⚠️ ML model not found. Train the model first.")

                # ── Step 3: Anomaly ────────────────────
                if run_anomaly:
                    status.markdown("""
                    <div class='info-box'>
                        🔍 <b>Step 3/4</b> — Running anomaly detection...
                    </div>
                    """, unsafe_allow_html=True)

                    anom_result = run_anomaly_detection()
                    progress.progress(75, text="✅ Step 3 complete")

                    if anom_result["total_flagged"] > 0:
                        status.markdown(f"""
                        <div class='danger-box'>
                            🚨 <b>Step 3 Complete</b> —
                            {anom_result['total_flagged']} anomalies detected!
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        status.markdown("""
                        <div class='success-box'>
                            ✅ <b>Step 3 Complete</b> — No anomalies detected!
                        </div>
                        """, unsafe_allow_html=True)

                # ── Step 4: Forecast ───────────────────
                if run_fc:
                    status.markdown("""
                    <div class='info-box'>
                        📈 <b>Step 4/4</b> — Updating spending forecast...
                    </div>
                    """, unsafe_allow_html=True)

                    fc_result = run_forecast(save_to_db=True)
                    progress.progress(100, text="✅ All steps complete!")
                    status.markdown(f"""
                    <div class='success-box'>
                        📈 <b>Step 4 Complete</b> — Forecast updated!
                        Next month predicted: <b>Rs {fc_result['total_predicted']:,.0f}</b>
                    </div>
                    """, unsafe_allow_html=True)

                # ── Success ────────────────────────────
                st.markdown("""
                <div class='glow-card' style='text-align:center; margin-top:20px;'>
                    <div style='font-size:3rem;'>🎉</div>
                    <h2 style='color:#10B981; margin:8px 0;'>Pipeline Complete!</h2>
                    <p style='color:#718096;'>
                        Go to <b style='color:#6C63FF;'>Dashboard</b> to see updated analytics,
                        <b style='color:#F59E0B;'>Anomalies</b> for flagged transactions,
                        or <b style='color:#10B981;'>Forecast</b> for next month predictions.
                    </p>
                </div>
                """, unsafe_allow_html=True)

                st.balloons()
                st.cache_data.clear()
                st.session_state["refresh_dashboard"] += 1
                st.success("🎉 Done! Go to Dashboard and click Refresh to see updated data.")

            except Exception as e:
                st.error(f"❌ Pipeline failed: {str(e)}")
                st.exception(e)

    else:
        # ── Empty state ───────────────────────────────
        st.markdown("""
        <div class='glow-card' style='text-align:center; padding:40px;'>
            <div style='font-size:4rem; margin-bottom:16px;'>📂</div>
            <h3 style='color:#A5B4FC;'>No file selected</h3>
            <p style='color:#718096;'>
                Upload any CSV bank statement from anywhere on your computer
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("### 📋 Supported CSV Format")
        sample = pd.DataFrame({
            "Transaction Date": ["15/01/2024", "16/01/2024", "17/01/2024"],
            "Description":      ["MCDONALDS LAHORE DHA", "SALARY CREDIT", "LESCO BILL"],
            "Amount":           ["850.00", "95000.00", "4200.50"],
            "Type":             ["Debit", "Credit", "Debit"],
        })
        st.dataframe(sample, use_container_width=True)

        st.markdown("""
        <div class='info-box'>
            💡 <b>Tips:</b><br>
            ✅ Works with CSV files from Desktop, Downloads, or any folder<br>
            ✅ Column names are flexible (Transaction Date, Date, DT etc.)<br>
            ✅ Amounts can include Rs prefix, commas, parentheses<br>
            ✅ Duplicate rows are automatically detected and removed<br>
            ✅ Supports DD/MM/YYYY, YYYY-MM-DD, and other date formats
        </div>
        """, unsafe_allow_html=True)