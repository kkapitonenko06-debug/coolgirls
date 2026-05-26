import csv
import re
import time
from dataclasses import dataclass, fields, asdict
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT    = Path(__file__).parent
OUT_DIR = ROOT / "data" / "raw"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_PATH = OUT_DIR / "competitor_prices_scraped.csv"

REQUEST_DELAY = 1.5
MAX_RETRIES   = 3
TIMEOUT       = 15

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Connection":      "keep-alive",
}

#одна найденная позиция из меню конкурента

@dataclass
class MenuItem:
    competitor:  str
    source_site: str
    category:    str
    drink_name:  str
    price_rub:   float
    source_url:  str

#Делает GET-запросы, при ошибке пробует ещё несколько раз
class HttpClient:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def get(self, url):
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = self.session.get(url, timeout=TIMEOUT)
                if resp.status_code == 200:
                    return BeautifulSoup(resp.text, "lxml")
                if resp.status_code == 404:
                    print(f"404 Not Found: {url}")
                    return None
                print(f"HTTP {resp.status_code} на попытке {attempt}: {url}")
            except requests.RequestException as exc:
                print(f"Ошибка на попытке {attempt}: {url} — {exc}")

            if attempt < MAX_RETRIES:
                time.sleep(REQUEST_DELAY * attempt)

        print(f"Не удалось получить: {url}")
        return None


DOSTAVKA_EDA_PLACES = [
    ("pims_l3swc",           "PIMS Tea"),
    ("nova_tea_moscow",      "Nova Bubble Tea"),
    ("chicha_san_chen_ubnwv","Chicha San Chen"),
    ("teahiro_ovdws",        "Teahiro"),
    ("jinju",                "Jinju"),
    ("jinju_bubble_tea",     "Jinju"),
    ("jinju_moscow",         "Jinju"),
    ("dav_bubble_tea",       "Dav Bubble Tea"),
    ("dav_bubble",           "Dav Bubble Tea"),
    ("dav_tea",              "Dav Bubble Tea"),
    ("zin_tea",              "Zin Tea"),
    ("zin_tea_moscow",       "Zin Tea"),
    ("pretty_bubble_tea",    "Pretty Bubble Tea"),
    ("pretty_bubble",        "Pretty Bubble Tea"),
    ("one_price_coffee",     "One Price Coffee"),
    ("jpan",                 "J'Pan"),
    ("j_pan_moscow",         "J'Pan"),
    ("j_pan",                "J'Pan"),
    ("won_cha",              "Won Cha"),
    ("won_cha_moscow",       "Won Cha"),
]

BASE_DOSTAVKA = "http://dostavka-eda.com/moscow/place/{slug}/"

class DostavkaEdaParser:

    PRICE_RE = re.compile(r"(\d[\d\s]*)\s*₽")

    def __init__(self, client):
        self.client = client

    def parse_place(self, slug, competitor):
        url = BASE_DOSTAVKA.format(slug=slug)
        soup = self.client.get(url)
        if soup is None:
            return

        print(f"dostavka-eda  {competitor}  {url}")

        current_category = "Меню"
        yielded = 0

        for tag in soup.find_all(
            ["h2", "h3", "div", "li", "article"],
            class_=re.compile(
                r"(category|section|group|header|menu-item|product|dish|item)",
                re.I,
            ),
        ):
            text = tag.get_text(" ", strip=True)
            if not text:
                continue

            #Если это заголовок категории (нет цены)
            if not self.PRICE_RE.search(text) and tag.name in ("h2", "h3"):
                current_category = text[:80]
                continue

            price_match = self.PRICE_RE.search(text)
            if not price_match:
                continue

            price_str = price_match.group(1).replace(" ", "")
            try:
                price = float(price_str)
            except ValueError:
                continue

            if price < 50 or price > 5000:
                continue

            #Название напитка --- это текст до цены
            name_raw = text[: price_match.start()].strip(" -–:")
            name = re.sub(r"\s{2,}", " ", name_raw)[:120]
            if len(name) < 3:
                continue

            yield MenuItem(
                competitor=competitor,
                source_site="dostavka-eda.com",
                category=current_category,
                drink_name=name,
                price_rub=price,
                source_url=url,
            )
            yielded += 1

        if yielded == 0:
            yield from self._fallback_parse(soup, competitor, url)

    def _fallback_parse(self, soup, competitor, url):
        blocks = soup.find_all(
            "div",
            class_=re.compile(r"(item|card|product|dish|menu)", re.I),
        )
        for block in blocks:
            price_m = self.PRICE_RE.search(block.get_text())
            if not price_m:
                continue
            try:
                price = float(price_m.group(1).replace(" ", ""))
            except ValueError:
                continue
            if price < 50 or price > 5000:
                continue

            name_tag = block.find(
                ["p", "span", "a"],
                string=lambda s: s and not self.PRICE_RE.search(s),
            )
            name = (name_tag.get_text(strip=True) if name_tag else "")[:120]
            if len(name) < 3:
                continue

            yield MenuItem(
                competitor=competitor,
                source_site="dostavka-eda.com",
                category="Меню",
                drink_name=name,
                price_rub=price,
                source_url=url,
            )


OEDA_PLACES = [
    ("won_cha_tukjs",       "Won Cha"),
    ("jinju",               "Jinju"),
    ("jinju_bubble",        "Jinju"),
    ("dav_bubble_tea",      "Dav Bubble Tea"),
    ("dav_bubble",          "Dav Bubble Tea"),
    ("zin_tea",             "Zin Tea"),
    ("pims_tea",            "PIMS Tea"),
    ("pretty_bubble_tea",   "Pretty Bubble Tea"),
    ("one_price_coffee",    "One Price Coffee"),
    ("teahiro",             "Teahiro"),
    ("nova_tea",            "Nova Bubble Tea"),
    ("chicha_san_chen",     "Chicha San Chen"),
    ("j_pan",               "J'Pan"),
]

BASE_OEDA = "https://o-eda-dostavka.ru/goroda/moscow/rest/{slug}/"

class OedaParser:

    PRICE_RE = re.compile(r"(\d[\d\s]*)\s*₽")

    def __init__(self, client):
        self.client = client

    def parse_place(self, slug, competitor):
        url = BASE_OEDA.format(slug=slug)
        soup = self.client.get(url)
        if soup is None:
            return

        print(f"o-eda-dostavka  {competitor}  {url}")

        current_category = "Меню"

        for tag in soup.find_all(
            ["h2", "h3", "h4", "div", "li", "tr"],
            class_=re.compile(
                r"(category|section|group|header|menu.item|product|dish|item|row)",
                re.I,
            ),
        ):
            text = tag.get_text(" ", strip=True)
            if not text:
                continue

            if not self.PRICE_RE.search(text) and tag.name in ("h2", "h3", "h4"):
                current_category = text[:80]
                continue

            price_m = self.PRICE_RE.search(text)
            if not price_m:
                continue

            try:
                price = float(price_m.group(1).replace(" ", ""))
            except ValueError:
                continue

            if price < 50 or price > 5000:
                continue

            name_raw = text[: price_m.start()].strip(" -–:")
            name = re.sub(r"\s{2,}", " ", name_raw)[:120]
            if len(name) < 3:
                continue

            yield MenuItem(
                competitor=competitor,
                source_site="o-eda-dostavka.ru",
                category=current_category,
                drink_name=name,
                price_rub=price,
                source_url=url,
            )

#Дедупликация

def deduplicate(items):
    seen = set()
    result = []
    for item in items:
        key = (item.competitor, item.drink_name.lower())
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result

#Основная функция

def collect_all():
    client = HttpClient()
    results = []

    parser1 = DostavkaEdaParser(client)
    seen_competitors_d = set()

    for slug, competitor in DOSTAVKA_EDA_PLACES:
        if competitor in seen_competitors_d:
            continue

        items = list(parser1.parse_place(slug, competitor))
        if items:
            print(f"  → {len(items)} позиций для {competitor} (slug={slug})")
            results.extend(items)
            seen_competitors_d.add(competitor)
        else:
            print(f"  → 0 позиций (slug={slug}, конкурент={competitor})")

        time.sleep(REQUEST_DELAY)

    parser2 = OedaParser(client)
    seen_competitors_o = set()

    for slug, competitor in OEDA_PLACES:
        if competitor in seen_competitors_o:
            continue

        items = list(parser2.parse_place(slug, competitor))
        if items:
            print(f"  → {len(items)} позиций для {competitor} (slug={slug})")
            results.extend(items)
            seen_competitors_o.add(competitor)
        else:
            print(f"  → 0 позиций (slug={slug}, конкурент={competitor})")

        time.sleep(REQUEST_DELAY)

    return deduplicate(results)

def save_csv(items, path):
    columns = [f.name for f in fields(MenuItem)]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for item in items:
            writer.writerow(asdict(item))

def main():
    items = collect_all()

    if not items:
        print("Данные не собраны")
        return

    save_csv(items, OUT_PATH)
    print(f"Собрано товаров: {len(items)}")
    print(f"Файл сохранён")

    #Немного статичтики
    from collections import Counter
    import statistics

    counter = Counter(item.competitor for item in items)
    prices  = [item.price_rub for item in items]
    print(f"\n{'=' * 55}")
    print(f"{'=' * 55}")
    print(f"  Всего позиций:     {len(items)}")
    print(f"  Конкурентов:       {len(counter)}")
    print(f"  Диапазон цен:      {min(prices):.0f} – {max(prices):.0f} ₽")
    print(f"  Медиана:           {statistics.median(prices):.0f} ₽")
    print(f"\n  {'Конкурент':<28} {'Позиций':>8}  {'Мин':>6}  {'Медиана':>8}  {'Макс':>6}")
    print("  " + "-" * 60)
    for competitor, count in sorted(counter.items(), key=lambda x: -x[1]):
        comp_prices = [i.price_rub for i in items if i.competitor == competitor]
        print(
            f"  {competitor:<28} {count:>8}  "
            f"{min(comp_prices):>5.0f}₽  "
            f"{statistics.median(comp_prices):>7.0f}₽  "
            f"{max(comp_prices):>5.0f}₽"
        )

if __name__ == "__main__":
    main()
