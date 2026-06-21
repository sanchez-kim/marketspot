"""심볼 검색 제공자 (Yahoo Finance search, 키 불필요).

자동완성용. 검색 실패 시 가짜 결과를 만들지 않고 빈 목록을 반환한다 — 제안이
없을 뿐이며 잘못된 종목을 지어내지 않는다.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, runtime_checkable

import httpx

from ..models import SymbolMatch

JsonDict = Mapping[str, object]

_SEARCH_URL = "https://query1.finance.yahoo.com/v1/finance/search"
# 자동완성에 보여줄 종류만 통과(선물/옵션/통화 등 제외)
_ALLOWED_TYPES = {"EQUITY", "ETF", "INDEX", "MUTUALFUND"}


@runtime_checkable
class SearchProvider(Protocol):
    async def search(self, query: str, limit: int = 8) -> list[SymbolMatch]: ...


def parse_search(payload: JsonDict, limit: int = 8) -> list[SymbolMatch]:
    """Yahoo search JSON → SymbolMatch 목록 (순수 함수)."""
    quotes = payload.get("quotes")
    if not isinstance(quotes, list):
        return []
    out: list[SymbolMatch] = []
    for q in quotes:
        if not isinstance(q, Mapping):
            continue
        symbol = q.get("symbol")
        qtype = q.get("quoteType")
        if not isinstance(symbol, str) or not symbol:
            continue
        if not isinstance(qtype, str) or qtype not in _ALLOWED_TYPES:
            continue
        long_name = q.get("longname")
        short_name = q.get("shortname")
        name = (
            long_name
            if isinstance(long_name, str) and long_name
            else short_name
            if isinstance(short_name, str)
            else symbol
        )
        exch = q.get("exchDisp")
        out.append(
            SymbolMatch(
                symbol=symbol,
                name=name,
                type=qtype,
                exchange=exch if isinstance(exch, str) else None,
            )
        )
        if len(out) >= limit:
            break
    return out


class YahooSearchProvider:
    name = "yahoo-search"

    async def search(self, query: str, limit: int = 8) -> list[SymbolMatch]:
        q = query.strip()
        if not q:
            return []
        params = {"q": q, "quotesCount": str(limit * 2), "newsCount": "0"}
        headers = {"User-Agent": "Mozilla/5.0 (MarketSpot)"}
        try:
            async with httpx.AsyncClient(timeout=8, headers=headers) as client:
                resp = await client.get(_SEARCH_URL, params=params)
                resp.raise_for_status()
                payload = resp.json()
        except (httpx.HTTPError, ValueError):
            return []  # 제안 없음(가짜 종목 ❌)
        return parse_search(payload, limit)
