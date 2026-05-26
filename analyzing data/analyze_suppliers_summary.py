from pathlib import Path

import pandas as pd

ROOT        = Path(__file__).parent.parent
PRICES_PATH = ROOT / "data" / "raw"       / "selected_supplier_prices.csv"
RECIPE_PATH = ROOT / "data" / "raw"       / "drink_recipe.csv"
DADATA_PATH = ROOT / "data" / "processed" / "counterparty_risk_summary.csv"
OUT_PATH    = ROOT / "data" / "processed" / "suppliers_summary.csv"

#Сопоставление названий поставщиков в прайсах с юрлицами в DaData
SUPPLIER_LEGAL = {
    "ShopBubbleTea": "ShopBubbleTea",
    "KiFood":        None,
    "Metro":         "ООО МЕТРО КЭШ ЭНД КЕРРИ",
    "FoodLine":      "ООО ФУДЛАЙН",
    "Market":        None,
    "Price.ru":      None,
}

def build_summary(prices, recipe, dadata):
    merged = prices.merge(
        recipe[["ingredient_key", "item", "category", "amount_per_drink", "amount_unit"]],
        on="ingredient_key",
        how="left",
    )

    #Цена за единицу и стоимость на порцию
    UNIT_NORM = {"g": 1, "kg": 1000, "ml": 1, "l": 1000, "pcs": 1}
    merged["pack_amount_base"] = merged["pack_amount"] * merged["pack_unit"].map(UNIT_NORM)
    merged["unit_price_rub"]   = merged["pack_price_rub"] / merged["pack_amount_base"]
    merged["cost_per_drink"]   = merged["unit_price_rub"] * merged["amount_per_drink"]

    #Статус по DaData
    dadata_status = dadata.set_index("query")[["status", "risk_comment"]]

    rows = []
    for supplier, group in merged.groupby("supplier_name"):
        legal_name  = SUPPLIER_LEGAL.get(supplier)
        if legal_name and legal_name in dadata_status.index:
            status       = dadata_status.loc[legal_name, "status"]
            risk_comment = dadata_status.loc[legal_name, "risk_comment"]
        elif legal_name is None:
            status       = "—"
            risk_comment = "нет данных"
        else:
            status       = "не найден"
            risk_comment = "нужна ручная проверка"

        categories  = ", ".join(sorted(group["category"].dropna().unique()))
        items_count = len(group)
        total_cost_per_drink = group["cost_per_drink"].sum()

        rows.append({
            "supplier_name":        supplier,
            "legal_name":           legal_name or "—",
            "categories":           categories,
            "items_count":          items_count,
            "total_cost_per_drink": round(total_cost_per_drink, 2),
            "status":               status,
            "risk_comment":         risk_comment,
        })

    return pd.DataFrame(rows).sort_values("total_cost_per_drink", ascending=False)


def print_summary(df, merged):
    print("\n" + "=" * 72)
    print("Данные по поставщикам")
    print("=" * 72)

    for _, row in df.iterrows():
        print(f"\n  {row['supplier_name']}  ({row['legal_name']})")
        print(f"  Статус: {row['status']}  —  {row['risk_comment']}")
        print(f"  Категории: {row['categories']}")
        print(f"  Позиций: {row['items_count']},  вклад в себестоимость порции: {row['total_cost_per_drink']:.2f} ₽")

        items = merged[merged["supplier_name"] == row["supplier_name"]]
        for _, item in items.iterrows():
            print(f"    · {item['item']:<30} {item['cost_per_drink']:.2f} ₽/порц  "
                  f"(расход: {item['amount_per_drink']:.0f} {item['amount_unit']})")

    print(f"\n  Итого себестоимость ингредиентов на порцию: "
          f"{df['total_cost_per_drink'].sum():.2f} ₽")


def main():
    prices = pd.read_csv(PRICES_PATH)
    recipe = pd.read_csv(RECIPE_PATH)
    dadata = pd.read_csv(DADATA_PATH)

    UNIT_NORM = {"g": 1, "kg": 1000, "ml": 1, "l": 1000, "pcs": 1}
    merged = prices.merge(
        recipe[["ingredient_key", "item", "category", "amount_per_drink", "amount_unit"]],
        on="ingredient_key", how="left",
    )
    merged["pack_amount_base"] = merged["pack_amount"] * merged["pack_unit"].map(UNIT_NORM)
    merged["unit_price_rub"]   = merged["pack_price_rub"] / merged["pack_amount_base"]
    merged["cost_per_drink"]   = merged["unit_price_rub"] * merged["amount_per_drink"]

    summary = build_summary(prices, recipe, dadata)
    summary.to_csv(OUT_PATH, index=False)
    print_summary(summary, merged)
    print(f"\nТаблица сохранена: {OUT_PATH}")


if __name__ == "__main__":
    main()
