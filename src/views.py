import json
import logging
from datetime import datetime
from src import utils

logger = logging.getLogger(__name__)


def main_page(date_time_str: str = None) -> str:
    """Генерирует главной страницы. """
    if date_time_str is None:
        current_dt = datetime.now()
    else:
        current_dt = datetime.strptime(date_time_str, "%Y-%m-%d %H:%M:%S")

    logger.info(f"Запрос главной страницы для даты: {current_dt}")

    hour = current_dt.hour
    if 5 <= hour < 12:
        greeting = "Доброе утро!"
    elif 12 <= hour < 18:
        greeting = "Добрый день!"
    elif 18 <= hour < 23:
        greeting = "Добрый вечер!"
    else:
        greeting = "Доброй ночи!"
    print(greeting)
    transactions = utils.read_excel()

    start_of_month = utils.get_start_of_month(current_dt)
    filtered = utils.filter_transactions_by_date(transactions, start_of_month, current_dt)

    # Расходы по картам и кешбэк
    cards = {}
    for t in filtered:
        card_num = t.get('Номер карты', '')
        if not card_num or card_num == 0:
            continue
        amount = t.get('Сумма операции', 0)
        if amount < 0:
            abs_amount = abs(amount)
            if card_num not in cards:
                cards[card_num] = {'spent': 0, 'cashback': 0}
            cards[card_num]['spent'] += abs_amount
            cards[card_num]['cashback'] = cards[card_num]['spent'] // 100

    # Топ-5 транзакций по сумме платежа (по модулю)
    sorted_by_amount = sorted(filtered, key=lambda x: abs(x.get('Сумма платежа', 0)), reverse=True)
    top_transactions = sorted_by_amount[:5]

    # Пользовательские настройки
    settings = utils.load_user_settings()
    currencies = settings.get('user_currencies', [])
    stocks = settings.get('user_stocks', [])

    # Внешние API
    exchange_rates = utils.get_exchange_rates(currencies)
    stock_prices = utils.get_stock_prices(stocks)

    # Формирование JSON-ответа
    response = {
        "greeting": greeting,
        "cards": [
            {
                "last_digits": str(card),
                "total_spent": round(data['spent'], 2),
                "cashback": data['cashback']
            }
            for card, data in cards.items()
        ],
        "top_transactions": [
            {
                "date": t.get('Дата операции').strftime("%d.%m.%Y") if isinstance(t.get('Дата операции'),
                                                                                  datetime) else '',
                "amount": abs(t.get('Сумма платежа', 0)),
                "category": t.get('Категория', ''),
                "description": t.get('Описание', '')
            }
            for t in top_transactions
        ],
        "currencies": exchange_rates,
        "stocks": stock_prices
    }

    json_str = json.dumps(response, ensure_ascii=False, indent=2, default=str)
    logger.info("JSON для главной страницы сформирован")
    return json_str
