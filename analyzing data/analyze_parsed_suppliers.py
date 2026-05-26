from pathlib import Path

import pandas as pd

from utils.plotting import plot_supplier_category_coverage

ROOT = Path(__file__).parent
INPUT_PATH = ROOT / "data" / "raw" / "supplier_products_parsed.csv"
OUTPUT_PATH = ROOT / "data" / "processed" / "supplier_category_coverage.csv"
PLOT_PATH = ROOT / "plots" / "supplier_category_coverage.png"

def main():
    products = pd.read_csv(INPUT_PATH)
    coverage = (
        products.groupby(["supplier_name", "category"], as_index=False)
        .agg(products_count=("product_name", "nunique"))
        .sort_values(["supplier_name", "products_count"], ascending=[True, False])
    )
    coverage.to_csv(OUTPUT_PATH, index=False)
    plot_supplier_category_coverage(coverage, PLOT_PATH)

    print(f"Всего найдено товаров: {products['product_name'].nunique()}")
    print(f"Поставщиков: {products['supplier_name'].nunique()}")
    print(f"Категорий: {products['category'].nunique()}")
    print(f"Таблица сохранена: {OUTPUT_PATH}")
    print(f"График сохранен: {PLOT_PATH}")

if __name__ == "__main__":
    main()

