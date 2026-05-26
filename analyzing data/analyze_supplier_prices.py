from pathlib import Path

import pandas as pd

from utils.plotting import plot_supplier_price_ranges

ROOT = Path(__file__).parent
INPUT_PATH = ROOT / "data" / "raw" / "supplier_products_parsed.csv"
OUTPUT_PATH = ROOT / "data" / "processed" / "supplier_price_summary.csv"
PLOT_PATH = ROOT / "plots" / "supplier_price_ranges.png"

def is_reasonable_price(row):
    price = row["price_rub"]
    if pd.isna(price):
        return False
    if row["category"] == "Упаковка":
        return price >= 1
    return price >= 50

def main():
    products = pd.read_csv(INPUT_PATH)
    priced = products.dropna(subset=["price_rub"]).copy()
    priced = priced[priced.apply(is_reasonable_price, axis=1)]
    priced = priced.drop_duplicates(
        subset=["supplier_name", "product_name", "category", "price_rub"]
    )

    summary = (
        priced.groupby(["supplier_name", "category"], as_index=False)
        .agg(
            products_with_price=("product_name", "nunique"),
            min_price_rub=("price_rub", "min"),
            median_price_rub=("price_rub", "median"),
            max_price_rub=("price_rub", "max"),
        )
        .sort_values(["supplier_name", "category"])
    )
    summary.to_csv(OUTPUT_PATH, index=False)
    plot_supplier_price_ranges(priced, PLOT_PATH)

    print(f"Товарных строк с ценой после очистки: {len(priced)}")
    print(f"Уникальных товаров с ценой: {priced['product_name'].nunique()}")
    print(f"Таблица сохранена: {OUTPUT_PATH}")
    print(f"График сохранен: {PLOT_PATH}")
    print(summary.to_string(index=False))

if __name__ == "__main__":
    main()

