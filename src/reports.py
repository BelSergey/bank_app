import functools
import json
import logging
from datetime import datetime
from typing import Any, Callable, Optional

import pandas as pd
from pandas.tseries.offsets import DateOffset

logger = logging.getLogger(__name__)


def report_to_file(filename: Optional[str] = None) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Декоратор для записи результата функции-отчёта в JSON-файл."""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            # Если результат — строка, считаем что это JSON
            if isinstance(result, str):
                data = json.loads(result)
            else:
                data = result
            if filename is None:
                fname = f"report_{func.__name__}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            else:
                fname = filename
            with open(fname, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"Отчёт сохранён в файл {fname}")
            return result

        return wrapper

    return decorator


@report_to_file()
def spending_by_category(transactions: pd.DataFrame, category: str, date: Optional[str] = None) -> str:
    """Отчёт по тратам в заданной категории за последние 3 месяца."""
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    end_date = pd.to_datetime(date).to_pydatetime()
    start_date = end_date - DateOffset(months=3)

    df = transactions.copy()
    if df.empty:
        return json.dumps({})

    df["Категория"] = df["Категория"].astype(str)
    df["Дата операции"] = pd.to_datetime(df["Дата операции"], errors="coerce")

    mask = (df["Дата операции"] >= start_date) & (df["Дата операции"] <= end_date) & (df["Категория"] == category)
    filtered = df.loc[mask]

    filtered["Месяц"] = filtered["Дата операции"].dt.to_period("M")
    spending = filtered.groupby("Месяц")["Сумма операции"].apply(lambda x: abs(x.sum())).to_dict()
    spending = {str(k): round(v, 2) for k, v in spending.items()}

    result = {
        "category": category,
        "period": f"{start_date.date()} - {end_date.date()}",
        "spending_by_month": spending,
    }
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)
