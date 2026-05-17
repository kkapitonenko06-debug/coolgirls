from __future__ import annotations

import math
from pathlib import Path

import pandas as pd


INSURANCE_RATE = 0.302

#Приводим разные единицы к базовым, чтобы граммы и килограммы нормально считались
UNIT_TO_BASE = {
    "g": ("g", 1),
    "kg": ("g", 1000),
    "ml": ("ml", 1),
    "l": ("ml", 1000),
    "pcs": ("pcs", 1),
    "шт": ("pcs", 1),
}


def convert_to_base(amount: float, unit: str) -> tuple[float, str]:
    base_unit, multiplier = UNIT_TO_BASE[unit]
    return amount * multiplier, base_unit


def build_recipe_costs(recipe: pd.DataFrame, prices: pd.DataFrame) -> pd.DataFrame:
    #Соединяем рецепт напитка с выбранными товарами
    result = recipe.merge(prices, on="ingredient_key", how="left", validate="one_to_one")
    if result["pack_price_rub"].isna().any():
        missing = result.loc[result["pack_price_rub"].isna(), "ingredient_key"].tolist()
        raise ValueError(f"No supplier price for ingredients: {missing}")

    pack_base = result.apply(
        lambda row: convert_to_base(row["pack_amount"], row["pack_unit"]),
        axis=1,
        result_type="expand",
    )
    recipe_base = result.apply(
        lambda row: convert_to_base(row["amount_per_drink"], row["amount_unit"]),
        axis=1,
        result_type="expand",
    )

    result["pack_amount_base"] = pack_base[0]
    result["pack_base_unit"] = pack_base[1]
    result["amount_per_drink_base"] = recipe_base[0]
    result["recipe_base_unit"] = recipe_base[1]

    unit_mismatch = result["pack_base_unit"] != result["recipe_base_unit"]
    if unit_mismatch.any():
        bad_rows = result.loc[unit_mismatch, ["ingredient_key", "pack_unit", "amount_unit"]]
        raise ValueError(f"Unit mismatch in recipe/prices:\n{bad_rows}")

    result["unit_price_rub"] = result["pack_price_rub"] / result["pack_amount_base"]
    result["cost_per_drink_rub"] = (
        result["amount_per_drink_base"] * result["unit_price_rub"]
    )
    result["drinks_per_pack"] = (
        result["pack_amount_base"] / result["amount_per_drink_base"]
    )
    return result


def summarize_monthly_purchase(
    supplier_costs: pd.DataFrame,
    drinks_per_day: int = 120,
    working_days: int = 30,
) -> pd.DataFrame:
    result = supplier_costs.copy()
    monthly_drinks = drinks_per_day * working_days

    #packs_needed может быть дробным, packs_to_buy округляется до целых упаковок
    result["monthly_amount"] = result["amount_per_drink_base"] * monthly_drinks
    result["packs_needed"] = result["monthly_amount"] / result["pack_amount_base"]
    result["packs_to_buy"] = result["packs_needed"].apply(math.ceil)
    result["monthly_cost_rub"] = result["cost_per_drink_rub"] * monthly_drinks
    result["monthly_purchase_cost_rub"] = result["packs_to_buy"] * result["pack_price_rub"]
    return result


def build_staff_costs() -> pd.DataFrame:
    staff = pd.DataFrame(
        [
            {
                "position": "Бариста",
                "headcount": 3,
                "monthly_salary_rub": 70000,
                "schedule": "2/2",
            },
            {
                "position": "Кассир",
                "headcount": 2,
                "monthly_salary_rub": 60000,
                "schedule": "2/2",
            },
            {
                "position": "Администратор смены",
                "headcount": 1,
                "monthly_salary_rub": 85000,
                "schedule": "5/2",
            },
        ]
    )
    staff["salary_fund_rub"] = staff["headcount"] * staff["monthly_salary_rub"]
    staff["insurance_payments_rub"] = staff["salary_fund_rub"] * INSURANCE_RATE
    staff["total_cost_rub"] = staff["salary_fund_rub"] + staff["insurance_payments_rub"]
    return staff


def analyze_supplier_categories(products: pd.DataFrame, output_path: Path) -> pd.DataFrame:
    #Смотрим у кого из поставщиков какие категории товаров представлены
    coverage = (
        products.groupby(["supplier_name", "category"], as_index=False)
        .agg(products_count=("product_name", "nunique"))
        .sort_values(["supplier_name", "products_count"], ascending=[True, False])
    )
    coverage.to_csv(output_path, index=False)
    return coverage


def analyze_supplier_prices(products: pd.DataFrame, output_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    #Не все цены на сайте -- это цены товаров, поэтому ниже фильтрация
    priced = products.dropna(subset=["price_rub"]).copy()
    priced = priced[priced.apply(_is_reasonable_price, axis=1)]
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
    summary.to_csv(output_path, index=False)
    return priced, summary


def analyze_counterparty_risks(counterparties: pd.DataFrame, output_path: Path) -> pd.DataFrame:
    #Если юрлицо активно и есть реквизиты, то рассматривем его
    summary = counterparties.copy()
    summary["status_score"] = summary["status"].apply(_score_status)
    summary["has_inn"] = summary["inn"].notna()
    summary["has_ogrn"] = summary["ogrn"].notna()
    summary["risk_comment"] = summary.apply(
        lambda row: (
            "Можно рассматривать"
            if row["status_score"] == 2 and row["has_inn"] and row["has_ogrn"]
            else "Нужна ручная проверка"
        ),
        axis=1,
    )
    summary.to_csv(output_path, index=False)
    return summary


def analyze_trudvsem_salaries(vacancies: pd.DataFrame, output_path: Path) -> pd.DataFrame:
    vacancies = vacancies.copy()

    #Если есть вилка зарплат, то берем среднее значение
    vacancies["salary_mid"] = vacancies[["salary_min", "salary_max"]].mean(axis=1)
    vacancies = vacancies.dropna(subset=["salary_mid"])
    vacancies = vacancies[vacancies["salary_mid"] > 0]
    summary = (
        vacancies.groupby("target_position", as_index=False)
        .agg(
            vacancies_count=("vacancy_id", "nunique"),
            companies_count=("company_inn", "nunique"),
            median_salary_rub=("salary_mid", "median"),
            mean_salary_rub=("salary_mid", "mean"),
            min_salary_rub=("salary_mid", "min"),
            max_salary_rub=("salary_mid", "max"),
        )
        .sort_values("median_salary_rub", ascending=False)
    )
    summary.to_csv(output_path, index=False)
    return summary


def _is_reasonable_price(row: pd.Series) -> bool:
    price = row["price_rub"]
    if pd.isna(price):
        return False
    if row["category"] == "Упаковка":
        return price >= 1
    return price >= 50


def _score_status(status: str | float | None) -> int:
    if not isinstance(status, str):
        return 0
    if status.upper() == "ACTIVE":
        return 2
    if status.upper() in {"LIQUIDATING", "REORGANIZING"}:
        return 1
    return 0
