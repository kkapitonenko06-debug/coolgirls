from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from scipy import stats

ROOT      = Path(__file__).parent.parent
HH_PATH   = ROOT / "data" / "raw" / "hh_vacancies_moscow.csv"
SJ_PATH   = ROOT / "data" / "raw" / "superjob_vacancies_moscow.csv"
TV_PATH   = ROOT / "data" / "raw" / "trudvsem_vacancies_moscow.csv"
SUP_PATH  = ROOT / "data" / "processed" / "supplier_comparison_full.csv"
PLOT_PATH_SJ = ROOT / "plots" / "salary_ttest_hh_vs_superjob.png"
PLOT_PATH_TV = ROOT / "plots" / "salary_ttest_hh_vs_trudvsem.png"
PLOT_PATH_CV = ROOT / "plots" / "supplier_price_variation.png"

POSITIONS = ["Бариста", "Помощник бариста", "Менеджер", "Уборщик"]

#Гипотеза H0: средние зарплаты на hh.ru и superjob одинаковы
#Если p < 0.05 — отвергаем H0, различие значимое

def run_ttest(hh, other, other_col):
    results = []
    for pos in POSITIONS:
        hh_sal    = hh[(hh["target_position"] == pos) & hh["salary_mid"].notna()]["salary_mid"]
        other_sal = other[(other["target_position"] == pos) & other["salary_mid"].notna()]["salary_mid"]

        t_stat, p_value = stats.ttest_ind(hh_sal, other_sal)

        results.append({
            "position":        pos,
            "hh_n":            len(hh_sal),
            f"{other_col}_n":  len(other_sal),
            "hh_median":       hh_sal.median(),
            f"{other_col}_median": other_sal.median(),
            "t_stat":          round(t_stat, 3),
            "p_value":         round(p_value, 4),
            "significant":     p_value < 0.05,
        })
    return pd.DataFrame(results)


def print_results(df, title, other_label):
    print("\n" + "=" * 70)
    print(f"t-тест: сравнение зарплат HH.RU И {title.upper()} по всем позициям")
    print("=" * 70)
    print(f"\n  {'Позиция':<22} {'HH медиана':>11}  {other_label+' медиана':>14}  {'p-value':>8}  {'Вывод'}")
    print("  " + "-" * 70)

    other_col = f"{other_label.lower()}_median"
    for _, row in df.iterrows():
        verdict = "различие значимо" if row["significant"] else "различия нет"
        print(
            f"  {row['position']:<22} "
            f"{row['hh_median']:>10.0f}₽  "
            f"{row[other_col]:>13.0f}₽  "
            f"{row['p_value']:>8.4f}  "
            f"{verdict}"
        )

    print("\n  p < 0.05 означает, что источники показывают статистически разные зарплаты")


def plot_results(df, path, title, other_label, other_color):
    fig, axes = plt.subplots(1, len(POSITIONS), figsize=(14, 5))
    fig.suptitle(f"Медианные зарплаты: hh.ru vs {title}", fontsize=14, fontweight="bold")

    colors = {"hh.ru": "#d6604d", other_label: other_color}
    other_col = f"{other_label.lower()}_median"

    for ax, (_, row) in zip(axes, df.iterrows()):
        bars = ax.bar(
            ["hh.ru", other_label],
            [row["hh_median"], row[other_col]],
            color=[colors["hh.ru"], colors[other_label]],
            width=0.5,
        )
        ax.set_title(row["position"], fontsize=11)
        ax.set_ylabel("₽" if ax == axes[0] else "")
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{int(x):,}".replace(",", " ")))

        for bar in bars:
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 1000,
                f"{int(bar.get_height()):,}₽".replace(",", " "),
                ha="center", va="bottom", fontsize=9,
            )

        color = "red" if row["significant"] else "green"
        label = f"p = {row['p_value']:.4f}\n{'значимо' if row['significant'] else 'не значимо'}"
        ax.set_xlabel(label, color=color, fontsize=9)

    plt.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"График сохранен")

#Коэффициент вариации цен поставщиков = std/mean * 100 показывает разброс цен в процентах
def compute_cv(sup):
    rows = []
    for category, group in sup.groupby("category"):
        if len(group) < 2:
            continue
        prices = group["median_unit_price"]
        cv = prices.std() / prices.mean() * 100
        rows.append({
            "category":    category,
            "suppliers_n": len(group),
            "min_price":   prices.min(),
            "max_price":   prices.max(),
            "mean_price":  prices.mean(),
            "cv_pct":      round(cv, 1),
        })
    return pd.DataFrame(rows).sort_values("cv_pct", ascending=False)

def print_cv(df):
    print("\n" + "=" * 65)
    print("РАЗБРОС ЦЕН НА ИНГРЕДИЕНТЫ У РАЗНЫХ ПОСТАВЩИКОВ")
    print("=" * 65)
    print(f"\n  {'Категория':<22} {'Поставщ.':>9}  {'Мин ₽/ед':>9}  {'Макс ₽/ед':>10}  {'CV %':>6}")
    print("  " + "-" * 65)
    for _, row in df.iterrows():
        print(
            f"  {row['category']:<22} {row['suppliers_n']:>9}  "
            f"{row['min_price']:>9.3f}  "
            f"{row['max_price']:>10.3f}  "
            f"{row['cv_pct']:>5.1f}%"
        )

def plot_cv(df, path):
    fig, ax = plt.subplots(figsize=(10, 6))
    colors = ["#d73027" if cv > 30 else "#fee090" if cv > 15 else "#91bfdb"
              for cv in df["cv_pct"]]
    bars = ax.barh(df["category"], df["cv_pct"], color=colors)
    ax.set_xlabel("Коэффициент вариации, %")
    ax.set_title("Нестабильность цен на ингредиенты у разных поставщиков", fontweight="bold")
    ax.axvline(15, color="orange", linestyle="--", alpha=0.7, label="15% — умеренный разброс")
    ax.axvline(30, color="red",    linestyle="--", alpha=0.7, label="30% — высокий разброс")
    ax.legend(fontsize=9)
    for bar, val in zip(bars, df["cv_pct"]):
        ax.text(val + 0.5, bar.get_y() + bar.get_height() / 2,
                f"{val:.1f}%", va="center", fontsize=9)
    plt.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"График сохранен")


def main():
    hh = pd.read_csv(HH_PATH)
    sj = pd.read_csv(SJ_PATH)
    tv = pd.read_csv(TV_PATH)

    #hh.ru и SuperJob
    results_sj = run_ttest(hh, sj, "sj")
    print_results(results_sj, "SuperJob", "SJ")
    plot_results(results_sj, PLOT_PATH_SJ, "SuperJob", "SJ", "#4393c3")

    #hh.ru и Trudvsem
    results_tv = run_ttest(hh, tv, "tv")
    print_results(results_tv, "Trudvsem", "TV")
    plot_results(results_tv, PLOT_PATH_TV, "Trudvsem", "TV", "#74add1")

    #Коэффициент вариации
    sup  =pd.read_csv(SUP_PATH)
    cv_df = compute_cv(sup)
    print_cv(cv_df)
    plot_cv(cv_df, PLOT_PATH_CV)


if __name__ == "__main__":
    main()
