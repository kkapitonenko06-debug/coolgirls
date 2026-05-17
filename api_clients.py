from __future__ import annotations

import os
from pathlib import Path
from time import sleep

import pandas as pd
import requests


DADATA_URL = "https://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/party"
TRUDVSEM_URL = "https://opendata.trudvsem.ru/api/v1/vacancies"

#Код Москвы в API "Работа России".
MOSCOW_REGION_CODE = "7700000000000"

#Запросы под сотрудников, которые могут понадобиться кафе
VACANCY_SEARCH_WORDS = {
    "Бариста": "бариста",
    "Кассир": "кассир кафе",
    "Администратор": "администратор кафе",
    "Управляющий": "управляющий кафе",
    "Уборщик": "уборщик кафе",
    "Продавец-кассир": "продавец кассир",
    "Работник кафе": "работник кафе",
    "Помощник бариста": "помощник бариста",
}


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def collect_dadata_counterparties(queries: pd.DataFrame, api_key: str) -> pd.DataFrame:
    #DaData ищет организацию по названию и возвращает реквизиты юрлица
    session = requests.Session()
    session.headers.update(
        {
            "Authorization": f"Token {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
    )

    rows = []
    for row in queries.itertuples(index=False):
        response = session.post(
            DADATA_URL,
            json={"query": row.query, "count": 1},
            timeout=20,
        )
        response.raise_for_status()
        suggestions = response.json().get("suggestions", [])
        rows.append(_parse_dadata_party(row.query, row.role, suggestions))
        sleep(0.2)
    return pd.DataFrame(rows)


def collect_trudvsem_vacancies(limit: int = 100) -> pd.DataFrame:
    rows = []
    for target_position, query in VACANCY_SEARCH_WORDS.items():
        response = requests.get(
            TRUDVSEM_URL,
            params={
                "text": query,
                "region_code": MOSCOW_REGION_CODE,
                "limit": limit,
                "offset": 0,
            },
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        for item in payload.get("results", {}).get("vacancies", []):
            rows.append(_parse_trudvsem_vacancy(target_position, item))
        sleep(0.5)
    return pd.DataFrame(rows)


def _parse_dadata_party(query: str, role: str, suggestions: list[dict]) -> dict:
    if not suggestions:
        return {
            "query": query,
            "role": role,
            "name": None,
            "inn": None,
            "kpp": None,
            "ogrn": None,
            "status": None,
            "address": None,
            "okved": None,
            "management_name": None,
            "management_post": None,
        }

    suggestion = suggestions[0]
    data = suggestion.get("data") or {}
    management = data.get("management") or {}
    state = data.get("state") or {}
    address = data.get("address") or {}
    return {
        "query": query,
        "role": role,
        "name": suggestion.get("value"),
        "inn": data.get("inn"),
        "kpp": data.get("kpp"),
        "ogrn": data.get("ogrn"),
        "status": state.get("status"),
        "address": address.get("unrestricted_value"),
        "okved": data.get("okved"),
        "management_name": management.get("name"),
        "management_post": management.get("post"),
    }


def _parse_trudvsem_vacancy(target_position: str, item: dict) -> dict:
    vacancy = item.get("vacancy") or {}
    company = vacancy.get("company") or {}
    region = vacancy.get("region") or {}
    return {
        "target_position": target_position,
        "vacancy_id": vacancy.get("id"),
        "job_name": vacancy.get("job-name"),
        "company_name": company.get("name"),
        "company_inn": company.get("inn"),
        "region_name": region.get("name"),
        "salary_text": vacancy.get("salary"),
        "salary_min": vacancy.get("salary_min"),
        "salary_max": vacancy.get("salary_max"),
        "schedule": vacancy.get("schedule"),
        "qualification": vacancy.get("qualification"),
        "creation_date": vacancy.get("creation-date"),
        "date_modify": vacancy.get("date_modify"),
        "vacancy_url": vacancy.get("vac_url"),
        "source": vacancy.get("source"),
    }
