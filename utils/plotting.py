
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path.cwd() / ".matplotlib-cache"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd

# Палитра и стиль

PALETTE = {
    "cost":       "#2563eb",   #себестоимость --- синий
    "price":      "#16a34a",   #наша цена --- зелёный
    "market":     "#d97706",   #конкуренты --- оранжевый
    "staff":      "#8f5c2f",   #персонал --- коричневый
    "supplier":   "#476f95",   #поставщики --- какой-то другой синий синий
    "salary":     "#7b5ea7",   #зарплаты --- фиолетовый
    "segment": {
        "бюджет":  "#60a5fa",
        "средний": "#34d399",
        "премиум": "#f87171",
    },
}

CATEGORY_COLORS = [
    "#2563eb", "#16a34a", "#d97706", "#7b5ea7",
    "#db2777", "#0891b2", "#65a30d", "#dc2626",
]

def _style(ax: plt.Axes, title: str, xlabel: str = "", ylabel: str = ""):
    ax.set_title(title, fontsize=13, fontweight="bold", pad=10)
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=10)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=10)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(labelsize=9)

def _add_barh_labels(ax: plt.Axes, values, fmt="{:.0f} ₽", offset_frac: float = 0.01):
    x_max = ax.get_xlim()[1]
    offset = x_max * offset_frac
    for i, v in enumerate(values):
        label = fmt(v) if callable(fmt) else fmt.format(v)
        ax.text(v + offset, i, label, va="center", fontsize=8.5, color="#374151")

def _save(fig: plt.Figure, path: Path):
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)

#Себестоимость напитков

def plot_drink_cost_structure(supplier_costs: pd.DataFrame, output_path: Path):
    by_category = (
        supplier_costs.groupby("category", as_index=False)["cost_per_drink_rub"]
        .mean()
        .sort_values("cost_per_drink_rub", ascending=True)
    )
    fig, ax = plt.subplots(figsize=(9, 5))
    bars = ax.barh(by_category["category"], by_category["cost_per_drink_rub"],
                   color=PALETTE["cost"], alpha=0.85)
    _style(ax, "Себестоимость по категориям ингредиентов\n(среднее на 1 напиток)",
           xlabel="₽ на 1 напиток")
    ax.grid(axis="x", alpha=0.2, linestyle="--")
    _add_barh_labels(ax, by_category["cost_per_drink_rub"], fmt="{:.1f} ₽")
    _save(fig, output_path)

def plot_drink_cost_vs_market_price(drink_costs: pd.DataFrame, output_path: Path):
    drinks = drink_costs["drink_name"].tolist()
    costs   = drink_costs["total_cost_rub"].tolist()
    medians = drink_costs["market_median_rub"].tolist()
    prices  = drink_costs["recommended_price_rub"].tolist()

    x = np.arange(len(drinks))
    width = 0.26

    fig, ax = plt.subplots(figsize=(12, 6))
    b1 = ax.bar(x - width, costs,   width, label="Себестоимость",      color=PALETTE["cost"],   alpha=0.9)
    b2 = ax.bar(x,          medians, width, label="Медиана рынка",       color=PALETTE["market"], alpha=0.9)
    b3 = ax.bar(x + width,  prices,  width, label="Наша рекомендованная цена", color=PALETTE["price"],  alpha=0.9)

    for bar in [b1, b2, b3]:
        for rect in bar:
            h = rect.get_height()
            ax.text(rect.get_x() + rect.get_width() / 2, h + 5,
                    f"{h:.0f}₽", ha="center", va="bottom", fontsize=7.5)

    ax.set_xticks(x)
    ax.set_xticklabels(drinks, rotation=15, ha="right", fontsize=9)
    _style(ax, "Себестоимость, рыночная цена и наша рекомендация", ylabel="₽")
    ax.legend(fontsize=9)
    ax.grid(axis="y", alpha=0.2, linestyle="--")
    ax.set_ylim(0, max(prices) * 1.18)
    _save(fig, output_path)

def plot_ingredient_breakdown_by_drink(ingredient_costs: pd.DataFrame, output_path: Path):
    pivot = (
        ingredient_costs.groupby(["drink_name", "category"])["cost_per_drink_rub"]
        .sum()
        .unstack(fill_value=0)
    )
    #Сортируем по суммарной себестоимости
    pivot = pivot.loc[pivot.sum(axis=1).sort_values().index]

    categories = list(pivot.columns)
    colors = CATEGORY_COLORS[: len(categories)]

    fig, ax = plt.subplots(figsize=(11, 5))
    left = np.zeros(len(pivot))
    for cat, color in zip(categories, colors):
        vals = pivot[cat].values
        bars = ax.barh(pivot.index, vals, left=left, label=cat, color=color, alpha=0.88)
        for i, (v, l) in enumerate(zip(vals, left)):
            if v > 2:
                ax.text(l + v / 2, i, f"{v:.0f}", ha="center", va="center",
                        fontsize=7, color="white", fontweight="bold")
        left += vals

    for i, total in enumerate(pivot.sum(axis=1)):
        ax.text(total + 1, i, f"{total:.0f} ₽", va="center", fontsize=8.5, color="#374151")

    ax.set_xlim(0, pivot.sum(axis=1).max() * 1.15)
    _style(ax, "Разбивка себестоимости по категориям ингредиентов", xlabel="₽ на 1 напиток")
    ax.legend(loc="lower right", fontsize=8, ncol=2)
    ax.grid(axis="x", alpha=0.15, linestyle="--")
    _save(fig, output_path)


def plot_competitor_segments(benchmark: pd.DataFrame, drink_costs: pd.DataFrame,
                             output_path: Path):
    segments = ["бюджет", "средний", "премиум"]
    seg_colors = [PALETTE["segment"][s] for s in segments]

    data_by_seg = [
        benchmark.loc[benchmark["segment"] == s, "price_rub"].dropna().tolist()
        for s in segments
    ]

    fig, ax = plt.subplots(figsize=(10, 6))

    bp = ax.boxplot(
        data_by_seg,
        patch_artist=True,
        widths=0.5,
        medianprops=dict(color="black", linewidth=2),
        whiskerprops=dict(linewidth=1.2),
        capprops=dict(linewidth=1.2),
        flierprops=dict(marker="o", markersize=4, alpha=0.5),
    )
    for patch, color in zip(bp["boxes"], seg_colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.55)

    #Наши цены -- горизонтальные маркеры
    our_prices = drink_costs["recommended_price_rub"].tolist()
    our_names  = drink_costs["drink_name"].tolist()
    jitter_x   = np.linspace(0.62, 1.38, len(our_prices))  # разброс внутри бюджетной зоны

    for i, (price, name) in enumerate(zip(our_prices, our_names)):
        #Определяем, в каком сегменте лежит наша цена
        seg_limits = benchmark.groupby("segment")["price_rub"].max()
        if price <= seg_limits.get("бюджет", 400):
            x_pos = 1
        elif price <= seg_limits.get("средний", 500):
            x_pos = 2
        else:
            x_pos = 3
        x_jitter = x_pos + (i - len(our_prices) / 2) * 0.07
        ax.scatter(x_jitter, price, s=90, zorder=5,
                   color=PALETTE["price"], edgecolors="white", linewidths=0.8)
        short = name.split(" ")[0]
        ax.annotate(f"{short}\n{price:.0f}₽",
                    xy=(x_jitter, price),
                    xytext=(x_jitter + 0.12, price),
                    fontsize=7.5, color=PALETTE["price"],
                    va="center",
                    arrowprops=dict(arrowstyle="-", color=PALETTE["price"], lw=0.8))

    ax.set_xticks([1, 2, 3])
    ax.set_xticklabels(["Бюджет", "Средний", "Премиум"], fontsize=11)
    _style(ax, "Цены конкурентов по сегментам и наши рекомендованные цены",
           ylabel="₽ за напиток")
    ax.grid(axis="y", alpha=0.2, linestyle="--")

    legend_handles = [
        mpatches.Patch(facecolor=c, alpha=0.55, label=s.capitalize())
        for s, c in zip(segments, seg_colors)
    ] + [
        plt.Line2D([0], [0], marker="o", color="w",
                   markerfacecolor=PALETTE["price"], markersize=9,
                   label="Наши цены")
    ]
    ax.legend(handles=legend_handles, fontsize=9)
    _save(fig, output_path)

def plot_competitor_price_scatter(benchmark: pd.DataFrame, output_path: Path):
    #Strip plot -- каждый напиток конкурента как точка. По оси Y конкурент, по оси X цена.Помогает увидеть разброс меню у каждого заведения
    competitors = (
        benchmark.groupby("competitor")["price_rub"]
        .median()
        .sort_values()
        .index.tolist()
    )
    seg_color_map = benchmark.set_index("competitor")["segment"].to_dict()

    fig, ax = plt.subplots(figsize=(11, 6))

    for i, comp in enumerate(competitors):
        prices = benchmark.loc[benchmark["competitor"] == comp, "price_rub"].values
        seg    = benchmark.loc[benchmark["competitor"] == comp, "segment"].iloc[0]
        color  = PALETTE["segment"].get(seg, "#888888")
        jitter = np.random.uniform(-0.25, 0.25, size=len(prices))
        ax.scatter(prices, [i + j for j in jitter], color=color, alpha=0.75,
                   s=45, edgecolors="white", linewidths=0.5)
        #Медиана
        ax.scatter(np.median(prices), i, color=color, s=120, marker="|",
                   linewidths=2.5, zorder=5)

    ax.set_yticks(range(len(competitors)))
    ax.set_yticklabels(competitors, fontsize=9)
    ax.set_xlabel("₽", fontsize=10)
    _style(ax, "Разброс цен в меню конкурентов\n(| = медиана, точки = позиции)")
    ax.grid(axis="x", alpha=0.2, linestyle="--")

    legend_handles = [
        mpatches.Patch(facecolor=PALETTE["segment"][s], alpha=0.75, label=s.capitalize())
        for s in ["бюджет", "средний", "премиум"]
    ]
    ax.legend(handles=legend_handles, fontsize=9, title="Сегмент")
    _save(fig, output_path)


def plot_supplier_category_coverage(coverage: pd.DataFrame, output_path: Path):
    pivot = coverage.pivot_table(
        index="category",
        columns="supplier_name",
        values="products_count",
        fill_value=0,
        aggfunc="sum",
    ).sort_index()

    fig, ax = plt.subplots(figsize=(11, 6))
    pivot.plot(kind="bar", ax=ax, width=0.78, colormap="tab10")
    _style(ax, "Ассортимент поставщиков по категориям", ylabel="Найдено товаров")
    ax.set_xlabel("")
    plt.xticks(rotation=30, ha="right", fontsize=9)
    ax.grid(axis="y", alpha=0.2, linestyle="--")
    ax.legend(title="Поставщик", fontsize=8)
    _save(fig, output_path)

def plot_supplier_serving_cost(comparison: pd.DataFrame, output_path: Path):
    best = (
        comparison.groupby("category", as_index=False)
        .agg(
            min_cost=("cost_per_serving_min", "min"),
            med_cost=("cost_per_serving_median", "min"),
        )
        .sort_values("med_cost", ascending=True)
    )

    fig, ax = plt.subplots(figsize=(10, 6))
    y = np.arange(len(best))
    ax.barh(y, best["med_cost"], color=PALETTE["supplier"], alpha=0.75,
            label="Медиана (лучший поставщик)")
    ax.barh(y, best["min_cost"], color=PALETTE["cost"], alpha=0.9,
            label="Минимум (лучший поставщик)")

    ax.set_yticks(y)
    ax.set_yticklabels(best["category"], fontsize=9)
    _style(ax, "Стоимость порции ингредиента у лучших поставщиков", xlabel="₽ на порцию")
    ax.grid(axis="x", alpha=0.2, linestyle="--")
    ax.legend(fontsize=9)
    _add_barh_labels(ax, best["med_cost"], fmt="{:.1f} ₽")
    _save(fig, output_path)

def plot_supplier_price_ranges(products: pd.DataFrame, output_path: Path):
    """Медианная цена товаров поставщиков по категориям."""
    by_category = (
        products.groupby("category", as_index=False)
        .agg(median_price_rub=("price_rub", "median"))
        .sort_values("median_price_rub", ascending=True)
    )
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.barh(by_category["category"], by_category["median_price_rub"],
            color="#6b7f3f", alpha=0.85)
    _style(ax, "Медианная цена товаров поставщиков по категориям",
           xlabel="₽ за товарную позицию")
    ax.grid(axis="x", alpha=0.2, linestyle="--")
    _add_barh_labels(ax, by_category["median_price_rub"], fmt="{:.0f} ₽")
    _save(fig, output_path)

def plot_monthly_ingredient_costs(monthly: pd.DataFrame, output_path: Path):
    #Горизонтальные бары: ежемесячные затраты на ингредиенты по категориям
    by_cat = (
        monthly.groupby("category", as_index=False)["monthly_cost_rub"]
        .sum()
        .sort_values("monthly_cost_rub", ascending=True)
    )
    total = by_cat["monthly_cost_rub"].sum()

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.barh(by_cat["category"], by_cat["monthly_cost_rub"],
                   color=PALETTE["cost"], alpha=0.82)
    _style(ax, f"Ежемесячные затраты на ингредиенты по категориям\n(итого: {total:,.0f} ₽)".replace(",", " "),
           xlabel="₽ в месяц")
    ax.grid(axis="x", alpha=0.2, linestyle="--")

    x_max = by_cat["monthly_cost_rub"].max()
    for i, (val, cat) in enumerate(zip(by_cat["monthly_cost_rub"], by_cat["category"])):
        pct = val / total * 100
        ax.text(val + x_max * 0.01, i,
                f"{val:,.0f} ₽  ({pct:.1f}%)".replace(",", " "),
                va="center", fontsize=8.5, color="#374151")
    ax.set_xlim(0, x_max * 1.35)
    _save(fig, output_path)


def plot_monthly_staff_cost(staff_costs: pd.DataFrame, output_path: Path):
    #Затраты на персонал по должностям (включая налоги и взносы)
    ordered = staff_costs.sort_values("total_cost_rub", ascending=True)
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(ordered["position"], ordered["total_cost_rub"],
            color=PALETTE["staff"], alpha=0.85)
    _style(ax, "Месячная стоимость персонала для компании\n(зарплата + страховые взносы)",
           xlabel="₽ в месяц")
    ax.grid(axis="x", alpha=0.2, linestyle="--")
    _add_barh_labels(ax, ordered["total_cost_rub"],
                     fmt=lambda v: f"{v:,.0f} ₽".replace(",", " "))
    _save(fig, output_path)

def plot_salary_by_position(vacancies: pd.DataFrame, output_path: Path):
    data = vacancies.dropna(subset=["salary_mid"]).copy()
    positions = sorted(data["target_position"].unique())
    values = [
        data.loc[data["target_position"] == pos, "salary_mid"].tolist()
        for pos in positions
    ]
    fig, ax = plt.subplots(figsize=(9, 5))
    bp = ax.boxplot(values, patch_artist=True,
                    medianprops=dict(color="black", linewidth=2),
                    flierprops=dict(marker="o", markersize=4, alpha=0.5))
    for patch in bp["boxes"]:
        patch.set_facecolor(PALETTE["salary"])
        patch.set_alpha(0.55)
    ax.set_xticks(range(1, len(positions) + 1))
    ax.set_xticklabels(positions, rotation=20, ha="right", fontsize=9)
    _style(ax, "Распределение зарплат по вакансиям в Москве (hh.ru)",
           ylabel="₽ в месяц")
    ax.grid(axis="y", alpha=0.2, linestyle="--")
    _save(fig, output_path)

def plot_staff_market_salary_sources(salaries: pd.DataFrame, output_path: Path):
    ordered = salaries.sort_values("salary_rub", ascending=True)
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.barh(ordered["position"], ordered["salary_rub"],
            color=PALETTE["supplier"], alpha=0.85)
    _style(ax, "Оценка рыночной зарплаты сотрудников", xlabel="₽ в месяц")
    ax.grid(axis="x", alpha=0.2, linestyle="--")
    x_max = ordered["salary_rub"].max()
    for i, v in enumerate(ordered["salary_rub"]):
        ax.text(v + x_max * 0.01, i,
                f"{v:,.0f} ₽".replace(",", " "), va="center", fontsize=8.5)
    _save(fig, output_path)

def plot_trudvsem_salary_medians(summary: pd.DataFrame, output_path: Path):
    ordered = summary.sort_values("median_salary_rub", ascending=True)
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(ordered["target_position"], ordered["median_salary_rub"],
            color=PALETTE["salary"], alpha=0.85)
    _style(ax, "Медианная зарплата по вакансиям «Работа России»", xlabel="₽ в месяц")
    ax.grid(axis="x", alpha=0.2, linestyle="--")
    x_max = ordered["median_salary_rub"].max()
    for i, v in enumerate(ordered["median_salary_rub"]):
        ax.text(v + x_max * 0.01, i,
                f"{v:,.0f} ₽".replace(",", " "), va="center", fontsize=8.5)
    _save(fig, output_path)
