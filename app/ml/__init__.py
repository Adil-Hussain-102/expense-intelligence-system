# app/ml/__init__.py
# Machine Learning module — classifier, anomaly detector, forecaster

from app.ml.classifier import train, load_model, predict_single, predict_batch, update_transactions_in_db
from app.ml.anomaly import run_anomaly_detection, get_anomaly_summary
from app.ml.forecaster import run_forecast, get_forecast_summary
from app.ml.preprocess import clean_text, preprocess_series