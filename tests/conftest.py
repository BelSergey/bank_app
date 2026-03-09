import pytest
import pandas as pd
from datetime import datetime


@pytest.fixture
def sample_transactions_df():
    """Возвращает DataFrame с тестовыми транзакциями."""
    data = {
        "Дата операции": [
            datetime(2025, 1, 5),
            datetime(2025, 1, 10),
            datetime(2025, 2, 15),
            datetime(2025, 2, 20),
        ],
        "Дата платежа": [
            datetime(2025, 1, 5),
            datetime(2025, 1, 10),
            datetime(2025, 2, 15),
            datetime(2025, 2, 20),
        ],
        "Номер карты": ["1234", "1234", "5678", "5678"],
        "Сумма операции": [-1500.0, -200.0, 5000.0, -1200.0],
        "Сумма платежа": [-1500.0, -200.0, 5000.0, -1200.0],
        "Категория": ["Супермаркеты", "Фастфуд", "Зарплата", "Переводы"],
        "Описание": ["Пятёрочка", "Бургерная", "Зарплата", "Перевод другу"],
    }
    df = pd.DataFrame(data)
    return df


@pytest.fixture
def sample_user_settings():
    """Возвращает тестовые настройки пользователя."""
    return {"user_currencies": ["USD", "EUR"], "user_stocks": ["AAPL", "GOOGL"]}