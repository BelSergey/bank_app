import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import requests
import yfinance as yf
from dotenv import load_dotenv
from tabulate import tabulate

load_dotenv()

logger = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = BASE_DIR / "data" / "operations.xlsx"


def read_excel(file_path: Optional[str] = None) -> pd.DataFrame:
    """Читает Excel-файл и возвращает DataFrame с транзакциями."""
    if file_path is None:
        file_path = str(DATA_FILE)
    elif not os.path.isabs(file_path):
        file_path = str(BASE_DIR / file_path)

    logger.info(f"Чтение файла: {Path(file_path).name}")
    try:
        df = pd.read_excel(file_path)
        df.columns = df.columns.str.strip()
        date_columns = ["Дата операции", "Дата платежа"]
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], dayfirst=True, errors="coerce")
        df = df.fillna(0)
        logger.info(f"Загружено {len(df)} транзакций")
        return df
    except FileNotFoundError:
        logger.error(f"Файл {file_path} не найден")
        return pd.DataFrame()
    except Exception as e:
        logger.exception(f"Ошибка при чтении файла: {e}")
        return pd.DataFrame()


def get_start_of_month(date: datetime) -> datetime:
    """Возвращает начало месяца для заданной даты."""
    return datetime(date.year, date.month, 1)


def get_date_range(date_str: str, period: str = "M") -> Tuple[datetime, datetime]:
    """Возвращает кортеж (start_date, end_date) в зависимости от периода."""
    end_date = pd.to_datetime(date_str).to_pydatetime()
    if period == "ALL":
        start_date = datetime.min
    elif period == "Y":
        start_date = datetime(end_date.year, 1, 1)
    elif period == "M":
        start_date = datetime(end_date.year, end_date.month, 1)
    elif period == "W":
        start_date = end_date - timedelta(days=end_date.weekday())
    else:
        raise ValueError(f"Неизвестный период: {period}")
    return start_date, end_date


def filter_transactions_by_date(df: pd.DataFrame, start_date: datetime, end_date: datetime) -> pd.DataFrame:
    """Фильтрует транзакции по диапазону дат."""
    if df.empty:
        return df
    mask = (df["Дата операции"] >= start_date) & (df["Дата операции"] <= end_date)
    return df.loc[mask].copy()


def get_exchange_rates(currencies: List[str]) -> Dict[str, float]:
    """Получает курсы валют через API Центробанка РФ."""
    try:
        url = "https://www.cbr-xml-daily.ru/daily_json.js"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        rates = {}
        for cur in currencies:
            if cur == "RUB":
                rates[cur] = 1.0
            elif cur in data["Valute"]:
                rates[cur] = data["Valute"][cur]["Value"]
            else:
                logger.warning(f"Валюта {cur} не найдена в данных ЦБ")
        logger.info(f"Курсы валют получены от ЦБ РФ: {rates}")
        return rates
    except Exception as e:
        logger.exception(f"Ошибка получения курсов валют от ЦБ РФ: {e}")
        return {}


def get_stock_prices(tickers: List[str]) -> Dict[str, float]:
    """Получает цены акций через yfinance."""
    try:
        data = yf.download(tickers, period="1d", interval="1d", progress=False)["Close"]
        if data.empty:
            return {}
        if len(tickers) == 1:
            return {tickers[0]: float(data.iloc[-1])}
        else:
            return data.iloc[-1].to_dict()
    except Exception as e:
        logger.exception(f"Ошибка получения цен акций: {e}")
        return {}


def load_user_settings() -> Dict[str, List[str]]:
    """Загружает настройки из user_settings.json."""
    try:
        with open(BASE_DIR / "user_settings.json", "r", encoding="utf-8") as f:
            settings = json.load(f)
        return settings
    except FileNotFoundError:
        logger.warning("Файл user_settings.json не найден, используются значения по умолчанию")
        return {"user_currencies": ["USD", "EUR"], "user_stocks": ["AAPL", "AMZN", "GOOGL", "MSFT", "TSLA"]}


def get_top_transactions_by_card(df: pd.DataFrame, card_number: str, limit: int = 3) -> List[Dict]:
    """Возвращает топ-N транзакций по сумме (по модулю) для указанной карты."""

    if df.empty:
        return []
    card_df = df[df["Номер карты"] == card_number].copy()
    if card_df.empty:
        return []
    card_df["abs_amount"] = card_df["Сумма платежа"].abs()
    card_df = card_df.sort_values("abs_amount", ascending=False).head(limit)
    result = []
    for _, row in card_df.iterrows():
        result.append(
            {
                "date": row["Дата операции"].strftime("%d.%m.%Y") if pd.notna(row["Дата операции"]) else "",
                "amount": abs(row["Сумма платежа"]),
                "category": row["Категория"],
                "description": row["Описание"],
            }
        )
    return result


def print_section(title: str):
    """Печатает заголовок раздела."""
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)


def print_cards(cards_data):
    """Выводит информацию по картам в виде таблицы."""
    if not cards_data:
        print("Нет данных по картам.")
        return
    table = []
    for card in cards_data:
        table.append([card["last_digits"], card["total_spent"], card["cashback"]])
    print(tabulate(table, headers=["Карта (посл. 4 цифры)", "Расходы, руб", "Кешбэк, руб"], tablefmt="grid"))


def print_top_transactions(transactions):
    """Выводит топ-5 транзакций."""
    if not transactions:
        print("Нет транзакций.")
        return
    table = []
    for t in transactions:
        table.append([t["date"], t["amount"], t["category"], t["description"][:30]])
    print(tabulate(table, headers=["Дата", "Сумма", "Категория", "Описание"], tablefmt="grid"))


def print_currency_rates(rates):
    """Выводит курсы валют."""
    if not rates:
        print("Курсы валют не получены.")
        return
    for cur, rate in rates.items():
        print(f"  {cur}: {rate:.2f} руб")


def print_stock_prices(prices):
    """Выводит цены акций."""
    if not prices:
        print("Цены акций не получены.")
        return
    for stock, price in prices.items():
        print(f"  {stock}: ${price:.2f}")


def print_categories(cat_list, title):
    """Выводит список категорий с суммами (универсальный доступ к ключам)."""
    if not cat_list:
        print(f"  {title}: нет данных")
        return
    print(f"  {title}:")
    for item in cat_list:
        cat = item.get("category") or item.get("Категория", "?")
        amt = item.get("amount") or item.get("Сумма операции", 0)
        print(f"    {cat}: {amt} руб")
