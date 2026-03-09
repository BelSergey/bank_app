
import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
import json
from src import main
from datetime import datetime


@patch("src.main.utils.read_excel")
@patch("builtins.input")
@patch("src.main.datetime")
def test_main_choose_mode_1(mock_datetime, mock_input, mock_read_excel):
    """Тест main с выбором режима 1 (текущая дата)."""
    # Фиксируем текущую дату
    mock_datetime.now.return_value = datetime(2025, 2, 25, 10, 0)

    # Создаём DataFrame с минимально необходимыми колонками
    mock_read_excel.return_value = pd.DataFrame({
        "Дата операции": [pd.Timestamp("2025-02-20")],
        "Номер карты": ["1234"],
        "Сумма операции": [-1000],
        "Сумма платежа": [-1000],
        "Категория": ["Еда"],
        "Описание": ["Покупка в супермаркете"]
    })
    mock_input.side_effect = ["1"]

    with patch("src.main.views.main_page") as mock_main_page, \
         patch("src.main.views.events_page") as mock_events_page, \
         patch("src.main.services.simple_search") as mock_search, \
         patch("src.main.reports.spending_by_category") as mock_report:

        # Возвращаем полный JSON от main_page
        mock_main_page.return_value = json.dumps({
            "greeting": "Доброе утро!",
            "cards": [],
            "top_transactions": [],
            "currencies": {},
            "stocks": {}
        })
        mock_events_page.return_value = '{"expenses": {"total": 0}}'
        mock_search.return_value = '[]'
        mock_report.return_value = '{}'

        # Запускаем main
        try:
            main.main()
        except SystemExit:
            pass

        assert mock_main_page.called
        assert mock_events_page.called