#Это сборщик вакансий с портала Работа в России (trudvsem.ru), API без авторизации

from dataclasses import asdict, dataclass
from pathlib import Path
from time import sleep

import pandas as pd
import requests

ROOT = Path(__file__).parent
OUTPUT_PATH = ROOT / "data" / "raw" / "trudvsem_vacancies_moscow.csv"

API_URL            = "https://opendata.trudvsem.ru/api/v1/vacancies"
MOSCOW_REGION_CODE = "7700000000000"  #код Москвы в ФИАС
PAGE_SIZE          =100              #максимум на страницу
REQUEST_DELAY      =0.8              #пауза между запросами

#Специфичные запросы первыми, потом будет дедупликация по id
SEARCH_QUERIES: list[tuple[str, str]] = [
    ("Помощник бариста", "помощник бариста"),
    ("Помощник бариста", "начинающий бариста"),
    ("Помощник бариста", "стажер бариста"),
    ("Помощник бариста", "ученик бариста"),
    ("Помощник бариста", "бариста без опыта"),
    ("Помощник бариста", "бармен стажер"),
    ("Помощник бариста", "младший бариста"),

    ("Бариста",          "бариста"),
    ("Бариста",          "бариста кофейня"),
    ("Бариста",          "бариста кассир"),
    ("Бариста",          "бармен кафе"),
    ("Бариста",          "бармен кофейня"),
    ("Бариста",          "кофевар"),
    ("Бариста",          "сотрудник кофейни"),
    ("Бариста",          "оператор кофемашины"),
    ("Бариста",          "бариста бармен"),
    ("Бариста",          "приготовитель напитков"),
    ("Бариста",          "продавец напитков"),
    ("Бариста",          "работник кофейни"),
    ("Бариста",          "сотрудник кафе"),

    ("Менеджер",         "менеджер кафе"),
    ("Менеджер",         "администратор кафе"),
    ("Менеджер",         "управляющий кафе"),
    ("Менеджер",         "менеджер смены кафе"),
    ("Менеджер",         "старший бариста"),
    ("Менеджер",         "директор кафе"),
    ("Менеджер",         "администратор кофейни"),
    ("Менеджер",         "управляющий кофейней"),
    ("Менеджер",         "менеджер ресторана"),
    ("Менеджер",         "администратор ресторана"),
    ("Менеджер",         "управляющий рестораном"),
    ("Менеджер",         "менеджер смены ресторан"),
    ("Менеджер",         "супервайзер кафе"),

    ("Уборщик",          "уборщик кафе"),
    ("Уборщик",          "уборщица кафе"),
    ("Уборщик",          "уборщик ресторан"),
    ("Уборщик",          "уборщица ресторан"),
    ("Уборщик",          "клинер кафе"),
    ("Уборщик",          "клинер ресторан"),
    ("Уборщик",          "посудомойщик"),
    ("Уборщик",          "мойщик посуды"),
    ("Уборщик",          "посудомойщик ресторан"),
    ("Уборщик",          "посудомойщик кафе"),
    ("Уборщик",          "уборщик помещений кафе"),
    ("Уборщик",          "технический персонал кафе"),
]

@dataclass
class Vacancy:
    target_position: str
    vacancy_id: str
    vacancy_name: str
    employer: str | None
    employer_inn: str | None
    region: str | None
    salary_from: int | None
    salary_to: int | None
    salary_mid: float | None
    schedule: str | None
    qualification: str | None
    created_at: str | None
    url: str | None
    source: str = "trudvsem.ru"

class TrudvsemApiClient:

    def __init__(
        self,
        region_code: str = MOSCOW_REGION_CODE,
        page_size: int = PAGE_SIZE,
        delay: float = REQUEST_DELAY,
    ):
        self.region_code = region_code
        self.page_size   = page_size
        self.delay       = delay
        self._session    = requests.Session()
        self._session.headers.update({"Accept": "application/json"})

    def iter_pages(self, keyword):
        #Возвращает список вакансий постранично.Запрашивает с фильтром региона и без него, чтобы учесть записи с нестандартными геоданными
        #Дедупликация по id выполняется в VacancyCollector

        for use_region, text in [
            (True,  keyword),
            (False, keyword + " Москва"),
        ]:
            offset = 0
            while True:
                params: dict = {
                    "text":   text,
                    "limit":  self.page_size,
                    "offset": offset,
                }
                if use_region:
                    params["region_code"] = self.region_code

                try:
                    response = self._session.get(API_URL, params=params, timeout=30)
                    response.raise_for_status()
                except requests.RequestException as exc:
                    print(f"Ошибка запроса (offset={offset}): {exc}")
                    break

                payload   = response.json()
                vacancies = payload.get("results", {}).get("vacancies", [])

                if not vacancies:
                    break

                yield vacancies

                if len(vacancies) < self.page_size:
                    break

                offset += self.page_size
                sleep(self.delay)

class VacancyCollector:

    def __init__(
        self,
        search_queries: list[tuple[str, str]],
        client: TrudvsemApiClient,
    ):
        self.search_queries = search_queries
        self.client         = client
        self._seen_ids: set[str] = set()

    @staticmethod
    def _parse_salary(raw: dict) -> tuple[int | None, int | None, float | None]:
        s_from = raw.get("salary_min")
        s_to   = raw.get("salary_max")
        s_from = int(s_from) if s_from else None
        s_to   = int(s_to)   if s_to   else None
        if s_from and s_to:
            s_mid: float | None = (s_from + s_to) / 2
        else:
            s_mid = float(s_from) if s_from else (float(s_to) if s_to else None)
        return s_from, s_to, s_mid

    def _parse_item(self, item: dict, target_position: str) -> Vacancy:
        raw     = item.get("vacancy") or {}
        company = raw.get("company") or {}
        region  = raw.get("region")  or {}
        s_from, s_to, s_mid = self._parse_salary(raw)
        return Vacancy(
            target_position = target_position,
            vacancy_id      = str(raw.get("id", "")),
            vacancy_name    = raw.get("job-name", ""),
            employer        = company.get("name") or None,
            employer_inn    = company.get("inn")  or None,
            region          = region.get("name")  or None,
            salary_from     = s_from,
            salary_to       = s_to,
            salary_mid      = s_mid,
            schedule        = raw.get("schedule") or None,
            qualification   = raw.get("qualification") or None,
            created_at      = raw.get("creation-date") or None,
            url             = raw.get("vac_url") or None,
        )

    def collect(self):
        results = []

        for position_name, query_text in self.search_queries:
            print(f"Запрос: {query_text}  (позиция: {position_name})")
            new_count = 0

            for page_items in self.client.iter_pages(query_text):
                for item in page_items:
                    raw = item.get("vacancy") or {}
                    vid = str(raw.get("id", ""))
                    if not vid or vid in self._seen_ids:
                        continue
                    self._seen_ids.add(vid)
                    results.append(self._parse_item(item, position_name))
                    new_count += 1

            print(f"{new_count} новых вакансий (итого: {len(results)}")

        return results

    @staticmethod
    def to_dataframe(vacancies):
        return pd.DataFrame([asdict(v) for v in vacancies])

def main():
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    client    = TrudvsemApiClient(region_code=MOSCOW_REGION_CODE, delay=REQUEST_DELAY)
    collector = VacancyCollector(SEARCH_QUERIES, client)

    vacancies = collector.collect()
    df        = collector.to_dataframe(vacancies)
    df.to_csv(OUTPUT_PATH, index=False)

    print("=" * 60)
    print(f"Итого уникальных вакансий: {len(df)}")
    print(f"Файл сохранен")

    if not df.empty:
        summary = (
            df.groupby("target_position")
            .agg(
                count         = ("vacancy_id", "count"),
                with_salary   = ("salary_mid", lambda s: s.notna().sum()),
                median_salary = ("salary_mid", "median"),
            )
            .sort_values("count", ascending=False)
        )
        print("\n" + summary.to_string())

if __name__ == "__main__":
    main()
