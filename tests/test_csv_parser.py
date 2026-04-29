# tests/test_csv_parser.py

import pytest
import pandas as pd
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ingestion.validator import (
    check_required_columns,
    parse_dates,
    clean_amount,
    clean_descriptions,
    validate_dataframe,
    ValidationError,
)


@pytest.fixture
def valid_df():
    return pd.DataFrame({
        "date":        ["15/01/2024", "16/01/2024", "17/01/2024"],
        "description": ["MCDONALDS LAHORE", "LESCO BILL", "UBER TRIP"],
        "amount":      ["850.00", "4200.00", "320.00"],
    })


@pytest.fixture
def messy_df():
    return pd.DataFrame({
        "date":        ["15/01/2024", "bad-date", "17/01/2024"],
        "description": ["  KFC BRANCH  ", "NETFLIX", ""],
        "amount":      ["Rs 1,234.50", "abc", "(500.00)"],
    })


class TestCheckRequiredColumns:

    def test_passes_with_all_columns(self, valid_df):
        check_required_columns(valid_df)

    def test_raises_when_date_missing(self, valid_df):
        df = valid_df.drop(columns=["date"])
        with pytest.raises(ValidationError) as exc_info:
            check_required_columns(df)
        assert "date" in str(exc_info.value)

    def test_raises_when_amount_missing(self, valid_df):
        df = valid_df.drop(columns=["amount"])
        with pytest.raises(ValidationError):
            check_required_columns(df)

    def test_raises_when_description_missing(self, valid_df):
        df = valid_df.drop(columns=["description"])
        with pytest.raises(ValidationError):
            check_required_columns(df)

    def test_raises_on_empty_dataframe(self):
        df = pd.DataFrame({"date": [], "description": [], "amount": []})
        with pytest.raises(ValidationError) as exc_info:
            check_required_columns(df)
        assert "no data" in str(exc_info.value).lower()


class TestParseDates:

    def test_parses_standard_format(self, valid_df):
        result, dropped = parse_dates(valid_df.copy())
        assert dropped == 0
        assert len(result) == 3

    def test_drops_invalid_dates(self):
        df = pd.DataFrame({
            "date":        ["15/01/2024", "not-a-date", "17/01/2024"],
            "description": ["A", "B", "C"],
            "amount":      [100, 200, 300],
        })
        result, dropped = parse_dates(df)
        assert dropped == 1
        assert len(result) == 2

    def test_handles_multiple_formats(self):
        df = pd.DataFrame({
            "date":        ["15/01/2024", "16/01/2024", "17/01/2024"],
            "description": ["A", "B", "C"],
            "amount":      [100, 200, 300],
        })
        result, dropped = parse_dates(df)
        assert dropped == 0
        assert len(result) == 3

    def test_returns_date_objects(self, valid_df):
        from datetime import date
        result, _ = parse_dates(valid_df.copy())
        assert isinstance(result["date"].iloc[0], date)


class TestCleanAmount:

    def test_removes_currency_symbol(self):
        df = pd.DataFrame({
            "date":        ["15/01/2024"],
            "description": ["TEST"],
            "amount":      ["Rs 1234.50"],
        })
        result, dropped = clean_amount(df)
        assert dropped == 0
        assert float(result["amount"].iloc[0]) == pytest.approx(1234.50)

    def test_removes_commas(self):
        df = pd.DataFrame({
            "date":        ["15/01/2024"],
            "description": ["TEST"],
            "amount":      ["1,234,567.89"],
        })
        result, dropped = clean_amount(df)
        assert float(result["amount"].iloc[0]) == pytest.approx(1234567.89)

    def test_handles_parentheses_as_negative(self):
        df = pd.DataFrame({
            "date":        ["15/01/2024"],
            "description": ["TEST"],
            "amount":      ["(500.00)"],
        })
        result, dropped = clean_amount(df)
        assert float(result["amount"].iloc[0]) == pytest.approx(500.00)

    def test_drops_invalid_amounts(self):
        df = pd.DataFrame({
            "date":        ["15/01/2024", "16/01/2024"],
            "description": ["VALID", "INVALID"],
            "amount":      ["1000.00", "abc"],
        })
        result, dropped = clean_amount(df)
        assert dropped == 1
        assert len(result) == 1

    def test_rounds_to_two_decimals(self):
        df = pd.DataFrame({
            "date":        ["15/01/2024"],
            "description": ["TEST"],
            "amount":      ["1234.5678"],
        })
        result, _ = clean_amount(df)
        assert float(result["amount"].iloc[0]) == pytest.approx(1234.57)


class TestCleanDescriptions:

    def test_strips_whitespace(self):
        df = pd.DataFrame({
            "date":        ["15/01/2024"],
            "description": ["  MCDONALDS LAHORE  "],
            "amount":      [850.0],
        })
        result, _ = clean_descriptions(df)
        assert result["description"].iloc[0] == "mcdonalds lahore"

    def test_converts_to_lowercase(self):
        df = pd.DataFrame({
            "date":        ["15/01/2024"],
            "description": ["LESCO ELECTRICITY BILL"],
            "amount":      [4200.0],
        })
        result, _ = clean_descriptions(df)
        assert result["description"].iloc[0] == "lesco electricity bill"

    def test_drops_empty_descriptions(self):
        df = pd.DataFrame({
            "date":        ["15/01/2024", "16/01/2024"],
            "description": ["VALID DESC", ""],
            "amount":      [850.0, 500.0],
        })
        result, dropped = clean_descriptions(df)
        assert dropped == 1
        assert len(result) == 1

    def test_collapses_multiple_spaces(self):
        df = pd.DataFrame({
            "date":        ["15/01/2024"],
            "description": ["KFC   GULBERG   BRANCH"],
            "amount":      [1150.0],
        })
        result, _ = clean_descriptions(df)
        assert "  " not in result["description"].iloc[0]


class TestValidateDataframe:

    def test_full_pipeline_clean_data(self, valid_df):
        result, report = validate_dataframe(valid_df.copy())
        assert len(result) == 3
        assert report["dropped_rows"] == 0
        assert report["clean_rows"] == 3

    def test_full_pipeline_messy_data(self, messy_df):
        result, report = validate_dataframe(messy_df.copy())
        assert report["dropped_rows"] > 0
        assert report["clean_rows"] < 3

    def test_report_structure(self, valid_df):
        _, report = validate_dataframe(valid_df.copy())
        required_keys = ["original_rows", "clean_rows", "dropped_rows", "drop_rate"]
        for key in required_keys:
            assert key in report, f"Missing key: {key}"