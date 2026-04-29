# tests/test_classifier.py

import pytest
import os
import sys
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ml.preprocess import clean_text, preprocess_series


class TestCleanText:

    def test_converts_to_lowercase(self):
        """Should convert uppercase to lowercase."""
        assert clean_text("MCDONALDS LAHORE") == "mcdonalds lahore"

    def test_removes_numbers(self):
        """Should strip reference numbers from descriptions."""
        result = clean_text("UBER TRIP REF123456")
        assert "123456" not in result
        assert "uber" in result

    def test_handles_empty_string(self):
        """Should return empty string for empty input."""
        assert clean_text("") == ""

    def test_handles_non_string(self):
        """Should return empty string for non-string input."""
        assert clean_text(None) == ""
        assert clean_text(123)  == ""

    def test_removes_special_characters(self):
        """Should strip special characters."""
        result = clean_text("KFC@GULBERG#BRANCH!")
        assert "@" not in result
        assert "#" not in result
        assert "!" not in result

    def test_collapses_whitespace(self):
        """Multiple spaces should become single space."""
        result = clean_text("KFC   LAHORE   DHA")
        assert "  " not in result


class TestPreprocessSeries:

    def test_processes_series(self):
        """Should apply clean_text to every element."""
        series = pd.Series([
            "MCDONALDS LAHORE",
            "LESCO ELECTRICITY BILL",
            "UBER TRIP PAYMENT",
        ])
        result = preprocess_series(series)
        assert len(result) == 3
        for text in result:
            assert text == text.lower()

    def test_handles_empty_series(self):
        """Should handle an empty Series without errors."""
        result = preprocess_series(pd.Series([], dtype=str))
        assert len(result) == 0


class TestModelIntegration:

    def test_model_file_exists(self):
        """Trained model file should exist after training."""
        model_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "models", "transaction_classifier.joblib"
        )
        assert os.path.exists(model_path), (
            "Model not found. Run train() in classifier.py first."
        )

    def test_predict_single_food(self):
        """Should predict Food & Dining for restaurant descriptions."""
        from app.ml.classifier import predict_single, load_model
        pipeline = load_model()
        result   = predict_single("MCDONALDS LAHORE DHA", pipeline)
        assert result["category"] == "Food & Dining"
        assert 0.0 <= result["confidence"] <= 1.0
        assert len(result["top3"]) == 3

    def test_predict_single_utilities(self):
        """Should predict Utilities for electricity bill."""
        from app.ml.classifier import predict_single, load_model
        pipeline = load_model()
        result   = predict_single("LESCO ELECTRICITY BILL", pipeline)
        assert result["category"] == "Utilities"

    def test_predict_batch_returns_dataframe(self):
        """Batch prediction should return DataFrame with correct columns."""
        from app.ml.classifier import predict_batch, load_model
        pipeline = load_model()
        descs    = pd.Series(["MCDONALDS", "LESCO BILL", "UBER TRIP"])
        result   = predict_batch(descs, pipeline)
        assert isinstance(result, pd.DataFrame)
        assert "predicted_category" in result.columns
        assert "confidence"         in result.columns
        assert len(result)          == 3