from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent
INPUT_PATH = ROOT / "data" / "raw" / "dadata_counterparties.csv"
OUTPUT_PATH = ROOT / "data" / "processed" / "counterparty_risk_summary.csv"

def score_status(status):
    if not isinstance(status, str):
        return 0
    if status.upper() == "ACTIVE":
        return 2
    if status.upper() in {"LIQUIDATING", "REORGANIZING"}:
        return 1
    return 0

def main():
    counterparties = pd.read_csv(INPUT_PATH)
    summary = counterparties.copy()
    summary["status_score"] = summary["status"].apply(score_status)
    summary["has_inn"] = summary["inn"].notna()
    summary["has_ogrn"] = summary["ogrn"].notna()
    summary["risk_comment"] = summary.apply(
        lambda row: (
            "Можно рассматривать"
            if row["status_score"] == 2 and row["has_inn"] and row["has_ogrn"]
            else "Нужна ручная проверка"
        ),
        axis=1,
    )
    summary.to_csv(OUTPUT_PATH, index=False)

    print(summary[["query", "name", "inn", "status", "risk_comment"]].to_string(index=False))
    print(f"Таблица сохранена: {OUTPUT_PATH}")

if __name__ == "__main__":
    main()

