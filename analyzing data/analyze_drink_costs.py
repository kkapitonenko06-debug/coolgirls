import math
from pathlib import Path

import pandas as pd

from utils.cost_analysis import build_recipe_costs, summarize_monthly_purchase


ROOT = Path(__file__).parent
RECIPE_PATH      = ROOT / "data" / "raw"       / "drink_recipe.csv"
PRICES_PATH      = ROOT / "data" / "raw"       / "selected_supplier_prices.csv"
PARSED_PATH      = ROOT / "data" / "raw"       / "supplier_products_parsed.csv"
BENCHMARK_PATH   = ROOT / "data" / "processed" / "competitor_benchmark.csv"

OUT_DIR = ROOT / "data" / "processed"
OUT_DIR.mkdir(parents=True, exist_ok=True)

DRINK_COSTS_OUT      = OUT_DIR / "drink_costs.csv"
INGREDIENT_COSTS_OUT = OUT_DIR / "ingredient_costs.csv"
SUPPLIER_COMPARE_OUT = OUT_DIR / "supplier_price_comparison.csv"
MONTHLY_OUT          = OUT_DIR / "monthly_purchase_plan.csv"
MIN_COST_MULTIPLIER = 2.5

DRINK_MARKET_MATCH = {
    "Молочный чай с тапиокой": ["Молочный/тапиока", "Молочный"],
    "Клубничный Фруктовый":   ["Фруктовый/тапиока", "Фруктовый"],
    "Габа Улун с Пудингом":   ["Молочный/пудинг", "Молочный/мусс", "Молочный"],
    "Матча Латте с Тапиокой": ["Матча/тапиока", "Матча"],
    "Кокосовый Крем Чай":     ["Кремовый/желе", "Кремовый"],
}

#Состав напитков

DRINKS = {
    "Молочный чай с тапиокой": [
        "tea_black", "milk", "tapioca", "syrup_brown_sugar",
        "ice", "cup", "lid", "straw",
    ],
    "Матча Латте с Тапиокой": [
        "matcha", "oat_milk", "tapioca", "syrup_vanilla",
        "ice", "cup", "lid", "straw",
    ],
    "Клубничный Фруктовый": [
        "tea_black", "strawberry_puree", "tapioca", "syrup_lychee",
        "ice", "cup", "lid", "straw",
    ],
    "Кокосовый Крем Чай": [
        "tea_jasmine", "coconut_milk", "coconut_jelly",
        "cream_cheese", "cream_33", "coconut_cream",
        "sugar_powder", "sea_salt", "syrup_vanilla",
        "ice", "cup", "lid", "straw",
    ],
    "Габа Улун с Пудингом": [
        "tea_gaba", "milk", "pudding", "syrup_vanilla",
        "ice", "cup", "lid", "straw",
    ],
}


def load_data():
    recipe = pd.read_csv(RECIPE_PATH)
    prices = pd.read_csv(PRICES_PATH)
    prices = prices[[
        "ingredient_key", "supplier_name", "product_name",
        "pack_amount", "pack_unit", "pack_price_rub",
    ]]
    return recipe, prices

def load_competitor_benchmark():
    if not BENCHMARK_PATH.exists():
        raise FileNotFoundError(
            f"Файл {BENCHMARK_PATH} не найден.\n"
            "Сначала запустите: python analyze_competitor_benchmark.py"
        )
    return pd.read_csv(BENCHMARK_PATH)


def get_market_stats(drink_name, benchmark):
    type_keys = DRINK_MARKET_MATCH.get(drink_name, [])

    for type_key in type_keys:
        primary = type_key.split("/")[0]
        subset = benchmark[
            benchmark["type"].str.contains(primary, case=False, na=False)
        ]
        if len(subset) >= 2:
            return {
                "type_matched":  type_key,
                "n_positions":   len(subset),
                "competitors":   sorted(subset["competitor"].unique().tolist()),
                "market_min":    float(subset["price_rub"].min()),
                "market_median": float(subset["price_rub"].median()),
                "market_max":    float(subset["price_rub"].max()),
            }

    return {
        "type_matched":  "весь рынок",
        "n_positions":   len(benchmark),
        "competitors":   sorted(benchmark["competitor"].unique().tolist()),
        "market_min":    float(benchmark["price_rub"].min()),
        "market_median": float(benchmark["price_rub"].median()),
        "market_max":    float(benchmark["price_rub"].max()),
    }

def recommend_price(cost, market_stats):
    market_target = market_stats["market_median"]
    cost_floor    = cost * MIN_COST_MULTIPLIER
    raw_price     = max(market_target, cost_floor)
    return math.ceil(raw_price / 10) * 10

#Себестоимость по рецептам

def compute_drink_costs(recipe, prices, benchmark):
    best_price = prices.drop_duplicates(subset="ingredient_key")
    full       = build_recipe_costs(recipe, best_price)

    rows = []
    for drink_name, keys in DRINKS.items():
        subset = full[full["ingredient_key"].isin(keys)].copy()
        subset["drink_name"] = drink_name
        rows.append(subset)

    ingredient_df = pd.concat(rows, ignore_index=True)

    summary_rows = []
    for drink_name, group in ingredient_df.groupby("drink_name"):
        cost      = group["cost_per_drink_rub"].sum()
        mstats    = get_market_stats(drink_name, benchmark)
        rec_price = recommend_price(cost, mstats)
        margin_rub = rec_price - cost
        margin_pct = margin_rub / rec_price*100

        #каждый словарь --- это один напиток с себестоимостью, рыночными данными и рекомендованной ценой
        summary_rows.append({
            "drink_name":            drink_name,
            "ingredients_count":     len(group),
            "total_cost_rub":        round(cost, 2),
            #рыночный ориентир
            "market_type":           mstats["type_matched"],
            "market_n":              mstats["n_positions"],
            "market_min_rub":        mstats["market_min"],
            "market_median_rub":     mstats["market_median"],
            "market_max_rub":        mstats["market_max"],
            #рекомендуемая цена
            "recommended_price_rub": rec_price,
            "margin_rub":            round(margin_rub, 2),
            "margin_pct":            round(margin_pct, 1),
        })

    drink_summary = (
        pd.DataFrame(summary_rows)
        .sort_values("total_cost_rub")
        .reset_index(drop=True)
    )
    return ingredient_df, drink_summary

#сравнение поставщиков по ингредиентам

def compare_suppliers(recipe, prices):
    UNIT_NORM = {"g": 1, "kg": 1000, "ml": 1, "l": 1000, "pcs": 1}

    p = prices.copy()
    p["pack_amount_base"] = p.apply(
        lambda r: r["pack_amount"] * UNIT_NORM.get(r["pack_unit"], 1), axis=1
    )
    p["unit_price_rub"] = p["pack_price_rub"] / p["pack_amount_base"]

    recipe_units = recipe.set_index("ingredient_key")[["item", "category", "amount_per_drink"]]
    p = p.join(recipe_units, on="ingredient_key", how="left")
    p["cost_per_drink_rub"] = p["unit_price_rub"] * p["amount_per_drink"]

    counts     = p.groupby("ingredient_key")["supplier_name"].count()
    multi      = counts[counts > 1].index
    comparison = p[p["ingredient_key"].isin(multi)].copy() if len(multi) > 0 else p.copy()

    return comparison[[
        "ingredient_key", "item", "category",
        "supplier_name", "product_name",
        "pack_amount", "pack_unit", "pack_price_rub",
        "unit_price_rub", "amount_per_drink", "cost_per_drink_rub",
    ]].sort_values(["ingredient_key", "unit_price_rub"])


def print_drink_summary(drink_summary):
    print("\n" + "=" * 85)
    print("Себестоимость и цены на рынке")
    print("=" * 85)
    print(
        f"  {'Напиток':<28}  {'Себест.':>8}  {'Медиана рынка':>14}  "
        f"{'Рек. цена':>10}  {'Маржа':>7}  {'Тип / n конк.'}"
    )
    print("  " + "-" * 85)

    for _, row in drink_summary.iterrows():
        print(
            f"  {row['drink_name']:<28}  "
            f"{row['total_cost_rub']:>7.2f}₽  "
            f"{row['market_median_rub']:>7.0f}₽       "
            f"{row['recommended_price_rub']:>9.0f}₽  "
            f"{row['margin_pct']:>6.1f}%  "
            f"{row['market_type']} / n={row['market_n']}"
        )

    avg_cost   = drink_summary["total_cost_rub"].mean()
    avg_price  = drink_summary["recommended_price_rub"].mean()
    avg_margin = drink_summary["margin_pct"].mean()
    print("  " + "-" * 85)
    print(
        f"  {'Среднее':<28}  {avg_cost:>7.2f}₽  {'':>14}  "
        f"{avg_price:>9.0f}₽  {avg_margin:>6.1f}%"
    )


def print_market_context(drink_summary):
    print("\n" + "=" * 75)
    print("Сравнение наших цен и конкурентов")
    print("=" * 75)

    for _, row in drink_summary.iterrows():
        p   = row["recommended_price_rub"]
        lo  = row["market_min_rub"]
        hi  = row["market_max_rub"]
        med = row["market_median_rub"]

        span = hi - lo if hi != lo else 1
        pos  = min(max((p - lo) / span, 0.0), 1.0)
        bar_len = 28
        marker  = int(pos * bar_len)
        bar = "─" * marker + "◆" + "─" * (bar_len - marker)

        if p < med:
            position = f"на {med - p:.0f}₽ ниже медианы, выгоднее для покупателя"
        elif p == med:
            position = "на уровне медианы"
        else:
            position = f"на {p - med:.0f}₽ выше медианы, премиальнее среднего"

        print(f"\n  {row['drink_name']}")
        print(f"  {lo:.0f}₽ [{bar}] {hi:.0f}₽")
        print(f"  Наша цена: {p:.0f}₽  —  {position}")
        print(f"  Тип аналогов: {row['market_type']}  |  позиций в выборке: {row['market_n']}")

def print_top_ingredients(ingredient_df):
    print("\n" + "=" * 65)
    print("Топ-10 ингридиентов по затратам по порцию (среднее по напиткам)")
    print("=" * 65)
    top = (
        ingredient_df.groupby(["ingredient_key", "item"], as_index=False)
        ["cost_per_drink_rub"].mean()
        .sort_values("cost_per_drink_rub", ascending=False)
        .head(10)
    )
    for _, row in top.iterrows():
        print(f"  {row['item']:<25} {row['cost_per_drink_rub']:>6.2f} ₽")

def print_supplier_comparison(comparison):
    print("\n" + "=" * 65)
    print("Сравнение поставщиков (цена за единицу, ₽)")
    print("=" * 65)
    for key, group in comparison.groupby("ingredient_key"):
        item_name = group["item"].iloc[0]
        print(f"\n  {item_name}:")
        for _, row in group.iterrows():
            mark = "★" if row["unit_price_rub"] == group["unit_price_rub"].min() else " "
            print(
                f"    {mark} {row['supplier_name']:<20} "
                f"{row['unit_price_rub']:.3f} ₽/ед  "
                f"({row['cost_per_drink_rub']:.2f} ₽/порц)"
            )


def main():
    recipe, prices = load_data()
    benchmark      = load_competitor_benchmark()

    #Себестоимость + рыночное ценообразование
    ingredient_df, drink_summary = compute_drink_costs(recipe, prices, benchmark)
    ingredient_df.to_csv(INGREDIENT_COSTS_OUT, index=False)
    drink_summary.to_csv(DRINK_COSTS_OUT, index=False)
    print_drink_summary(drink_summary)
    print_market_context(drink_summary)
    print_top_ingredients(ingredient_df)

    #Ежемесячные закупки (120 напитков в день, 30 дней)
    best_price = prices.drop_duplicates(subset="ingredient_key")
    full       = build_recipe_costs(recipe, best_price)
    monthly    = summarize_monthly_purchase(full, drinks_per_day=120, working_days=30)
    monthly.to_csv(MONTHLY_OUT, index=False)

    monthly_total = monthly["monthly_cost_rub"].sum()
    print(f"\n{'=' * 65}")
    print(f"Ежемесячные затраты на игридиенты (120 напитков/день)")
    print(f"{'=' * 65}")
    cat_monthly = (
        monthly.groupby("category")["monthly_cost_rub"]
        .sum()
        .sort_values(ascending=False)
    )
    for cat, val in cat_monthly.items():
        pct = val / monthly_total * 100
        print(f"  {cat:<20} {val:>8,.0f} ₽  ({pct:.1f}%)")
    print(f"  {'ИТОГО':<20} {monthly_total:>8,.0f} ₽")

    #Сравнение поставщиков
    comparison = compare_suppliers(recipe, prices)
    comparison.to_csv(SUPPLIER_COMPARE_OUT, index=False)
    print_supplier_comparison(comparison)

    print(f"Файлы сохранены:")


if __name__ == "__main__":
    main()
