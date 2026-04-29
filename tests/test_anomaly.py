# tests/test_anomaly.py

import pytest
import pandas as pd
import numpy as np
import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ml.anomaly import zscore_detection, merge_anomaly_results


@pytest.fixture
def sample_df():
    """DataFrame with obvious outliers for testing Z-score."""
    rows = []
    for i in range(20):
        rows.append({
            "id":          i,
            "date":        pd.Timestamp("2024-01-15"),
            "amount":      900 + (i * 10),
            "category":    "Food & Dining",
            "description": f"RESTAURANT {i}",
            "is_anomaly":  False,
            "amount_log":  np.log1p(900 + i * 10),
            "day_of_week":  1,
            "day_of_month": 15,
            "month":        1,
        })
    rows.append({
        "id":          99,
        "date":        pd.Timestamp("2024-01-20"),
        "amount":      85000,
        "category":    "Food & Dining",
        "description": "SUSPICIOUS LARGE FOOD PURCHASE",
        "is_anomaly":  False,
        "amount_log":  np.log1p(85000),
        "day_of_week":  1,
        "day_of_month": 20,
        "month":        1,
    })
    return pd.DataFrame(rows)


class TestZscoreDetection:

    def test_detects_obvious_outlier(self, sample_df):
        """Z-score should flag the Rs 85,000 transaction."""
        anomalies   = zscore_detection(sample_df, threshold=2.5)
        flagged_ids = [a["transaction_id"] for a in anomalies]
        assert 99 in flagged_ids

    def test_does_not_flag_normal_transactions(self, sample_df):
        """Normal transactions around Rs 1000 should not be flagged."""
        anomalies   = zscore_detection(sample_df, threshold=2.5)
        flagged_ids = [a["transaction_id"] for a in anomalies]
        normal_ids  = list(range(20))
        for nid in normal_ids:
            assert nid not in flagged_ids

    def test_returns_severity(self, sample_df):
        """Each anomaly should have a severity field."""
        anomalies = zscore_detection(sample_df, threshold=2.5)
        for a in anomalies:
            assert a["severity"] in ("low", "medium", "high")

    def test_returns_reason_string(self, sample_df):
        """Each anomaly should have a human-readable reason."""
        anomalies = zscore_detection(sample_df, threshold=2.5)
        for a in anomalies:
            assert isinstance(a["reason"], str)
            assert len(a["reason"]) > 10

    def test_skips_category_with_few_transactions(self):
        """Should skip categories with fewer than 3 transactions."""
        df = pd.DataFrame({
            "id":          [1, 2],
            "amount":      [100, 50000],
            "category":    ["Food & Dining", "Food & Dining"],
            "date":        [pd.Timestamp("2024-01-01")] * 2,
            "description": ["A", "B"],
            "is_anomaly":  [False, False],
        })
        result = zscore_detection(df)
        assert result == []


class TestMergeAnomalyResults:

    def test_merges_unique_anomalies(self):
        """Different transaction IDs should all appear in merged result."""
        zscore  = [{"transaction_id": 1, "method": "zscore",
                    "severity": "low",    "reason": "Z-score test"}]
        iforest = [{"transaction_id": 2, "method": "isolation_forest",
                    "severity": "medium", "reason": "IF test"}]
        merged  = merge_anomaly_results(zscore, iforest)
        ids     = [m["transaction_id"] for m in merged]
        assert 1 in ids
        assert 2 in ids

    def test_upgrades_severity_when_both_methods_agree(self):
        """Transaction flagged by BOTH methods should be upgraded to high."""
        zscore  = [{"transaction_id": 5, "method": "zscore",
                    "severity": "low",    "reason": "Z reason"}]
        iforest = [{"transaction_id": 5, "method": "isolation_forest",
                    "severity": "medium", "reason": "IF reason"}]
        merged  = merge_anomaly_results(zscore, iforest)
        assert len(merged)           == 1
        assert merged[0]["severity"] == "high"
        assert merged[0]["method"]   == "both"