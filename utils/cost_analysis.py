
import math

import pandas as pd

INSURANCE_RATE = 0.302
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

def build_recipe_costs(recipe: pd.DataFrame, prices: pd.DataFrame):
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

def add_drink_costs(suppliers: pd.DataFrame):
    result = suppliers.copy()
    result["cost_per_drink_rub"] = (
        result["amount_per_drink"] * result["unit_price_rub"]
    )
    return result

def summarize_monthly_purchase(
    suppliers: pd.DataFrame,
    drinks_per_day: int = 120,
    working_days: int = 30,
):
    if "cost_per_drink_rub" in suppliers.columns:
        result = suppliers.copy()
    else:
        result = add_drink_costs(suppliers)

    monthly_drinks = drinks_per_day * working_days
    amount_column = (
        "amount_per_drink_base"
        if "amount_per_drink_base" in result.columns
        else "amount_per_drink"
    )
    result["monthly_amount"] = result[amount_column] * monthly_drinks

    if "pack_amount_base" in result.columns:
        result["packs_needed"] = result["monthly_amount"] / result["pack_amount_base"]
        result["monthly_cost_rub"] = result["packs_needed"] * result["pack_price_rub"]
        result["packs_to_buy"] = result["packs_needed"].apply(math.ceil)
        result["monthly_purchase_cost_rub"] = (
            result["packs_to_buy"] * result["pack_price_rub"]
        )
    else:
        result["monthly_cost_rub"] = result["cost_per_drink_rub"] * monthly_drinks
    return result

def add_staff_total_cost(staff: pd.DataFrame):
    result = staff.copy()
    result["salary_fund_rub"] = result["headcount"] * result["monthly_salary_rub"]
    result["insurance_payments_rub"] = result["salary_fund_rub"] * INSURANCE_RATE
    result["total_cost_rub"] = (
        result["salary_fund_rub"] + result["insurance_payments_rub"]
    )
    return result
