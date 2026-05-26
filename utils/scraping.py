from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup


PRODUCT_KEYWORDS = (
    "тапиока",
    "чай",
    "матча",
    "улун",
    "габа",
    "жасмин",
    "желе",
    "джус",
    "поппинг",
    "боба",
    "пудинг",
    "алоэ",

    "сироп",
    "пюре",
    "концентрат",
    "личи",
    "манго",
    "клубник",
    "маракуй",

    "сливк",
    "молок",
    "кокосов",
    "творожн",
    "пенк",
    "овсян",

    "смесь",
    "порошок",

    "стакан",
    "крышка",
    "трубоч",
    "плёнк",
    "плен",
    "запай",
)


@dataclass
class SupplierSource:
    supplier_name: str
    url: str
    source_type: str
    notes: str


class SupplierProductParser:

    def __init__(self, timeout: int = 20) -> None:
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0 Safari/537.36"
                )
            }
        )

    def parse_sources(self, sources_path: Path) -> pd.DataFrame:
        sources = pd.read_csv(sources_path)
        frames = []
        import logging
        logger = logging.getLogger(__name__)

        for row in sources.itertuples(index=False):
            source = SupplierSource(
                supplier_name=row.supplier_name,
                url=row.url,
                source_type=row.source_type,
                notes=row.notes,
            )
            try:
                frames.append(self.parse_source(source))
            except Exception as exc:
                logger.warning("Пропускем %s (%s): %s", source.supplier_name, source.url, exc)

        if not frames:
            return pd.DataFrame()
        return pd.concat(frames, ignore_index=True).drop_duplicates()

    def parse_source(self, source: SupplierSource, max_pages: int = 10) -> pd.DataFrame:
        all_rows: list[dict] = []
        visited: set[str] = set()
        url = source.url

        import logging
        logger = logging.getLogger(__name__)

        for page_num in range(max_pages):
            if url in visited:
                break
            visited.add(url)

            try:
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
            except Exception as exc:
                if page_num == 0:
                    raise
                logger.debug("Пагинация остановлена на стр.%d (%s): %s", page_num, url, exc)
                break

            soup = BeautifulSoup(response.text, "html.parser")
            rows = self._extract_rows_from_soup(soup, source)
            all_rows.extend(rows)

            next_url = self._find_next_page(soup, url)
            if not next_url or next_url in visited:
                break
            url = next_url

        return pd.DataFrame(all_rows)

    def _extract_rows_from_soup(self, soup, source: SupplierSource) -> list[dict]:
        rows = []
        item_containers = soup.select("div.itemContainer, div.k2store-product-info")
        for container in item_containers:
            row = self._parse_product_container(container, source)
            if row:
                rows.append(row)

        for title_node in soup.find_all(["h2", "h3", "h4", "a", "img"]):
            title = self._extract_title(title_node)
            if not title or not self._looks_like_product(title):
                continue

            product_url = self._extract_url(title_node, source.url)
            price = self._extract_price(title_node)
            category = self._guess_category(title)
            pack_size = self._extract_pack_size(title)

            rows.append(
                {
                    "supplier_name": source.supplier_name,
                    "source_url": source.url,
                    "product_name": title,
                    "category": category,
                    "pack_size": pack_size,
                    "price_rub": price,
                    "product_url": product_url,
                    "source_notes": source.notes,
                }
            )
        return rows

    @staticmethod
    def _find_next_page(soup, current_url: str) -> str | None:
        next_texts = {"следующая", "next", "вперёд", "›", "»", ">"}
        for a in soup.find_all("a", href=True):
            text = a.get_text(strip=True).lower()
            if text in next_texts:
                href = a["href"]
                return urljoin(current_url, href)

        rel_next = soup.find("a", rel=lambda r: r and "next" in r)
        if rel_next and rel_next.get("href"):
            return urljoin(current_url, rel_next["href"])

        return None

    def _parse_product_container(
        self,
        container,
        source: SupplierSource,
    ) -> dict | None:
        title = self._extract_container_title(container)
        if not title or not self._looks_like_product(title):
            return None

        product_url = self._extract_url(container, source.url)
        price = self._extract_price(container)
        category = self._guess_category(title)
        pack_size = self._extract_pack_size(title)

        return {
            "supplier_name": source.supplier_name,
            "source_url": source.url,
            "product_name": title,
            "category": category,
            "pack_size": pack_size,
            "price_rub": price,
            "product_url": product_url,
            "source_notes": source.notes,
        }

    @staticmethod
    def _extract_container_title(container) -> str:
        candidates = []
        for selector in [
            ".catItemTitle",
            ".itemTitle",
            "[itemprop='name']",
            "h2",
            "h3",
            "h4",
            "a",
        ]:
            candidates.extend(container.select(selector))

        for candidate in candidates:
            title = candidate.get_text(" ", strip=True)
            title = re.sub(r"\s+", " ", title).strip(" -")
            if title and len(title) > 5 and title.lower() not in {"подробнее", "просмотр корзины"}:
                return title
        return ""

    @staticmethod
    def _extract_title(node) -> str:
        if node.name == "img":
            value = node.get("alt", "")
        else:
            value = node.get_text(" ", strip=True)
        return re.sub(r"\s+", " ", value).strip(" -")

    @staticmethod
    def _extract_url(node, base_url: str) -> str | None:
        link = node if node.name == "a" else node.find_parent("a")
        if not link or not link.get("href"):
            return None
        return urljoin(base_url, link["href"])

    @staticmethod
    def _extract_price(node) -> float | None:
        container = node.find_parent(["article", "div", "li"]) or node
        text = container.get_text(" ", strip=True)
        match = re.search(r"(\d[\d\s']{1,8})(?:[,.]\d{1,2})?\s*(?:₽|руб)", text, re.I)
        if not match:
            return None
        raw = match.group(1).replace("\xa0", "").replace(" ", "").replace("'", "")
        try:
            return float(raw)
        except ValueError:
            return None

    @staticmethod
    def _extract_pack_size(title: str) -> str | None:
        match = re.search(
            r"(\d+(?:[,.]\d+)?)\s*(кг|г|гр|л|мл|шт)",
            title,
            flags=re.I,
        )
        if not match:
            return None
        return f"{match.group(1).replace(',', '.')} {match.group(2).lower()}"

    @staticmethod
    def _looks_like_product(title: str) -> bool:
        lowered = title.lower()
        return any(keyword in lowered for keyword in PRODUCT_KEYWORDS)

    @staticmethod
    def _guess_category(title: str) -> str:
        lowered = title.lower()
        if "тапиока" in lowered:
            return "Тапиока"
        if "джус" in lowered or "поппинг" in lowered or "боба" in lowered:
            return "Джус-боллы"
        if "желе" in lowered or "алоэ" in lowered:
            return "Желе"
        if "пудинг" in lowered:
            return "Пудинг"
        if "сироп" in lowered:
            return "Сиропы"
        if "пюре" in lowered or "концентрат" in lowered:
            return "Фруктовые пюре"
        if any(k in lowered for k in ("сливк", "творожн", "пенк")):
            return "Крем и молочные"
        if any(k in lowered for k in ("кокосов", "овсян", "молок")):
            return "Молочная основа"
        if any(k in lowered for k in ("стакан", "крышка", "трубоч", "плёнк", "плен", "запай")):
            return "Упаковка"
        if any(k in lowered for k in ("чай", "матча", "улун", "габа", "жасмин")):
            return "Чай"
        if "смесь" in lowered or "порошок" in lowered:
            return "Сухие смеси"
        return "Другое"
