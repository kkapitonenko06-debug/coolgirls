from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path.cwd() / ".matplotlib-cache"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def plot_drink_cost_structure(supplier_costs: pd.DataFrame, output_path: Path) -> None:
    by_category = (
        supplier_costs.groupby("category", as_index=False)["cost_per_drink_rub"]
        .sum()
        .sort_values("cost_per_drink_rub", ascending=True)
    )
    _barh(by_category["category"], by_category["cost_per_drink_rub"], output_path, "Структура себестоимости одного стакана", "Рублей на 1 напиток")


def plot_monthly_staff_cost(staff_costs: pd.DataFrame, output_path: Path) -> None:
    ordered = staff_costs.sort_values("total_cost_rub", ascending=True)
    _barh(ordered["position"], ordered["total_cost_rub"], output_path, "Месячная стоимость сотрудников для компании", "Рублей в месяц")


def plot_supplier_category_coverage(coverage: pd.DataFrame, output_path: Path) -> None:
    pivot = coverage.pivot_table(
        index="category",
        columns="supplier_name",
        values="products_count",
        fill_value=0,
        aggfunc="sum",
    ).sort_index()
    fig, ax = plt.subplots(figsize=(10, 6))
    pivot.plot(kind="bar", ax=ax, width=0.78)
    ax.set_title("Ассортимент поставщиков по категориям")
    ax.set_xlabel("")
    ax.set_ylabel("Количество найденных товаров")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(title="Поставщик")
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def plot_supplier_price_ranges(products: pd.DataFrame, output_path: Path) -> None:
    by_category = (
        products.groupby("category", as_index=False)
        .agg(median_price_rub=("price_rub", "median"))
        .sort_values("median_price_rub", ascending=True)
    )
    _barh(by_category["category"], by_category["median_price_rub"], output_path, "Медианная цена товаров поставщиков по категориям", "Рублей за товарную позицию")


def plot_trudvsem_salary_medians(summary: pd.DataFrame, output_path: Path) -> None:
    ordered = summary.sort_values("median_salary_rub", ascending=True)
    _barh(ordered["target_position"], ordered["median_salary_rub"], output_path, "Медианная зарплата по вакансиям Работа России", "Рублей в месяц")


def _barh(labels, values, output_path: Path, title: str, xlabel: str) -> None:
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(labels, values, color="#476f95")
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)

