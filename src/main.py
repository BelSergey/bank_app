import json
import logging
from datetime import datetime

import pandas as pd
from typing import List, Dict, Any
from src import reports, services, utils, views

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


def choose_mode():
    """Запрашивает у пользователя режим работы."""
    while True:
        print("\nВыберите режим отображения:")
        print("1 - Использовать текущую дату (сегодня)")
        print("2 - Использовать последнюю дату операции из файла")
        choice = input("Введите 1 или 2: ").strip()
        if choice in ("1", "2"):
            return choice
        print("Некорректный ввод. Пожалуйста, введите 1 или 2.")


def main():
    print("=== ЗАГРУЗКА ТРАНЗАКЦИЙ ===")
    transactions_df = utils.read_excel()
    if transactions_df.empty:
        print("Не удалось загрузить транзакции. Проверьте файл data/operations.xlsx")
        return

    last_date = transactions_df["Дата операции"].max()
    if pd.isna(last_date):
        print("В файле нет корректных дат операций.")
        return

    mode = choose_mode()

    if mode == "1":
        current_dt = datetime.now()
        date_input = current_dt.strftime("%Y-%m-%d %H:%M:%S")
        date_for_events = current_dt.strftime("%Y-%m-%d")
        end_date = current_dt
        start_date = utils.get_start_of_month(current_dt)
        print(f"\nИспользуем текущую дату: {current_dt.strftime('%d.%m.%Y')}")
    else:
        date_input = last_date.strftime("%Y-%m-%d 12:00:00")
        date_for_events = last_date.strftime("%Y-%m-%d")
        end_date = last_date
        start_date = utils.get_start_of_month(last_date)
        print(f"\nИспользуем последнюю дату из данных: {last_date.strftime('%d.%m.%Y')}")

    filtered_df = utils.filter_transactions_by_date(transactions_df, start_date, end_date)
    transactions_list = transactions_df.to_dict("records")

    utils.print_section("ГЛАВНАЯ СТРАНИЦА")
    json_result = views.main_page(transactions_df, date_input)
    data = json.loads(json_result)

    print(f"\n{data['greeting']}")
    print("\n--- Информация по картам ---")
    utils.print_cards(data["cards"])

    print("\n--- Топ-5 транзакций по каждой карте ---")
    all_cards = filtered_df["Номер карты"].dropna().unique()
    if len(all_cards) == 0:
        print("  Нет данных по картам за выбранный период.")
    else:
        for card_num in all_cards:
            top_trans = utils.get_top_transactions_by_card(filtered_df, card_num, limit=5)
            if top_trans:
                print(f"\n  Карта {card_num}:")
                for t in top_trans:
                    print(f"    {t['date']} | {t['amount']:>10.2f} руб | {t['category']} | {t['description'][:50]}")
            else:
                print(f"\n  Карта {card_num}: нет транзакций")

    print("\n--- Топ-5 транзакций (общий) ---")
    utils.print_top_transactions(data["top_transactions"])

    print("\n--- Курсы валют ---")
    utils.print_currency_rates(data["currencies"])

    print("\n--- Цены акций S&P500 ---")
    utils.print_stock_prices(data["stocks"])

    # 2. Страница событий
    utils.print_section("СТРАНИЦА СОБЫТИЙ (месяц до указанной даты)")
    events_json = views.events_page(transactions_df, date_for_events, period="M")
    events = json.loads(events_json)

    print("\n--- РАСХОДЫ ---")
    print(f"  Общая сумма расходов: {events['expenses']['total']} руб")
    utils.print_categories(events["expenses"]["main"], "Основные категории")
    utils.print_categories(events["expenses"]["transfers_and_cash"], "Переводы и наличные")

    print("\n--- ПОСТУПЛЕНИЯ ---")
    print(f"  Общая сумма поступлений: {events['income']['total']} руб")
    utils.print_categories(events["income"]["main"], "Основные категории")

    print("\n--- Курсы валют ---")
    for curr in events["currency_rates"]:
        print(f"  {curr['currency']}: {curr['rate']:.2f} руб")

    print("\n--- Цены акций S&P500 ---")
    for stock in events["stock_prices"]:
        print(f"  {stock['stock']}: ${stock['price']:.2f}")

    utils.print_section("ПРОСТОЙ ПОИСК")
    search_string = input("Введите слово для поиска: ").strip()
    transactions_list_str_keys: List[Dict[str, Any]] = [
        {str(k): v for k, v in record.items()}
        for record in transactions_df.to_dict("records")
    ]
    search_result = services.simple_search(search_string, transactions_list_str_keys)
    found = json.loads(search_result)
    print(f"Найдено транзакций: {len(found)}")
    if found:
        print("\n Первая найденная транзакция:")
        first = found[0]
        print(f"  Дата: {first.get('Дата операции', '')}")
        print(f"  Категория: {first.get('Категория', '')}")
        print(f"  Описание: {first.get('Описание', '')}")
        print(f"  Сумма: {abs(first.get('Сумма операции', 0))} руб")

    utils.print_section("ОТЧЁТ ПО КАТЕГОРИИ 'Супермаркеты' за последние 3 месяца")
    report_result = reports.spending_by_category(transactions_df, "Супермаркеты", date_for_events)
    report = json.loads(report_result)
    if report and report.get("spending_by_month"):
        print(f"Категория: {report['category']}")
        print(f"Период: {report['period']}")
        print("Траты по месяцам:")
        for month, amount in report["spending_by_month"].items():
            print(f"  {month}: {amount} руб")
    else:
        print("Нет данных по категории 'Супермаркеты' за последние 3 месяца.")

    print("\n" + "=" * 60)
    print("Все отчёты также сохранены в JSON-файлы (см. директорию проекта).")


if __name__ == "__main__":
    main()
