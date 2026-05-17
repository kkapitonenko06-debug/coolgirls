import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup
from requests import RequestException


PRODUCT_KEYWORDS = (
    "тапиока",
    "сироп",
    "джус",
    "поппинг",
    "боба",
    "желе",
    "чай",
    "стакан",
    "крышка",
    "трубоч",
    "смесь",
    "матча",
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
        self.session.headers.update({"User-Agent": "Mozilla/5.0"})

    def parse_sources(self, sources_path: Path) -> pd.DataFrame:
        sources = pd.read_csv(sources_path)
        frames = []
        for row in sources.itertuples(index=False):
            source = SupplierSource(
                supplier_name=row.supplier_name,
                url=row.url,
                source_type=row.source_type,
                notes=row.notes,
            )
            try:
                frames.append(self.parse_source(source))
            except RequestException as error:
                print(f"Не получилось скачать страницу: {source.url}. Ошибка: {error}")
        return pd.concat(frames, ignore_index=True).drop_duplicates()

    def parse_source(self, source: SupplierSource) -> pd.DataFrame:
        #Сначала скачиваем HTML, потом ищем блоки товаров и отдельные ссылки
        response = self.session.get(source.url, timeout=self.timeout)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        rows = []
        for container in soup.select("article, div.itemContainer, div.k2store-product-info"):
            row = self._parse_product_container(container, source)
            if row:
                rows.append(row)

        for title_node in soup.find_all(["h2", "h3", "h4", "a", "img"]):
            title = self._extract_title(title_node)
            if not title or not self._looks_like_product(title):
                continue
            rows.append(
                {
                    "supplier_name": source.supplier_name,
                    "source_url": source.url,
                    "product_name": title,
                    "category": self._guess_category(title),
                    "pack_size": self._extract_pack_size(title),
                    "price_rub": self._extract_price(title_node),
                    "product_url": self._extract_url(title_node, source.url),
                    "source_notes": source.notes,
                }
            )
        return pd.DataFrame(rows)

    def _parse_product_container(self, container, source: SupplierSource) -> dict | None:
        title = self._extract_container_title(container)
        if not title or not self._looks_like_product(title):
            return None
        return {
            "supplier_name": source.supplier_name,
            "source_url": source.url,
            "product_name": title,
            "category": self._guess_category(title),
            "pack_size": self._extract_pack_size(title),
            "price_rub": self._extract_price(container),
            "product_url": self._extract_url(container, source.url),
            "source_notes": source.notes,
        }

    @staticmethod
    def _extract_title(node) -> str:
        if node.name == "img":
            value = node.get("alt", "")
        else:
            value = node.get_text(" ", strip=True)
        return re.sub(r"\s+", " ", value).strip(" -")

    @staticmethod
    def _extract_container_title(container) -> str:
        selectors = [".catItemTitle", ".itemTitle", "[itemprop='name']", "h2", "h3", "h4", "a"]
        for selector in selectors:
            for candidate in container.select(selector):
                title = re.sub(r"\s+", " ", candidate.get_text(" ", strip=True)).strip(" -")
                title = SupplierProductParser._remove_price_from_title(title)
                if title and len(title) > 5 and title.lower() not in {"подробнее", "просмотр корзины"}:
                    return title
        return ""

    @staticmethod
    def _remove_price_from_title(title: str) -> str:
        title = re.sub(r"^\d[\d\s']*(?:[,.]\d+)?\s*₽\s*", "", title)
        title = re.sub(r"^\d[\d\s']*(?:[,.]\d+)?\s*руб\.?\s*", "", title, flags=re.I)
        title = re.sub(r"^\d[\d\s']*(?:[,.]\d+)?\s*₽\s*−\s*\d+\s*%\s*", "", title)
        return title.strip(" -")

    @staticmethod
    def _extract_url(node, base_url: str) -> str | None:
        link = node if getattr(node, "name", None) == "a" else node.find_parent("a") or node.find("a")
        if not link or not link.get("href"):
            return None
        return urljoin(base_url, link["href"])

    @staticmethod
    def _extract_price(node) -> float | None:
        #Приводим цены к нужному формату
        container = node.find_parent(["article", "div", "li"]) or node
        text = container.get_text(" ", strip=True)
        match = re.search(r"(\d[\d\s']{1,8})(?:[,.]\d{1,2})?\s*(?:₽|руб)", text, re.I)
        if not match:
            return None
        clean_price = re.sub(r"[^\d]", "", match.group(1))
        return float(clean_price)

    @staticmethod
    def _extract_pack_size(title: str) -> str | None:
        match = re.search(r"(\d+(?:[,.]\d+)?)\s*(кг|г|гр|л|мл|шт)", title, flags=re.I)
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
        if "сироп" in lowered:
            return "Сиропы"
        if "джус" in lowered or "поппинг" in lowered or "боба" in lowered:
            return "Джус-боллы"
        if "желе" in lowered:
            return "Желе"
        if "стакан" in lowered or "крышка" in lowered or "трубоч" in lowered:
            return "Упаковка"
        if "чай" in lowered or "матча" in lowered:
            return "Чай"
        if "смесь" in lowered:
            return "Сухие смеси"
        return "Другое"
