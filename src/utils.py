import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
import yfinance as yf
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = BASE_DIR / 'data' / 'operations.xlsx'

def read_excel(file_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Читает Excel-файл и возвращает список словарей с транзакциями."""
    if file_path is None:
        file_path = str(DATA_FILE)
    elif not os.path.isabs(file_path):
        file_path = str(BASE_DIR / file_path)

    logger.info(f"Чтение файла: {file_path.split()[-1]}")
    try:
        df = pd.read_excel(file_path)
        df.columns = df.columns.str.strip()
        date_columns = ['Дата операции', 'Дата платежа']
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], dayfirst=True, errors='coerce')
        df = df.fillna(0)
        logger.info(f"Загружено {len(df)} транзакций")
        return df.to_dict('records')
    except FileNotFoundError:
        logger.error(f"Файл {file_path} не найден")
        return []
    except Exception as e:
        logger.exception(f"Ошибка при чтении файла: {e}")
        return []

def get_start_of_month(date: datetime) -> datetime:
    """Возвращает начало месяца для заданной даты."""
    return datetime(date.year, date.month, 1)

def get_date_range(date_str: str, period: str = 'M') -> tuple[datetime, datetime]:
    """ Возвращает кортеж (start_date, end_date) в зависимости от периода. """
    end_date = pd.to_datetime(date_str).to_pydatetime()
    if period == 'ALL':
        # все транзакции до end_date
        start_date = datetime.min
    elif period == 'Y':
        start_date = datetime(end_date.year, 1, 1)
    elif period == 'M':
        start_date = datetime(end_date.year, end_date.month, 1)
    elif period == 'W':
        # начало недели (понедельник)
        start_date = end_date - timedelta(days=end_date.weekday())
    else:
        raise ValueError(f"Неизвестный период: {period}")
    return start_date, end_date

def filter_transactions_by_date(transactions: List[Dict], start_date: datetime, end_date: datetime) -> List[Dict]:
    """Фильтрует транзакции по диапазону дат (по полю 'Дата операции')."""
    filtered = []
    for t in transactions:
        op_date = t.get('Дата операции')
        if isinstance(op_date, datetime) and start_date <= op_date <= end_date:
            filtered.append(t)
    return filtered

# ---------- Внешние API ----------
def get_exchange_rates(currencies: List[str]) -> Dict[str, float]:
    """  Получает курсы валют относительно RUB через API Layer. """

    api_key = os.getenv("exchange_rates_data_api_key")
    if not api_key:
        logger.error("Не задан EXCHANGE_API_KEY")
        return {}

    symbols = ','.join(currencies)
    url = f"https://api.apilayer.com/exchangerates_data/latest?base=RUB&symbols={symbols}"
    headers = {"apikey": api_key}

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        rates = data.get('rates', {})
        logger.info(f"Курсы валют получены: {rates}")
        return rates
    except Exception as e:
        logger.exception(f"Ошибка получения курсов валют: {e}")
        return {}

def get_stock_prices(tickers: List[str]) -> Dict[str, float]:
    """ Получает цены акций через yfinance. """
    try:
        data = yf.download(tickers, period="1d", interval="1d", progress=False)['Close']
        if data.empty:
            return {}
        # Берём последнюю цену
        if len(tickers) == 1:
            return {tickers[0]: float(data.iloc[-1])}
        else:
            return data.iloc[-1].to_dict()
    except Exception as e:
        logger.exception(f"Ошибка получения цен акций: {e}")
        return {}

# ---------- Загрузка пользовательских настроек ----------
def load_user_settings() -> Dict[str, List[str]]:
    """Загружает настройки из user_settings.json."""

    try:
        with open(BASE_DIR/'user_settings.json', 'r', encoding='utf-8') as f:
            settings = json.load(f)
        return settings
    except FileNotFoundError:
        logger.warning("Файл user_settings.json не найден, используются значения по умолчанию")
        return {
            "user_currencies": ["USD", "EUR"],
            "user_stocks": ["AAPL", "AMZN", "GOOGL", "MSFT", "TSLA"]
        }