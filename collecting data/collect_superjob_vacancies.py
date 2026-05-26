#Это сборщик ваканский с SuperJob
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from time import sleep

import pandas as pd
import requests

ROOT = Path(__file__).parent
OUTPUT_PATH = ROOT / "data" / "raw" / "superjob_vacancies_moscow.csv"

SUPERJOB_API_KEY = os.getenv(
    "SUPERJOB_API_KEY",
    "КЛЮЧ",
)

MOSCOW_TOWN_ID = 4    #ID Москвы в SuperJob
COUNT_PER_PAGE = 100  #максимум разрешенный API
REQUEST_DELAY  = 0.5  #пауза между запросами

#Те же позиции что в hh.ru (дедупликация по ID)
SEARCH_QUERIES: list[tuple[str, str]] = [
    ("Помощник бариста", "помощник бариста"),
    ("Помощник бариста", "начинающий бариста"),
    ("Помощник бариста", "стажер бариста"),
    ("Помощник бариста", "ученик бариста"),
    ("Помощник бариста", "бариста без опыта"),

    ("Бариста",          "бариста"),
    ("Бариста",          "бариста кофейня"),
    ("Бариста",          "бариста кассир"),
    ("Бариста",          "бармен кафе"),
    ("Бариста",          "бармен кофейня"),
    ("Бариста",          "кофевар"),
    ("Бариста",          "сотрудник кофейни"),
    ("Бариста",          "оператор кофемашины"),
    ("Бариста",          "бариста бармен"),

    ("Менеджер",         "менеджер кафе"),
    ("Менеджер",         "администратор кафе"),
    ("Менеджер",         "управляющий кафе"),
    ("Менеджер",         "менеджер смены кафе"),
    ("Менеджер",         "старший бариста"),
    ("Менеджер",         "директор кафе"),
    ("Менеджер",         "администратор кофейни"),

    ("Уборщик",          "уборщик кафе"),
    ("Уборщик",          "уборщица кафе"),
    ("Уборщик",          "уборщик ресторан"),
    ("Уборщик",          "клинер кафе"),
    ("Уборщик",          "клинер ресторан"),
    ("Уборщик",          "посудомойщик"),
    ("Уборщик",          "мойщик посуды"),
    ("Уборщик",          "посудомойщик ресторан"),
]

@dataclass
class Vacancy:
    target_position: str
    vacancy_id: str
    vacancy_name: str
    employer: str | None
    town: str | None
    salary_from: int | None
    salary_to: int | None
    salary_mid: float | None
    experience: str | None
    employment: str | None
    schedule: str | None
    published_at: int | None
    url: str | None
    source: str = "superjob"


class SuperJobApiClient:

    BASE_URL = "https://api.superjob.ru/2.0/vacancies/"

    def __init__(
        self,
        api_key: str,
        town: int = MOSCOW_TOWN_ID,
        count: int = COUNT_PER_PAGE,
        delay: float = REQUEST_DELAY,
    ):
        if not api_key or api_key == "КЛЮЧ":
            raise ValueError(
                "Нужно получить ключ"
            )
        self.town  = town
        self.count = count
        self.delay =delay
        self._session = requests.Session()
        self._session.headers.update({
            "X-Api-App-Id":  api_key,
            "User-Agent":    "CafeHR/1.0 (hr@bubblecafe.ru)",
            "Accept":        "application/json",
            "Accept-Language": "ru-RU,ru;q=0.9",
        })

    def _get_page(self, keyword: str, page: int):
        response = self._session.get(
            self.BASE_URL,
            params={
                "keyword":     keyword,
                "town":        self.town,
                "count":       self.count,
                "page":        page,
                "no_agreement": 0,
            },
            timeout=20,
        )
        if not response.ok:
            raise RuntimeError(
                f"SuperJob вернул {response.status_code}.\n"
                f"Тело: {response.text[:600]}"
            )
        return response.json()

    def iter_pages(self, keyword):
        page = 0
        while True:
            payload  = self._get_page(keyword, page)
            objects  = payload.get("objects", [])
            if not objects:
                break

            yield objects

            if not payload.get("more", False):
                break

            page += 1
            sleep(self.delay)

class VacancyCollector:

    def __init__(
        self,
        search_queries: list[tuple[str, str]],
        client: SuperJobApiClient,
    ):
        self.search_queries = search_queries
        self.client         = client
        self._seen_ids: set[str] = set()

    @staticmethod
    def _parse_salary(item: dict) -> tuple[int | None, int | None, float | None]:
        s_from = item.get("payment_from") or None
        s_to   = item.get("payment_to")   or None
        if s_from and s_to:
            s_mid: float | None = (s_from + s_to) / 2
        else:
            s_mid = float(s_from) if s_from else (float(s_to) if s_to else None)
        return s_from, s_to, s_mid

    def _parse_item(self, item: dict, target_position: str) -> Vacancy:
        s_from, s_to, s_mid = self._parse_salary(item)
        return Vacancy(
            target_position = target_position,
            vacancy_id      = str(item.get("id", "")),
            vacancy_name    = item.get("profession", ""),
            employer        = (item.get("firm_name") or "").strip() or None,
            town            = (item.get("town") or {}).get("title"),
            salary_from     = s_from,
            salary_to       = s_to,
            salary_mid      = s_mid,
            experience      = (item.get("experience") or {}).get("title"),
            employment      = (item.get("type_of_work") or {}).get("title"),
            schedule        = (item.get("place_of_work") or {}).get("title"),
            published_at    = item.get("date_published"),
            url             = item.get("link"),
        )

    def collect(self):
        results = []
        for position_name, query_text in self.search_queries:
            print(f"Запрос: {query_text}  (позиция: {position_name})")
            new_count = 0
            for page_items in self.client.iter_pages(query_text):
                for item in page_items:
                    vid = str(item.get("id", ""))
                    if vid in self._seen_ids:
                        continue
                    self._seen_ids.add(vid)
                    results.append(self._parse_item(item, position_name))
                    new_count += 1
            print(f"  {new_count} новых вакансий (итого: {len(results)}")
        return results

    @staticmethod
    def to_dataframe(vacancies):
        return pd.DataFrame([asdict(v) for v in vacancies])


def main():
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    client    = SuperJobApiClient(SUPERJOB_API_KEY, town=MOSCOW_TOWN_ID,
                                  count=COUNT_PER_PAGE, delay=REQUEST_DELAY)
    collector = VacancyCollector(SEARCH_QUERIES, client)

    vacancies = collector.collect()
    df = collector.to_dataframe(vacancies)
    df.to_csv(OUTPUT_PATH, index=False)

    print("=" * 60)
    print(f"Итого уникальных вакансий: {len(df)}")
    print(f"Файл сохранен")

    if not df.empty:
        summary = (
            df.groupby("target_position")
            .agg(
                count        = ("vacancy_id",  "count"),
                with_salary  = ("salary_mid",  lambda s: s.notna().sum()),
                median_salary= ("salary_mid",  "median"),
            )
            .sort_values("count", ascending=False)
        )
        print("\n" + summary.to_string())

if __name__ == "__main__":
    main()
