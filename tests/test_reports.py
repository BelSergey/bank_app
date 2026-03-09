import pytest
import json
import pandas as pd
from datetime import datetime
from unittest.mock import patch
from src import reports


def test_spending_by_category(sample_transactions_df):
    with patch("src.reports.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2025, 2, 25)
        result_json = reports.spending_by_category(sample_transactions_df, "Супермаркеты", date="2025-02-25")
        result = json.loads(result_json)
        assert result["category"] == "Супермаркеты"
        assert "2024-11-25" in result["period"]
        assert "2025-02-25" in result["period"]


def test_spending_by_category_no_data():
    """Тест, когда нет транзакций по категории."""
    empty_df = pd.DataFrame(columns=["Дата операции", "Категория", "Сумма операции"])
    result_json = reports.spending_by_category(empty_df, "Супермаркеты", date="2025-02-25")
    result = json.loads(result_json)
    assert result == {}


def test_spending_by_category_with_default_date(sample_transactions_df):
    with patch("src.reports.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2025, 2, 25)
        result_json = reports.spending_by_category(sample_transactions_df, "Супермаркеты")
        result = json.loads(result_json)
        assert "2024-11-25" in result["period"]
        assert "2025-02-25" in result["period"]


def test_report_to_file_decorator(tmp_path):
    """Тест декоратора report_to_file."""
    @reports.report_to_file(filename=str(tmp_path / "test.json"))
    def dummy_report():
        return json.dumps({"key": "value"})

    result = dummy_report()
    assert result == '{"key": "value"}'
    assert (tmp_path / "test.json").exists()