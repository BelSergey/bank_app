import json
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def simple_search(search_str: str, transactions: List[Dict[str, Any]]) -> str:
    """Простой поиск транзакций по категории или описанию."""
    logger.info(f"Поиск по строке: '{search_str}'")
    result = []
    search_lower = search_str.lower()
    for t in transactions:
        description = str(t.get("Описание", ""))
        category = str(t.get("Категория", ""))
        if search_lower in description.lower() or search_lower in category.lower():
            result.append(t)
    logger.info(f"Найдено {len(result)} транзакций")
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)
