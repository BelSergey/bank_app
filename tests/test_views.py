import pytest
import json
import pandas as pd
from datetime import datetime
from unittest.mock import patch
from src import views


def test_main_page_greeting():
    result_json = views.main_page(pd.DataFrame(), "2025-02-25 10:00:00")
    result = json.loads(result_json)
    assert result["greeting"] == "Доброе утро!"


def test_main_page_cards(sample_transactions_df):
    """Тест агрегации по картам."""
    result_json = views.main_page(sample_transactions_df, "2025-02-20 12:00:00")
    result = json.loads(result_json)
    # за период с 01.02 по 20.02 попадают две транзакции по карте 5678: 5000 (доход) и -1200 (расход)
    # cards считает только расходы (отрицательные суммы)
    cards = result["cards"]
    # ожидаем одну карту 5678 с расходом 1200, кешбэк 12
    assert len(cards) == 1
    assert cards[0]["last_digits"] == "5678"
    assert cards[0]["total_spent"] == 1200.0
    assert cards[0]["cashback"] == 12


def test_main_page_top_transactions(sample_transactions_df):
    result_json = views.main_page(sample_transactions_df, "2025-02-20 12:00:00")
    result = json.loads(result_json)
    top = result["top_transactions"]
    assert len(top) == 2   # только февраль


@patch("src.views.utils.get_exchange_rates")
@patch("src.views.utils.get_stock_prices")
def test_events_page(mock_stocks, mock_rates, sample_transactions_df, sample_user_settings):
    """Тест страницы событий."""
    mock_rates.return_value = {"USD": 90.0, "EUR": 100.0}
    mock_stocks.return_value = {"AAPL": 150.0, "GOOGL": 2500.0}
    with patch("src.views.utils.load_user_settings", return_value=sample_user_settings):
        result_json = views.events_page(sample_transactions_df, "2025-02-25")
        result = json.loads(result_json)
        assert "expenses" in result
        assert result["expenses"]["total"] > 0
        assert len(result["currency_rates"]) == 2
        assert len(result["stock_prices"]) == 2


def test_events_page_process_transactions():
    """Тест внутренней функции process_transactions через вызов events_page."""
    # Создаём простой DF
    data = {
        "Дата операции": [datetime(2025, 2, 1), datetime(2025, 2, 2)],
        "Сумма операции": [-100, 500],
        "Категория": ["Еда", "Зарплата"],
    }
    df = pd.DataFrame(data)
    result_json = views.events_page(df, "2025-02-25", period="M")
    result = json.loads(result_json)
    assert result["expenses"]["total"] == 100
    assert result["income"]["total"] == 500
    assert len(result["expenses"]["main"]) == 1
    assert result["expenses"]["main"][0]["category"] == "Еда"

def test_main_page_empty_dataframe():
    """Тест главной страницы с пустым DataFrame."""
    empty_df = pd.DataFrame()
    result_json = views.main_page(empty_df, "2025-02-25 10:00:00")
    result = json.loads(result_json)
    assert result["greeting"] == "Доброе утро!"  # зависит от времени
    assert result["cards"] == []
    assert result["top_transactions"] == []
    assert "currencies" in result
    assert "stocks" in result


def test_main_page_no_transactions_in_period(sample_transactions_df):
    """Тест, когда за период нет транзакций."""
    # Дата, после всех транзакций
    result_json = views.main_page(sample_transactions_df, "2025-03-01 12:00:00")
    result = json.loads(result_json)
    assert result["cards"] == []
    assert result["top_transactions"] == []


def test_events_page_empty_dataframe():
    """Тест страницы событий с пустым DataFrame."""
    empty_df = pd.DataFrame()
    result_json = views.events_page(empty_df, "2025-02-25")
    result = json.loads(result_json)
    assert result["expenses"]["total"] == 0
    assert result["expenses"]["main"] == []
    assert result["income"]["total"] == 0
    assert result["income"]["main"] == []


def test_events_page_no_transactions_in_period(sample_transactions_df):
    """Тест страницы событий, когда за период нет транзакций."""
    result_json = views.events_page(sample_transactions_df, "2025-03-01", period="M")
    result = json.loads(result_json)
    assert result["expenses"]["total"] == 0
    assert result["income"]["total"] == 0


def test_events_page_different_periods(sample_transactions_df):
    """Тест различных периодов (Y, W, ALL)."""
    # Период год
    result_json = views.events_page(sample_transactions_df, "2025-02-25", period="Y")
    result = json.loads(result_json)
    assert result["expenses"]["total"] > 0  # должны быть все транзакции за 2025

    # Период неделя
    result_json = views.events_page(sample_transactions_df, "2025-02-20", period="W")
    result = json.loads(result_json)
    # Должны попасть транзакции с 17.02 по 20.02 (в наборе данных есть 20.02)
    assert result["expenses"]["total"] == 1200  # только перевод

    # Период ALL
    result_json = views.events_page(sample_transactions_df, "2025-02-25", period="ALL")
    result = json.loads(result_json)
    assert result["expenses"]["total"] == 2900  # -1500-200-1200 = 2900


@patch("src.views.utils.get_exchange_rates")
@patch("src.views.utils.get_stock_prices")
def test_events_page_empty_rates_and_prices(mock_stocks, mock_rates, sample_transactions_df):
    """Тест, когда курсы валют и цены акций не получены."""
    mock_rates.return_value = {}
    mock_stocks.return_value = {}
    with patch("src.views.utils.load_user_settings", return_value={"user_currencies": ["USD"], "user_stocks": ["AAPL"]}):
        result_json = views.events_page(sample_transactions_df, "2025-02-25")
        result = json.loads(result_json)
        assert result["currency_rates"] == []
        assert result["stock_prices"] == []


def test_main_page_cards_no_transactions():
    """Тест обработки карт, когда нет расходов."""
    df = pd.DataFrame({
        "Дата операции": [datetime(2025, 2, 1)],
        "Номер карты": ["1234"],
        "Сумма операции": [500],  # доход, не расход
        "Сумма платежа": [500],
        "Категория": ["Зарплата"],
        "Описание": ["Зарплата"]
    })
    result_json = views.main_page(df, "2025-02-25 12:00:00")
    result = json.loads(result_json)
    # Карты не должны появиться, т.к. сумма операции положительная
    assert result["cards"] == []

def test_events_page_with_only_income():
    """Тест страницы событий только с доходами."""
    df = pd.DataFrame({
        "Дата операции": [datetime(2025, 2, 1)],
        "Сумма операции": [1000],
        "Категория": ["Зарплата"]
    })
    result_json = views.events_page(df, "2025-02-25")
    result = json.loads(result_json)
    assert result["expenses"]["total"] == 0
    assert result["income"]["total"] == 1000


def test_events_page_with_only_expenses():
    """Тест страницы событий только с расходами."""
    df = pd.DataFrame({
        "Дата операции": [datetime(2025, 2, 1)],
        "Сумма операции": [-500],
        "Категория": ["Еда"]
    })
    result_json = views.events_page(df, "2025-02-25")
    result = json.loads(result_json)
    assert result["expenses"]["total"] == 500
    assert result["income"]["total"] == 0


def test_main_page_with_income_only():
    """Тест главной страницы, где есть только доходы (карты не создаются)."""
    df = pd.DataFrame({
        "Дата операции": [datetime(2025, 2, 1)],
        "Номер карты": ["1234"],
        "Сумма операции": [1000],
        "Сумма платежа": [1000],
        "Категория": ["Зарплата"],
        "Описание": ["Зарплата"]
    })
    result_json = views.main_page(df, "2025-02-25 12:00:00")
    result = json.loads(result_json)
    assert result["cards"] == []  # доходы не учитываются