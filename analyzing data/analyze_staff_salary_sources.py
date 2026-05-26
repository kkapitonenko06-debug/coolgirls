from pathlib import Path

import pandas as pd

from utils.cost_analysis import INSURANCE_RATE
from utils.plotting import plot_staff_market_salary_sources

ROOT = Path(__file__).parent
INPUT_PATH = ROOT / "data" / "raw" / "staff_salary_sources.csv"
OUTPUT_PATH = ROOT / "data" / "processed" / "staff_salary_sources_summary.csv"
PLOT_PATH = ROOT / "plots" / "staff_market_salary_sources.png"

def main():
    salaries = pd.read_csv(INPUT_PATH)
    salaries["employer_total_cost_rub"] = salaries["salary_rub"] * (1 + INSURANCE_RATE)
    salaries.to_csv(OUTPUT_PATH, index=False)
    plot_staff_market_salary_sources(salaries, PLOT_PATH)

    print(salaries[["position", "source_name", "salary_rub", "employer_total_cost_rub"]])
    print(f"Таблица сохранена")
    print(f"График сохранен")

if __name__ == "__main__":
    main()

