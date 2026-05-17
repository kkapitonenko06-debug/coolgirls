from pathlib import Path
import os

import pandas as pd

from analysis import (
    analyze_counterparty_risks,
    analyze_supplier_categories,
    analyze_supplier_prices,
    analyze_trudvsem_salaries,
    build_recipe_costs,
    build_staff_costs,
    summarize_monthly_purchase,
)
from api_clients import (
    collect_dadata_counterparties,
    collect_trudvsem_vacancies,
    load_env_file,
)
from plotting import (
    plot_drink_cost_structure,
    plot_monthly_staff_cost,
    plot_supplier_category_coverage,
    plot_supplier_price_ranges,
    plot_trudvsem_salary_medians,
)
from scraping import SupplierProductParser


ROOT = Path(__file__).parent
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
PLOTS_DIR = ROOT / "plots"


def prepare_folders() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)


def collect_supplier_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    # Сбор и обработка данных о товарах поставщиков
    supplier_products = SupplierProductParser().parse_sources(RAW_DIR / "supplier_sources.csv")
    supplier_products.to_csv(RAW_DIR / "supplier_products_parsed.csv", index=False)

    coverage = analyze_supplier_categories(
        supplier_products,
        PROCESSED_DIR / "supplier_category_coverage.csv",
    )
    priced_products, _ = analyze_supplier_prices(
        supplier_products,
        PROCESSED_DIR / "supplier_price_summary.csv",
    )
    return supplier_products, coverage, priced_products


def collect_counterparty_data() -> None:
    # Проверка потенциальных контрагентов через сайт DaData
    api_key = os.getenv("DADATA_API_KEY")
    if not api_key:
        print("DADATA_API_KEY не найден: блок DaData пропущен.")
        return

    queries = pd.read_csv(RAW_DIR / "counterparty_queries.csv")
    counterparties = collect_dadata_counterparties(queries, api_key)
    counterparties.to_csv(RAW_DIR / "dadata_counterparties.csv", index=False)
    analyze_counterparty_risks(
        counterparties,
        PROCESSED_DIR / "counterparty_risk_summary.csv",
    )


def collect_vacancy_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    # Сбор вакансий для оценки зарплат сотрудников
    vacancies = collect_trudvsem_vacancies()
    vacancies.to_csv(RAW_DIR / "trudvsem_vacancies_moscow.csv", index=False)
    salary_summary = analyze_trudvsem_salaries(
        vacancies,
        PROCESSED_DIR / "trudvsem_salary_summary.csv",
    )
    return vacancies, salary_summary


def calculate_costs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    # Расчет себестоимости одного напитка, месячных закупок и стоимости сотрудников
    recipe = pd.read_csv(RAW_DIR / "drink_recipe.csv")
    selected_prices = pd.read_csv(RAW_DIR / "selected_supplier_prices.csv")

    supplier_costs = build_recipe_costs(recipe, selected_prices)
    monthly_purchase = summarize_monthly_purchase(supplier_costs)
    staff_costs = build_staff_costs()

    supplier_costs.to_csv(PROCESSED_DIR / "supplier_costs.csv", index=False)
    monthly_purchase.to_csv(PROCESSED_DIR / "monthly_purchase_plan.csv", index=False)
    staff_costs.to_csv(PROCESSED_DIR / "staff_costs.csv", index=False)
    return supplier_costs, monthly_purchase, staff_costs


def build_plots(
    coverage: pd.DataFrame,
    priced_products: pd.DataFrame,
    salary_summary: pd.DataFrame,
    supplier_costs: pd.DataFrame,
    staff_costs: pd.DataFrame,
) -> None:
    # Построение графиков
    plot_supplier_category_coverage(coverage, PLOTS_DIR / "supplier_category_coverage.png")
    plot_supplier_price_ranges(priced_products, PLOTS_DIR / "supplier_price_ranges.png")
    plot_trudvsem_salary_medians(salary_summary, PLOTS_DIR / "trudvsem_salary_medians.png")
    plot_drink_cost_structure(supplier_costs, PLOTS_DIR / "drink_cost_structure.png")
    plot_monthly_staff_cost(staff_costs, PLOTS_DIR / "monthly_staff_cost.png")


def print_results(
    supplier_products: pd.DataFrame,
    vacancies: pd.DataFrame,
    supplier_costs: pd.DataFrame,
    monthly_purchase: pd.DataFrame,
    staff_costs: pd.DataFrame,
) -> None:
    drink_cost = supplier_costs["cost_per_drink_rub"].sum()
    monthly_purchase_cost = monthly_purchase["monthly_purchase_cost_rub"].sum()
    monthly_staff_cost = staff_costs["total_cost_rub"].sum()

    print()
    print("Итоги анализа:")
    print(f"Товарных строк поставщиков: {len(supplier_products)}")
    print(f"Вакансий Работа России: {len(vacancies)}")
    print(f"Себестоимость 1 стакана: {drink_cost:.2f} руб.")
    print(f"Закупки на месяц: {monthly_purchase_cost:.2f} руб.")
    print(f"Total cost сотрудников в месяц: {monthly_staff_cost:.2f} руб.")


def main() -> None:
    prepare_folders()
    load_env_file(ROOT / ".env")

    supplier_products, coverage, priced_products = collect_supplier_data()
    collect_counterparty_data()
    vacancies, salary_summary = collect_vacancy_data()
    supplier_costs, monthly_purchase, staff_costs = calculate_costs()
    build_plots(coverage, priced_products, salary_summary, supplier_costs, staff_costs)
    print_results(supplier_products, vacancies, supplier_costs, monthly_purchase, staff_costs)


if __name__ == "__main__":
    main()
