import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from time import sleep

import pandas as pd
import requests

ROOT = Path(__file__).parent
OUTPUT_PATH = ROOT / "data" / "raw" / "hh_vacancies_moscow.csv" #это чтобы кодик работал на любом устройстве

MOSCOW_AREA_ID = 1  #код Москвы в API hh.ru
PER_PAGE = 20       #hh.ru ограничивает токены до 20 результатов на странице
REQUEST_DELAY = 0.6 #пауза между запросами

HH_CLIENT_ID     = "CLIENT_ID"
HH_CLIENT_SECRET = "CLIENT_SECRET"

#Одна позиция может иметь несколько запросов, дедупликация по id исключает повторы в итоговом файле
#Более специфичные позиции идут первыми, иначе широкий запрос
SEARCH_QUERIES = [
#Специфичные запросы сначала --- помощник бариста
    ("Помощник бариста", "помощник бариста"),
    ("Помощник бариста", "начинающий бариста"),
    ("Помощник бариста", "стажер бариста"),
    ("Помощник бариста", "ученик бариста"),
    ("Помощник бариста", "бариста без опыта"),
    ("Помощник бариста", "бармен стажер"),
#теперь обычный бариста
    ("Бариста",          "бариста"),
    ("Бариста",          "бариста кофейня"),
    ("Бариста",          "бариста кассир"),
    ("Бариста",          "бармен кафе"),
    ("Бариста",          "бармен кофейня"),
    ("Бариста",          "кофевар"),
    ("Бариста",          "сотрудник кофейни"),
    ("Бариста",          "оператор кофемашины"),
    ("Бариста",          "приготовитель напитков"),
    ("Бариста",          "продавец напитков"),
    ("Бариста",          "бариста бармен"),

    ("Менеджер",         "менеджер кафе"),
    ("Менеджер",         "администратор кафе"),
    ("Менеджер",         "управляющий кафе"),
    ("Менеджер",         "менеджер смены кафе"),
    ("Менеджер",         "старший бариста"),
    ("Менеджер",         "директор кафе"),

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
    employer: str
    area: str
    salary_from: float
    salary_to: float
    salary_mid: float
    salary_currency: str
    salary_gross: bool
    experience: str
    employment: str
    schedule: str
    published_at: str
    url: str

class HHOAuthClient: #Получает OAuth-токен от hh.ru и сохраняет его в файл, а при следующем запуске берет токен из файла, а не запрашивает заново, потому что hh.ru не дает обновлять токен раньше срока истечения

    TOKEN_URL  = "https://hh.ru/oauth/token"
#Запрашивает новый токен за 60 секунд до реального истечения
    EXPIRY_GAP = 60

    def __init__(self, client_id, client_secret, cache_path=ROOT / ".hh_token_cache.json"):
        self.client_id     = client_id
        self.client_secret = client_secret
        self.cache_path    = cache_path

    def _load_cache(self):
        if not self.cache_path.exists():
            return None
        try:
            data = json.loads(self.cache_path.read_text())
            return data["access_token"], float(data["expires_at"])
        except Exception:
            return None

    def _save_cache(self, token, expires_in):
        expires_at = time.time() + expires_in - self.EXPIRY_GAP
        self.cache_path.write_text(
            json.dumps({"access_token": token, "expires_at": expires_at})
        )

    def get_token(self):
        cached = self._load_cache()
        if cached:
            token, expires_at = cached
            if time.time() < expires_at:
                expiry_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(expires_at))
                return token

        response = requests.post(
            self.TOKEN_URL,
            data={
                "grant_type":    "client_credentials",
                "client_id":     self.client_id,
                "client_secret": self.client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=15,
        )
        if not response.ok:
            raise RuntimeError(
                f"Не удалось получить токен: "
                f"{response.status_code} — {response.text[:400]}"
            )
        payload    = response.json()
        token      = payload["access_token"]
        expires_in = int(payload.get("expires_in", 1_209_600))  # default 14 days
        self._save_cache(token, expires_in)
        print(f"Токен получен и сохранен")
        return token

class HHApiClient:

    BASE_URL = "https://api.hh.ru/vacancies"

    HEADERS = {
        "User-Agent":      "CafeHR/1.0 (hr@bubblecafe.ru)",
        "Accept":          "application/json",
        "Accept-Language": "ru-RU,ru;q=0.9",
    }

    def __init__(self, area=MOSCOW_AREA_ID, per_page=PER_PAGE, delay=REQUEST_DELAY, oauth=None):
        self.area     = area
        self.per_page = per_page
        self.delay    = delay
        self.oauth    = oauth
        self._session = requests.Session()
        self._session.headers.update(self.HEADERS)

    def _extra_headers(self):
        if self.oauth is None:
            return {}
        try:
            token = self.oauth.get_token()
            return {"Authorization": f"Bearer {token}"}
        except RuntimeError as exc:
            print(f"OAuth недоступен, работаем без токена: {exc}")
            return {}

    def _get_page(self, query, page): #Возвращает один JSON API для страницы
        params = {
            "text":     query,
            "area":     self.area,
            "per_page": self.per_page,
            "page":     page,
        }
        response = self._session.get(
            self.BASE_URL,
            params=params,
            headers=self._extra_headers(),
            timeout=20,
        )
        if not response.ok:
            raise RuntimeError(
                f"hh.ru вернул {response.status_code}.\n"
                f"URL: {response.url}\n"
                f"Тело ответа: {response.text[:800]}"
            )
        return response.json()

    def iter_pages(self, query):
        page = 0
        while True:
            payload = self._get_page(query, page)
            items = payload.get("items", [])
            if not items:
                break

            yield items

            total_pages = payload.get("pages", 1)
            page += 1
            if page >= total_pages:
                break

            sleep(self.delay)

class VacancyCollector:

    def __init__(self, search_queries, client):
        self.search_queries = search_queries
        self.client = client
        self._seen_ids = set()

    @staticmethod
    def _parse_salary(salary):
        if not salary:
            return None, None, None, None, None

        raw_from = salary.get("from")
        raw_to   = salary.get("to")
        s_from   = int(raw_from) if raw_from is not None else None
        s_to     = int(raw_to)   if raw_to   is not None else None

        if s_from and s_to:
            s_mid = (s_from + s_to) / 2
        else:
            s_mid = float(s_from) if s_from else (float(s_to) if s_to else None)

        return s_from, s_to, s_mid, salary.get("currency"), salary.get("gross")

    def _parse_item(self, item, target_position): #Преобразует один элемент API-ответа в объект Vacancy
        s_from, s_to, s_mid, currency, gross = self._parse_salary(item.get("salary"))
        return Vacancy(
            target_position = target_position,
            vacancy_id      = str(item.get("id", "")),
            vacancy_name    = item.get("name", ""),
            employer        = (item.get("employer") or {}).get("name"),
            area            = (item.get("area")     or {}).get("name"),
            salary_from     = s_from,
            salary_to       = s_to,
            salary_mid      = s_mid,
            salary_currency = currency,
            salary_gross    = gross,
            experience      = (item.get("experience")  or {}).get("name"),
            employment      = (item.get("employment")  or {}).get("name"),
            schedule        = (item.get("schedule")    or {}).get("name"),
            published_at    = item.get("published_at"),
            url             = item.get("alternate_url"),
        )

    def collect(self): #Обходит все запросы и все страницы, возвращает список уникальных вакансий
        results = []

        for position_name, query_text in self.search_queries:
            print(f"▶ Запрос: {query_text}  (позиция: {position_name})")
            new_for_query = 0

            for page_items in self.client.iter_pages(query_text):
                for item in page_items:
                    vid = str(item.get("id", ""))
                    if vid in self._seen_ids:
                        continue
                    self._seen_ids.add(vid)
                    results.append(self._parse_item(item, position_name))
                    new_for_query += 1

            print(f"  {new_for_query} новых вакансий  (итого: {len(results)})")

        return results

    @staticmethod
    def to_dataframe(vacancies):
        return pd.DataFrame([asdict(v) for v in vacancies])

def main():
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    oauth  = HHOAuthClient(HH_CLIENT_ID, HH_CLIENT_SECRET)
    client = HHApiClient(
        area=MOSCOW_AREA_ID,
        per_page=PER_PAGE,
        delay=REQUEST_DELAY,
        oauth=oauth,
    )
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
                count=("vacancy_id", "count"),
                with_salary=("salary_mid", lambda s: s.notna().sum()),
                median_salary=("salary_mid", "median"),
            )
            .sort_values("count", ascending=False)
        )
        print("\n" + summary.to_string())

if __name__ == "__main__":
    main()
