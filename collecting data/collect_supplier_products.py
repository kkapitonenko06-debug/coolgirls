from pathlib import Path

from utils.scraping import SupplierProductParser

ROOT = Path(__file__).parent
SOURCES_PATH = ROOT / "data" / "raw" / "supplier_sources.csv"
OUTPUT_PATH = ROOT / "data" / "raw" / "supplier_products_parsed.csv"

def main():
    parser = SupplierProductParser()
    products = parser.parse_sources(SOURCES_PATH)
    products.to_csv(OUTPUT_PATH, index=False)

    print(f"Собрано товаров: {len(products)}")
    print(f"Файл сохранен")
    if not products.empty:
        print(products.groupby(["supplier_name", "category"]).size())

if __name__ == "__main__":
    main()

