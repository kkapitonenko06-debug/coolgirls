from pathlib import Path
import os

import pandas as pd

from utils.dadata_api import collect_counterparties, load_env_file

ROOT = Path(__file__).parent
ENV_PATH = ROOT / ".env"
INPUT_PATH = ROOT / "data" / "raw" / "counterparty_queries.csv"
OUTPUT_PATH = ROOT / "data" / "raw" / "dadata_counterparties.csv"

def main():
    load_env_file(ENV_PATH)
    api_key = os.getenv("DADATA_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Не найден DADATA_API_KEY"
        )

    queries = pd.read_csv(INPUT_PATH)
    counterparties = collect_counterparties(queries, api_key)
    counterparties.to_csv(OUTPUT_PATH, index=False)

    print(f"Собрано контрагентов: {len(counterparties)}")
    print(f"Файл сохранен")
    print(counterparties[["query", "name", "inn", "status", "okved"]].to_string(index=False))

if __name__ == "__main__":
    main()

