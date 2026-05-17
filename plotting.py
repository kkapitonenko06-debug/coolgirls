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

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(by_category["category"], by_category["cost_per_drink_rub"], color="#2f8f83")
    ax.set_title("Структура себестоимости одного стакана")
    ax.set_xlabel("Рублей на 1 напиток")
    ax.set_ylabel("")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def plot_monthly_staff_cost(staff_costs: pd.DataFrame, output_path: Path) -> None:
    ordered = staff_costs.sort_values("total_cost_rub", ascending=True)

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(ordered["position"], ordered["total_cost_rub"], color="#8f5c2f")
    ax.set_title("Месячная стоимость сотрудников для компании")
    ax.set_xlabel("Рублей в месяц")
    ax.set_ylabel("")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


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


def plot_salary_by_position(vacancies: pd.DataFrame, output_path: Path) -> None:
    data = vacancies.dropna(subset=["salary_mid"]).copy()
    positions = sorted(data["target_position"].unique())
    values = [
        data.loc[data["target_position"] == position, "salary_mid"].tolist()
        for position in positions
    ]

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.boxplot(values, tick_labels=positions, patch_artist=True)
    ax.set_title("Распределение зарплат по вакансиям в Москве")
    ax.set_xlabel("")
    ax.set_ylabel("Рублей в месяц")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def plot_staff_market_salary_sources(salaries: pd.DataFrame, output_path: Path) -> None:
    ordered = salaries.sort_values("salary_rub", ascending=True)

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.barh(ordered["position"], ordered["salary_rub"], color="#476f95")
    ax.set_title("Оценка рыночной зарплаты сотрудников")
    ax.set_xlabel("Рублей в месяц")
    ax.set_ylabel("")
    ax.grid(axis="x", alpha=0.25)
    for index, value in enumerate(ordered["salary_rub"]):
        ax.text(value + 1000, index, f"{value:,.0f}".replace(",", " "), va="center")
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def plot_supplier_price_ranges(products: pd.DataFrame, output_path: Path) -> None:
    by_category = (
        products.groupby("category", as_index=False)
        .agg(median_price_rub=("price_rub", "median"))
        .sort_values("median_price_rub", ascending=True)
    )

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.barh(by_category["category"], by_category["median_price_rub"], color="#6b7f3f")
    ax.set_title("Медианная цена товаров поставщиков по категориям")
    ax.set_xlabel("Рублей за товарную позицию")
    ax.set_ylabel("")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def plot_trudvsem_salary_medians(summary: pd.DataFrame, output_path: Path) -> None:
    ordered = summary.sort_values("median_salary_rub", ascending=True)

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(ordered["target_position"], ordered["median_salary_rub"], color="#7b5ea7")
    ax.set_title("Медианная зарплата по вакансиям Работа России")
    ax.set_xlabel("Рублей в месяц")
    ax.set_ylabel("")
    ax.grid(axis="x", alpha=0.25)
    for index, value in enumerate(ordered["median_salary_rub"]):
        ax.text(value + 1000, index, f"{value:,.0f}".replace(",", " "), va="center")
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)
