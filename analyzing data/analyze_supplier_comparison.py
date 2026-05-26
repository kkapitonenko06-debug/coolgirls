#Сравнение поставщиков по цене за порцию.Берёт спарсенные товары из supplier_products_parsed.csv, вычисляет цену за единицу веса/объёма и цену на одну порцию напитка.Сравнивает с ценами из selected_supplier_prices.csv

import re
from pathlib import Path

import pandas as pd

ROOT         = Path(__file__).parent
PARSED_PATH  = ROOT / "data" / "raw" / "supplier_products_parsed.csv"
MANUAL_PATH  = ROOT / "data" / "raw" / "selected_supplier_prices.csv"
RECIPE_PATH  = ROOT / "data" / "raw" / "drink_recipe.csv"
OUT_PATH     = ROOT / "data" / "processed" / "supplier_comparison_full.csv"

#Количество ингредиента на порцию:

SERVING = {
    "Тапиока":         (55,  "g"),
    "Сиропы":          (22,  "ml"),
    "Желе":            (40,  "g"),
    "Джус-боллы":      (40,  "g"),
    "Пудинг":          (45,  "g"),
    "Фруктовые пюре":  (40,  "ml"),
    "Молочная основа": (100, "ml"),
    "Упаковка":        (1,   "pcs"),
    "Сухие смеси":     (15,  "g"),
    "Чай":             (8,   "g"),
}

#Парсим размер упаковки

def parse_pack_size(pack_size):
    if not pack_size or pd.isna(pack_size):
        return None

    s = str(pack_size).strip().replace(",", ".")

    m = re.search(r"([\d.]+)\s*(кг|г|гр|кг\.|л|мл|шт|pcs)", s, re.I)
    if not m:
        return None

    amount = float(m.group(1))
    unit   = m.group(2).lower().rstrip(".")

    multipliers = {
        "кг": ("g", 1000),
        "г":  ("g", 1),
        "гр": ("g", 1),
        "л":  ("ml", 1000),
        "мл": ("ml", 1),
        "шт": ("pcs", 1),
        "pcs":("pcs", 1),
    }
    base_unit, mult = multipliers.get(unit, ("g", 1))
    return amount * mult, base_unit

#Ключевые слова аксессуары, инвентарь, не еда
ACCESSORY_KEYWORDS = (
    "ложка", "шумовка", "дозатор", "помпа", "сито", "трубочка-мешалка",
    "щипцы", "лопатка", "термометр", "мерный", "набор инструмент",
    "пинцет", "воронка",
)

def load_parsed(path):
    df = pd.read_csv(path)
    df = df.dropna(subset=["price_rub"]).copy()
    df = df[df["price_rub"] > 0]

    mask_accessory = df["product_name"].str.lower().apply(
        lambda name: any(kw in name for kw in ACCESSORY_KEYWORDS)
    )
    df = df[~mask_accessory]

    def is_sampler(row):
        if "набор" not in str(row["product_name"]).lower():
            return False
        ps = str(row.get("pack_size", "") or "")
        m = re.search(r"([\d.]+)\s*(кг|г)", ps, re.I)
        if not m:
            return False
        amount = float(m.group(1))
        if m.group(2).lower() == "кг":
            amount *= 1000
        return amount < 200

    df = df[~df.apply(is_sampler, axis=1)]

    parsed = df["pack_size"].apply(parse_pack_size)
    df["pack_amount_base"] = parsed.apply(lambda x: x[0] if x else None)
    df["base_unit"]        = parsed.apply(lambda x: x[1] if x else None)

    #Оставляем только строки с распознанным размером упаковки
    df = df.dropna(subset=["pack_amount_base"])

    #Цена за единицу
    df["unit_price_rub"] = df["price_rub"] / df["pack_amount_base"]

    df["price_source"] = "parsed"

    return df[[
        "supplier_name", "category", "product_name",
        "price_rub", "pack_amount_base", "base_unit",
        "unit_price_rub", "price_source",
    ]]

INGREDIENT_CATEGORY = {
    "tea_black":       "Чай",
    "tea_gaba":        "Чай",
    "tea_oolong":      "Чай",
    "tea_jasmine":     "Чай",
    "matcha":          "Чай",
    "milk":            "Молочная основа",
    "oat_milk":        "Молочная основа",
    "coconut_milk":    "Молочная основа",
    "tapioca":         "Тапиока",
    "coconut_jelly":   "Желе",
    "aloe_jelly":      "Желе",
    "pudding":         "Пудинг",
    "strawberry_puree":"Фруктовые пюре",
    "mango_puree":     "Фруктовые пюре",
    "passion_fruit":   "Фруктовые пюре",
    "syrup_vanilla":   "Сиропы",
    "syrup_lychee":    "Сиропы",
    "syrup_brown_sugar":"Сиропы",
    "cup":             "Упаковка",
    "lid":             "Упаковка",
    "straw":           "Упаковка",
    "seal_film":       "Упаковка",
    "ice":             "Прочее",
    "lemon_juice":     "Прочее",
    "cream_cheese":    "Крем",
    "cream_33":        "Крем",
    "coconut_cream":   "Крем",
    "sugar_powder":    "Крем",
    "sea_salt":        "Крем",
}

def load_manual(path, recipe):
    df = pd.read_csv(path)

    # Категория по маппингу ингредиентов (совпадает с parsed данными)
    df["category"] = df["ingredient_key"].map(INGREDIENT_CATEGORY)

    UNIT_NORM = {"g": ("g", 1), "kg": ("g", 1000), "ml": ("ml", 1),
                 "l": ("ml", 1000), "pcs": ("pcs", 1)}
    df["pack_amount_base"] = df.apply(
        lambda r: r["pack_amount"] * UNIT_NORM.get(r["pack_unit"], ("g", 1))[1], axis=1
    )
    df["base_unit"] = df["pack_unit"].map(
        lambda u: UNIT_NORM.get(u, ("g", 1))[0]
    )
    df["unit_price_rub"] = df["pack_price_rub"] / df["pack_amount_base"]
    df["price_source"] = "manual"

    return df[[
        "supplier_name", "category", "product_name",
        "pack_price_rub", "pack_amount_base", "base_unit",
        "unit_price_rub", "price_source",
    ]].rename(columns={"pack_price_rub": "price_rub"})

#Основная функция

def build_comparison(parsed, manual):
    combined = pd.concat([parsed, manual], ignore_index=True)

    rows = []
    for category, serving_amount_and_unit in SERVING.items():
        serving_amount, serving_unit = serving_amount_and_unit

        subset = combined[combined["category"] == category].copy()
        if subset.empty:
            continue

        subset = subset[subset["base_unit"] == serving_unit]
        if subset.empty:
            continue

        #Медианная цена за единицу по каждому поставщику
        agg = (
            subset.groupby("supplier_name", as_index=False)
            .agg(
                products_count   =("product_name", "nunique"),
                min_unit_price   =("unit_price_rub", "min"),
                median_unit_price=("unit_price_rub", "median"),
                max_unit_price   =("unit_price_rub", "max"),
                price_source     =("price_source",
                                   lambda s: "+".join(sorted(s.unique()))),
            )
        )
        agg["category"]        = category
        agg["serving_amount"]  = serving_amount
        agg["serving_unit"]    = serving_unit
        agg["cost_per_serving_min"]    = agg["min_unit_price"]    * serving_amount
        agg["cost_per_serving_median"] = agg["median_unit_price"] * serving_amount
        rows.append(agg)

    if not rows:
        return pd.DataFrame()

    result = pd.concat(rows, ignore_index=True)
    result = result.sort_values(["category", "cost_per_serving_median"])
    return result

def print_comparison(df):
    print("\n" + "=" * 72)
    print("Сравнение поставщиков по цене за порцию")
    print("=" * 72)

    for category, group in df.groupby("category", sort=False):
        serving_amount = group["serving_amount"].iloc[0]
        serving_unit   = group["serving_unit"].iloc[0]
        print(f"\n  {category}  ({serving_amount} {serving_unit}/порция)")
        print(f"  {'Поставщик':<22} {'Товаров':>7}  {'Мин ₽/порц':>11}  {'Медиана':>9}  {'Источник'}")
        print("  " + "-" * 65)

        min_median = group["cost_per_serving_median"].min()
        for _, row in group.iterrows():
            mark = "★" if row["cost_per_serving_median"] == min_median else " "
            src  = "ручн." if row["price_source"] == "manual" else "парсинг"
            print(
                f"  {mark} {row['supplier_name']:<21} {row['products_count']:>7}  "
                f"{row['cost_per_serving_min']:>10.2f}₽  "
                f"{row['cost_per_serving_median']:>8.2f}₽  {src}"
            )

def main():
    recipe = pd.read_csv(RECIPE_PATH)
    parsed = load_parsed(PARSED_PATH)
    manual = load_manual(MANUAL_PATH, recipe)

    comparison = build_comparison(parsed, manual)
    comparison.to_csv(OUT_PATH, index=False)
    print_comparison(comparison)

    print(f"\nФайл сохранен")

if __name__ == "__main__":
    main()
