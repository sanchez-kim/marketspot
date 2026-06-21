"""심볼 검색 파싱 테스트 (네트워크 없음).

실제 Yahoo search 응답(tests/fixtures)을 파싱해 종류 필터·이름 선택을 검증한다.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.providers.search_provider import parse_search

_FIX = Path(__file__).parent / "fixtures"


def _load(name: str) -> dict[str, object]:
    data: dict[str, object] = json.loads((_FIX / name).read_text(encoding="utf-8"))
    return data


def test_parse_filters_to_allowed_types() -> None:
    results = parse_search(_load("yahoo_search_plt.json"), limit=10)
    symbols = [m.symbol for m in results]
    # PLTR(EQUITY)/PLTW(ETF) 등은 포함, PLT=F(FUTURE)는 제외
    assert "PLTR" in symbols
    assert "PLT=F" not in symbols
    assert all(m.type in {"EQUITY", "ETF", "INDEX", "MUTUALFUND"} for m in results)


def test_parse_prefers_longname_then_shortname() -> None:
    results = parse_search(_load("yahoo_search_plt.json"))
    pltr = next(m for m in results if m.symbol == "PLTR")
    assert pltr.name == "Palantir Technologies Inc."
    assert pltr.type == "EQUITY"
    assert pltr.exchange == "NASDAQ"


def test_parse_respects_limit() -> None:
    assert len(parse_search(_load("yahoo_search_plt.json"), limit=2)) == 2


def test_parse_empty_on_missing_quotes() -> None:
    assert parse_search({}) == []
    assert parse_search({"quotes": "nope"}) == []
