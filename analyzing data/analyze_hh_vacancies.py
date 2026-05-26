from pathlib import Path

import pandas as pd

from utils.plotting import plot_salary_by_position

ROOT = Path(__file__).parent
INPUT_PATH = ROOT / "data" / "raw" / "hh_vacancies_moscow.csv"
OUTPUT_PATH = ROOT / "data" / "processed" / "hh_salary_summary.csv"
PLOT_PATH = ROOT / "plots" / "hh_salary_by_position.png"

def main():
    vacancies = pd.read_csv(INPUT_PATH)
    vacancies = vacancies[vacancies["salary_currency"] == "RUR"].copy()
    vacancies = vacancies.dropna(subset=["salary_mid"])

    summary = vacancies.groupby("target_position")["salary_mid"].agg(["median", "mean", "min", "max"])
    summary.columns = ["median_salary_rub", "mean_salary_rub", "min_salary_rub", "max_salary_rub"]
    summary = summary.reset_index()
    summary["vacancies_count"] = vacancies.groupby("target_position")["vacancy_name"].count().values
    summary = summary.sort_values("median_salary_rub", ascending=False)
    summary.to_csv(OUTPUT_PATH, index=False)
    plot_salary_by_position(vacancies, PLOT_PATH)

    print(summary)
    print(f"Таблица сохранена")
    print(f"График сохранен")

if __name__ == "__main__":
    main()

