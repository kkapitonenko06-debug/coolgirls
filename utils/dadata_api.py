from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import requests


SUGGEST_PARTY_URL = "https://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/party"


@dataclass
class DadataParty:
    query: str
    role: str
    name: str | None
    inn: str | None
    kpp: str | None
    ogrn: str | None
    status: str | None
    address: str | None
    okved: str | None
    management_name: str | None
    management_post: str | None


def load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


class DadataPartyClient:
    """Client for DaData party suggestions API."""

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError("DADATA_API_KEY is empty")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Token {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

    def suggest_party(self, query: str, count: int = 3) -> list[dict]:
        response = self.session.post(
            SUGGEST_PARTY_URL,
            json={"query": query, "count": count},
            timeout=20,
        )
        response.raise_for_status()
        return response.json().get("suggestions", [])

    def get_best_party(self, query: str, role: str) -> DadataParty:
        suggestions = self.suggest_party(query, count=1)
        if not suggestions:
            return DadataParty(
                query=query,
                role=role,
                name=None,
                inn=None,
                kpp=None,
                ogrn=None,
                status=None,
                address=None,
                okved=None,
                management_name=None,
                management_post=None,
            )

        suggestion = suggestions[0]
        data = suggestion.get("data") or {}
        management = data.get("management") or {}
        state = data.get("state") or {}
        address = data.get("address") or {}

        return DadataParty(
            query=query,
            role=role,
            name=suggestion.get("value"),
            inn=data.get("inn"),
            kpp=data.get("kpp"),
            ogrn=data.get("ogrn"),
            status=state.get("status"),
            address=address.get("unrestricted_value"),
            okved=data.get("okved"),
            management_name=management.get("name"),
            management_post=management.get("post"),
        )


def collect_counterparties(queries: pd.DataFrame, api_key: str) -> pd.DataFrame:
    client = DadataPartyClient(api_key)
    rows = []
    for row in queries.itertuples(index=False):
        party = client.get_best_party(query=row.query, role=row.role)
        rows.append(party.__dict__)
    return pd.DataFrame(rows)

