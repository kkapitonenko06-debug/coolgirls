from pathlib import Path

import pandas as pd

from utils.plotting import plot_trudvsem_salary_medians

ROOT = Path(__file__).parent
INPUT_PATH = ROOT / "data" / "raw" / "trudvsem_vacancies_moscow.csv"
OUTPUT_PATH = ROOT / "data" / "processed" / "trudvsem_salary_summary.csv"
PLOT_PATH = ROOT / "plots" / "trudvsem_salary_medians.png"

def main():
    vacancies = pd.read_csv(INPUT_PATH)
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
    summary.to_csv(OUTPUT_PATH, index=False)
    plot_trudvsem_salary_medians(summary, PLOT_PATH)

    print(summary.to_string(index=False))
    print(f"Таблица сохранена: {OUTPUT_PATH}")
    print(f"График сохранен: {PLOT_PATH}")

if __name__ == "__main__":
    main()
