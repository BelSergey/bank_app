import pytest
import json
from src import services


def test_simple_search_found():
    transactions = [
        {"Описание": "Покупка в супермаркете", "Категория": "Еда"},
        {"Описание": "Перевод другу", "Категория": "Переводы"},
        {"Описание": "Оплата связи", "Категория": "Связь"},
    ]
    result_json = services.simple_search("перевод", transactions)
    result = json.loads(result_json)
    assert len(result) == 1   # только вторая транзакция


def test_simple_search_not_found():
    """Тест когда ничего не найдено."""
    transactions = [{"Описание": "Покупка", "Категория": "Еда"}]
    result_json = services.simple_search("nonexistent", transactions)
    result = json.loads(result_json)
    assert result == []


@pytest.mark.parametrize(
    "search_str,expected_count",
    [
        ("покупка", 1),
        ("перевод", 1),
        ("", 2),  # пустая строка найдёт всё? В текущей реализации пустая строка не совпадает ни с чем.
    ],
)
def test_simple_search_parametrized(search_str, expected_count):
    """Параметризованный тест поиска."""
    transactions = [
        {"Описание": "Покупка", "Категория": "Еда"},
        {"Описание": "Перевод", "Категория": "Переводы"},
    ]
    result_json = services.simple_search(search_str, transactions)
    result = json.loads(result_json)
    assert len(result) == expected_count