#Это генерация всех графиков для анализа бабл-тишки. Результат в папке plots

import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path.cwd() / ".matplotlib-cache"))
import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd

ROOT = Path(__file__).parent
DATA = ROOT / "data" / "processed"
PLOTS = ROOT / "plots"
PLOTS.mkdir(exist_ok=True)

#Себестоимость по категориям ингредиентов

def plot_cost_by_category(ingredient_costs): # считаем среднюю стоимость по категориям
    by_cat = ingredient_costs.groupby("category")["cost_per_drink_rub"].mean()
    by_cat = by_cat.sort_values()

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(by_cat.index, by_cat.values, color="steelblue")

    for i, v in enumerate(by_cat.values):
        ax.text(v + 0.3, i, f"{v:.1f} ₽", va="center", fontsize=9)

    ax.set_title("Себестоимость по категориям ингредиентов (среднее на 1 напиток)")
    ax.set_xlabel("₽")
    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    fig.savefig(PLOTS / "drink_cost_structure.png", dpi=150)
    plt.close()

#Разбивка себестоимости по категориям для каждого напитка

def plot_ingredient_breakdown(ingredient_costs):
#делаем сводную таблицу: напиток категория
    pivot = ingredient_costs.groupby(["drink_name", "category"])["cost_per_drink_rub"].sum()
    pivot = pivot.unstack(fill_value=0)

    #сортируем напитки по суммарной себестоимости
    order = pivot.sum(axis=1).sort_values().index
    pivot = pivot.loc[order]

    colors = ["steelblue", "seagreen", "darkorange", "mediumpurple",
              "crimson", "cadetblue", "olivedrab", "tomato"]

    fig, ax = plt.subplots(figsize=(11, 5))
    left = np.zeros(len(pivot))

    for cat, color in zip(pivot.columns, colors):
        vals = pivot[cat].values
        ax.barh(pivot.index, vals, left=left, label=cat, color=color, alpha=0.85)

        for i, (v, l) in enumerate(zip(vals, left)):
            if v > 2:
                ax.text(l + v / 2, i, f"{v:.0f}",
                        ha="center", va="center", fontsize=7.5,
                        color="white", fontweight="bold")
        left += vals

    for i, total in enumerate(pivot.sum(axis=1)):
        ax.text(total + 1, i, f"{total:.0f} ₽", va="center", fontsize=9)

    ax.set_title("Разбивка себестоимости по категориям ингредиентов")
    ax.set_xlabel("₽ на 1 напиток")
    ax.set_xlim(0, pivot.sum(axis=1).max() * 1.15)
    ax.legend(fontsize=8, ncol=2, loc="lower right")
    ax.grid(axis="x", alpha=0.2)
    fig.tight_layout()
    fig.savefig(PLOTS / "ingredient_breakdown_by_drink.png", dpi=150)
    plt.close()

#Себестоимость, медиана рынка и наша цена для каждого напитка

def plot_cost_vs_price(drink_costs):
    drinks  = drink_costs["drink_name"].tolist()
    costs   = drink_costs["total_cost_rub"].tolist()
    medians = drink_costs["market_median_rub"].tolist()
    prices  = drink_costs["recommended_price_rub"].tolist()

    x = np.arange(len(drinks))
    w = 0.26

    fig, ax = plt.subplots(figsize=(12, 6))

    b1 = ax.bar(x - w, costs,   w, label="Себестоимость",       color="steelblue",  alpha=0.9)
    b2 = ax.bar(x,     medians, w, label="Медиана рынка",        color="darkorange", alpha=0.9)
    b3 = ax.bar(x + w, prices,  w, label="Рекомендованная цена", color="seagreen",   alpha=0.9)

    for group in [b1, b2, b3]:
        for bar in group:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2, h + 4,
                    f"{h:.0f}₽", ha="center", va="bottom", fontsize=7.5)

    ax.set_xticks(x)
    ax.set_xticklabels(drinks, rotation=15, ha="right", fontsize=9)
    ax.set_title("Себестоимость, рыночная медиана и наша рекомендованная цена")
    ax.set_ylabel("₽")
    ax.legend(fontsize=9)
    ax.grid(axis="y", alpha=0.2)
    ax.set_ylim(0, max(prices) * 1.2)
    fig.tight_layout()
    fig.savefig(PLOTS / "drink_cost_vs_market_price.png", dpi=150)
    plt.close()

#Цены конкурентов по сегментам и наши цены (боксплот)

def plot_competitor_segments(benchmark, drink_costs):
    fig, ax = plt.subplots(figsize=(10, 6))

    order = ["бюджет", "средний", "премиум"]
    benchmark["segment_label"] = benchmark["segment"].map(
        {"бюджет": "Бюджет", "средний": "Средний", "премиум": "Премиум"}
    )
    sns.boxplot(
        data=benchmark,
        x="segment_label", y="price_rub",
        order=["Бюджет", "Средний", "Премиум"],
        hue="segment_label",
        palette={"Бюджет": "#60a5fa", "Средний": "#34d399", "Премиум": "#f87171"},
        width=0.5, legend=False,
        ax=ax
    )

    #наши цены поверх боксплотов
    seg_max = benchmark.groupby("segment")["price_rub"].max()
    for i, row in drink_costs.iterrows():
        price = row["recommended_price_rub"]
        name  = row["drink_name"].split()[0]

        if price <= seg_max.get("бюджет", 400):
            x_pos = 0
        elif price <= seg_max.get("средний", 500):
            x_pos = 1
        else:
            x_pos = 2

        x_j = x_pos + (i - len(drink_costs) / 2) * 0.07
        ax.scatter(x_j, price, s=80, color="darkgreen", zorder=5)
        ax.text(x_j + 0.08, price, f"{name} {price:.0f}₽",
                fontsize=8, color="darkgreen", va="center")

    ax.set_xticks([0, 1, 2])
    ax.set_xticklabels(["Бюджет", "Средний", "Премиум"], fontsize=11)
    ax.set_title("Цены конкурентов по сегментам и наши рекомендованные цены")
    ax.set_xlabel("")
    ax.set_ylabel("₽")
    ax.grid(axis="y", alpha=0.2)
    fig.tight_layout()
    fig.savefig(PLOTS / "competitor_segments.png", dpi=150)
    plt.close()

#Разброс цен в меню каждого конкурента

def plot_competitor_scatter(benchmark):
    #сортируем конкурентов по медианной цене
    order = (
        benchmark.groupby("competitor")["price_rub"]
        .median()
        .sort_values()
        .index.tolist()
    )

    fig, ax = plt.subplots(figsize=(11, 6))

    sns.stripplot(
        data=benchmark,
        x="price_rub", y="competitor",
        order=order,
        hue="segment",
        palette={"бюджет": "#60a5fa", "средний": "#34d399", "премиум": "#f87171"},
        jitter=True, size=6, alpha=0.75,
        ax=ax
    )

    ax.set_title("Разброс цен в меню конкурентов")
    ax.set_xlabel("₽")
    ax.set_ylabel("")
    ax.legend(title="Сегмент", fontsize=9)
    ax.grid(axis="x", alpha=0.2)
    fig.tight_layout()
    fig.savefig(PLOTS / "competitor_price_scatter.png", dpi=150)
    plt.close()

#Стоимость порции у лучших поставщиков по категориям

def plot_supplier_serving_cost(comparison):
    #берем минимальную и медианную стоимость порции по каждой категории
    best = comparison.groupby("category").agg(
        min_cost=("cost_per_serving_min", "min"),
        med_cost=("cost_per_serving_median", "min")
    ).sort_values("med_cost")

    fig, ax = plt.subplots(figsize=(10, 6))

    ax.barh(best.index, best["med_cost"], color="steelblue", alpha=0.7, label="Медиана")
    ax.barh(best.index, best["min_cost"], color="royalblue", alpha=0.9, label="Минимум")

    for i, v in enumerate(best["med_cost"]):
        ax.text(v + 0.2, i, f"{v:.1f} ₽", va="center", fontsize=9)

    ax.set_title("Стоимость порции ингредиента у лучших поставщиков")
    ax.set_xlabel("₽ на порцию")
    ax.legend(fontsize=9)
    ax.grid(axis="x", alpha=0.2)
    fig.tight_layout()
    fig.savefig(PLOTS / "supplier_serving_cost.png", dpi=150)
    plt.close()

#Ежемесячные затраты на ингредиенты по категориям

def plot_monthly_costs(monthly):
    by_cat = monthly.groupby("category")["monthly_cost_rub"].sum()
    by_cat = by_cat.sort_values()
    total  = by_cat.sum()

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.barh(by_cat.index, by_cat.values, color="steelblue", alpha=0.82)

    for i, v in enumerate(by_cat.values):
        pct = v / total * 100
        label = f"{v:,.0f} ₽  ({pct:.1f}%)".replace(",", " ")
        ax.text(v + total * 0.005, i, label, va="center", fontsize=8.5)

    ax.set_title(f"Ежемесячные затраты на ингредиенты (итого: {total:,.0f} ₽)".replace(",", " "))
    ax.set_xlabel("₽ в месяц")
    ax.set_xlim(0, by_cat.max() * 1.4)
    ax.grid(axis="x", alpha=0.2)
    fig.tight_layout()
    fig.savefig(PLOTS / "monthly_ingredient_costs.png", dpi=150)
    plt.close()

def main():

    ingredient_costs = pd.read_csv(DATA / "ingredient_costs.csv")
    drink_costs      = pd.read_csv(DATA / "drink_costs.csv")
    benchmark        = pd.read_csv(DATA / "competitor_benchmark.csv")
    comparison       = pd.read_csv(DATA / "supplier_comparison_full.csv")
    monthly          = pd.read_csv(DATA / "monthly_purchase_plan.csv")

    plot_cost_by_category(ingredient_costs)
    print("drink_cost_structure")

    plot_ingredient_breakdown(ingredient_costs)
    print("ingredient_breakdown_by_drink")

    plot_cost_vs_price(drink_costs)
    print("drink_cost_vs_market_price")

    plot_competitor_segments(benchmark, drink_costs)
    print("competitor_segments")

    plot_competitor_scatter(benchmark)
    print("competitor_price_scatter")

    plot_supplier_serving_cost(comparison)
    print("supplier_serving_cost")

    plot_monthly_costs(monthly)
    print("monthly_ingredient_costs")

    print(f"\nВсего графиков построено: {len(list(PLOTS.glob('*.png')))}")

if __name__ == "__main__":
    main()
