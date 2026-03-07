import json
import logging
from datetime import datetime
from typing import Optional

import pandas as pd

from src import utils

logger = logging.getLogger(__name__)


def main_page(transactions: pd.DataFrame, date_time_str: Optional[str] = None) -> str:
    """Генерирует JSON для главной страницы."""
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

    start_of_month = utils.get_start_of_month(current_dt)
    filtered = utils.filter_transactions_by_date(transactions, start_of_month, current_dt)

    cards = {}
    for _, t in filtered.iterrows():
        card_num = t.get("Номер карты", "")
        if pd.isna(card_num) or card_num == 0 or card_num == "":
            continue
        amount = t.get("Сумма операции", 0)
        if amount < 0:
            abs_amount = abs(amount)
            card_key = str(card_num)
            if card_key not in cards:
                cards[card_key] = {"spent": 0, "cashback": 0}
            cards[card_key]["spent"] += abs_amount
            cards[card_key]["cashback"] = cards[card_key]["spent"] // 100

    sorted_by_amount = filtered.sort_values(by="Сумма платежа", key=abs, ascending=False)
    top_transactions = sorted_by_amount.head(5).to_dict("records")

    settings = utils.load_user_settings()
    currencies = settings.get("user_currencies", [])
    stocks = settings.get("user_stocks", [])

    exchange_rates = utils.get_exchange_rates(currencies)
    stock_prices = utils.get_stock_prices(stocks)

    response = {
        "greeting": greeting,
        "cards": [
            {"last_digits": card, "total_spent": round(data["spent"], 2), "cashback": data["cashback"]}
            for card, data in cards.items()
        ],
        "top_transactions": [
            {
                "date": (
                    t.get("Дата операции").strftime("%d.%m.%Y") if isinstance(t.get("Дата операции"), datetime) else ""
                ),
                "amount": abs(t.get("Сумма платежа", 0)),
                "category": t.get("Категория", ""),
                "description": t.get("Описание", ""),
            }
            for t in top_transactions
        ],
        "currencies": exchange_rates,
        "stocks": stock_prices,
    }

    json_str = json.dumps(response, ensure_ascii=False, indent=2, default=str)
    logger.info("JSON для главной страницы сформирован")
    return json_str


def events_page(transactions: pd.DataFrame, date_str: str, period: str = "M") -> str:
    """Генерирует JSON для страницы событий."""
    start_date, end_date = utils.get_date_range(date_str, period)
    filtered = utils.filter_transactions_by_date(transactions, start_date, end_date)

    expenses_df = filtered[filtered["Сумма операции"] < 0].copy()
    income_df = filtered[filtered["Сумма операции"] > 0].copy()

    def process_transactions(df: pd.DataFrame, is_expense: bool = True) -> dict:
        if df.empty:
            return {"total": 0, "main": [], "transfers_and_cash": []}
        total = int(round(abs(df["Сумма операции"].sum())))
        grouped = df.groupby("Категория")["Сумма операции"].sum().abs().round().astype(int)
        grouped = grouped.sort_values(ascending=False)
        main_categories = grouped.head(7).reset_index()
        main_list = main_categories.to_dict("records")
        if len(grouped) > 7:
            other_sum = grouped.iloc[7:].sum()
            main_list.append({"category": "Остальное", "amount": other_sum})
        transfers_and_cash = []
        if is_expense:
            for cat in ["Наличные", "Переводы"]:
                if cat in grouped:
                    transfers_and_cash.append({"category": cat, "amount": int(grouped[cat])})
        return {"total": total, "main": main_list, "transfers_and_cash": transfers_and_cash}

    expenses = process_transactions(expenses_df, is_expense=True)
    income = process_transactions(income_df, is_expense=False)

    settings = utils.load_user_settings()
    currencies = settings.get("user_currencies", [])
    stocks = settings.get("user_stocks", [])
    currency_rates = [{"currency": cur, "rate": rate} for cur, rate in utils.get_exchange_rates(currencies).items()]
    stock_prices = [{"stock": ticker, "price": price} for ticker, price in utils.get_stock_prices(stocks).items()]

    response = {"expenses": expenses, "income": income, "currency_rates": currency_rates, "stock_prices": stock_prices}
    return json.dumps(response, ensure_ascii=False, indent=2, default=str)
