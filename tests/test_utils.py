import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from datetime import datetime
from src import utils


def test_read_excel_success(tmp_path):
    """Тест успешного чтения Excel-файла."""
    # Создаём временный Excel-файл
    df_test = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
    file_path = tmp_path / "test.xlsx"
    df_test.to_excel(file_path, index=False)

    result = utils.read_excel(str(file_path))
    assert not result.empty
    assert list(result.columns) == ["A", "B"]


@patch("src.utils.pd.read_excel")
def test_read_excel_file_not_found(mock_read_excel):
    """Тест обработки FileNotFoundError."""
    mock_read_excel.side_effect = FileNotFoundError
    result = utils.read_excel("nonexistent.xlsx")
    assert result.empty


def test_get_start_of_month():
    """Тест получения начала месяца."""
    date = datetime(2025, 5, 15)
    start = utils.get_start_of_month(date)
    assert start == datetime(2025, 5, 1)


@pytest.mark.parametrize(
    "period, expected_start_day",
    [
        ("M", 1),
        ("Y", 1),
        ("W", 16),  # для даты 2025-02-19 (среда) начало недели понедельник 17.02.2025
    ],
)
def test_get_date_range(period, expected_start_day):
    """Параметризованный тест get_date_range."""
    date_str = "2025-02-19"
    start, end = utils.get_date_range(date_str, period)
    assert end == datetime(2025, 2, 19)
    if period == "M":
        assert start == datetime(2025, 2, 1)
    elif period == "Y":
        assert start == datetime(2025, 1, 1)
    elif period == "W":
        # 2025-02-19 среда, начало недели понедельник 2025-02-17
        assert start == datetime(2025, 2, 17)


def test_filter_transactions_by_date(sample_transactions_df):
    """Тест фильтрации по датам."""
    start = datetime(2025, 1, 1)
    end = datetime(2025, 1, 31)
    filtered = utils.filter_transactions_by_date(sample_transactions_df, start, end)
    assert len(filtered) == 2
    assert all(filtered["Дата операции"].dt.month == 1)


@patch("src.utils.requests.get")
def test_get_exchange_rates_success(mock_get):
    """Тест успешного получения курсов валют."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "Valute": {
            "USD": {"Value": 90.5},
            "EUR": {"Value": 100.2},
        }
    }
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    rates = utils.get_exchange_rates(["USD", "EUR", "RUB"])
    assert rates == {"USD": 90.5, "EUR": 100.2, "RUB": 1.0}


@patch("src.utils.requests.get")
def test_get_exchange_rates_failure(mock_get):
    """Тест обработки ошибки при запросе курсов."""
    mock_get.side_effect = Exception("Network error")
    rates = utils.get_exchange_rates(["USD"])
    assert rates == {}


@patch("src.utils.yf.download")
def test_get_stock_prices_success(mock_download):
    import pandas as pd
    dates = pd.date_range("2025-02-25", periods=1)
    columns = pd.MultiIndex.from_tuples([('AAPL', 'Close'), ('GOOGL', 'Close')])
    df = pd.DataFrame([[150.0, 2500.0]], index=dates, columns=columns)
    mock_download.return_value = df
    prices = utils.get_stock_prices(["AAPL", "GOOGL"])
    assert prices == {"AAPL": 150.0, "GOOGL": 2500.0}


def test_load_user_settings_file_not_found():
    """Тест загрузки настроек при отсутствии файла."""
    with patch("builtins.open", side_effect=FileNotFoundError):
        settings = utils.load_user_settings()
        assert settings == {"user_currencies": ["USD", "EUR"], "user_stocks": ["AAPL", "AMZN", "GOOGL", "MSFT", "TSLA"]}


def test_get_top_transactions_by_card(sample_transactions_df):
    """Тест получения топ-транзакций по карте."""
    top = utils.get_top_transactions_by_card(sample_transactions_df, "1234", limit=2)
    assert len(top) == 2
    assert top[0]["amount"] == 1500.0  # самая большая по модулю
    assert top[1]["amount"] == 200.0


def test_print_functions(capsys):
    """Тест функций вывода (просто проверяем, что не падают)."""
    utils.print_section("Test")
    captured = capsys.readouterr()
    assert "Test" in captured.out

    utils.print_cards([{"last_digits": "1234", "total_spent": 100, "cashback": 1}])
    captured = capsys.readouterr()
    assert "1234" in captured.out

def test_get_date_range_invalid_period():
        """Тест обработки неизвестного периода."""
        with pytest.raises(ValueError, match="Неизвестный период: INVALID"):
            utils.get_date_range("2025-02-25", "INVALID")

def test_filter_transactions_by_date_empty_df():
        """Тест фильтрации пустого DataFrame."""
        empty_df = pd.DataFrame()
        result = utils.filter_transactions_by_date(empty_df, datetime.now(), datetime.now())
        assert result.empty

def test_get_exchange_rates_partial_success():
        """Тест, когда одна валюта есть, другой нет."""
        with patch("src.utils.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "Valute": {
                    "USD": {"Value": 90.5},
                }
            }
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            rates = utils.get_exchange_rates(["USD", "EUR"])
            assert rates == {"USD": 90.5}  # EUR не будет добавлен
            # Проверяем, что было предупреждение (можно проверить через caplog)
            # Но для покрытия достаточно, что функция вернула словарь без EUR

def test_get_stock_prices_single_ticker():
        """Тест получения цены для одного тикера."""
        with patch("src.utils.yf.download") as mock_download:
            import pandas as pd
            # Для одного тикера yfinance возвращает Series
            dates = pd.date_range("2025-02-25", periods=1)
            series = pd.Series([150.0], index=dates, name="Close")
            mock_download.return_value = series

            prices = utils.get_stock_prices(["AAPL"])
            assert prices == {"AAPL": 150.0}

def test_get_stock_prices_empty_data():
        """Тест, когда yfinance возвращает пустой DataFrame."""
        with patch("src.utils.yf.download") as mock_download:
            empty_df = pd.DataFrame()
            mock_download.return_value = empty_df

            prices = utils.get_stock_prices(["AAPL"])
            assert prices == {}

def test_print_cards_empty(capsys):
        """Тест вывода пустого списка карт."""
        utils.print_cards([])
        captured = capsys.readouterr()
        assert "Нет данных по картам" in captured.out

def test_print_top_transactions_empty(capsys):
        """Тест вывода пустого списка транзакций."""
        utils.print_top_transactions([])
        captured = capsys.readouterr()
        assert "Нет транзакций" in captured.out

def test_print_currency_rates_empty(capsys):
        """Тест вывода пустого словаря курсов."""
        utils.print_currency_rates({})
        captured = capsys.readouterr()
        assert "Курсы валют не получены" in captured.out

def test_print_stock_prices_empty(capsys):
        """Тест вывода пустого словаря цен акций."""
        utils.print_stock_prices({})
        captured = capsys.readouterr()
        assert "Цены акций не получены" in captured.out

def test_print_categories_empty(capsys):
        """Тест вывода пустого списка категорий."""
        utils.print_categories([], "Тест")
        captured = capsys.readouterr()
        assert "Тест: нет данных" in captured.out

def test_get_top_transactions_by_card_empty_df():
        """Тест для пустого DataFrame."""
        empty_df = pd.DataFrame()
        result = utils.get_top_transactions_by_card(empty_df, "1234")
        assert result == []

def test_get_top_transactions_by_card_no_card():
        """Тест для карты, которой нет в данных."""
        df = pd.DataFrame({"Номер карты": ["5678"], "Сумма платежа": [100]})
        result = utils.get_top_transactions_by_card(df, "1234")
        assert result == []

def test_read_excel_other_exception():
        """Тест обработки исключения, отличного от FileNotFoundError."""
        with patch("src.utils.pd.read_excel") as mock_read:
            mock_read.side_effect = Exception("Some error")
            result = utils.read_excel("some.xlsx")
            assert result.empty

def test_load_user_settings_success(tmp_path):
        """Тест успешной загрузки user_settings.json."""
        settings_content = '{"user_currencies": ["USD"], "user_stocks": ["AAPL"]}'
        settings_file = tmp_path / "user_settings.json"
        settings_file.write_text(settings_content, encoding="utf-8")

        with patch("src.utils.BASE_DIR", tmp_path):
            settings = utils.load_user_settings()
            assert settings == {"user_currencies": ["USD"], "user_stocks": ["AAPL"]}

def test_get_exchange_rates_connection_error():
    """Тест ошибки соединения при получении курсов."""
    with patch("src.utils.requests.get", side_effect=Exception("Connection error")):
        rates = utils.get_exchange_rates(["USD"])
        assert rates == {}


def test_get_stock_prices_exception():
    """Тест исключения в get_stock_prices."""
    with patch("src.utils.yf.download", side_effect=Exception("YF error")):
        prices = utils.get_stock_prices(["AAPL"])
        assert prices == {}


def test_get_top_transactions_by_card_with_nan_date():
    """Тест обработки NaN в дате операции."""
    df = pd.DataFrame({
        "Номер карты": ["1234"],
        "Сумма платежа": [100],
        "Дата операции": [pd.NaT],
        "Категория": ["Test"],
        "Описание": ["Test"]
    })
    result = utils.get_top_transactions_by_card(df, "1234")
    assert len(result) == 1
    assert result[0]["date"] == ""


def test_print_categories_with_mixed_keys(capsys):
    """Тест print_categories с разными ключами."""
    cat_list = [
        {"category": "Еда", "amount": 100},
        {"Категория": "Транспорт", "Сумма операции": 200}
    ]
    utils.print_categories(cat_list, "Тест")
    captured = capsys.readouterr()
    assert "Еда: 100 руб" in captured.out
    assert "Транспорт: 200 руб" in captured.out