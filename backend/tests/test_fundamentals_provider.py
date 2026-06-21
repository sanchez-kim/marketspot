"""기본정보 파싱 테스트 (네트워크 없음).

실제 yfinance 응답(tests/fixtures)을 파싱해 주식/ETF 필드를 검증한다.
숫자/문자열을 지어내지 않는다(CLAUDE.md §1.3).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.providers.fundamentals_provider import parse_fundamentals

_FIX = Path(__file__).parent / "fixtures"


def _load(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((_FIX / name).read_text(encoding="utf-8"))
    return data


def test_parse_stock_fundamentals() -> None:
    d = _load("yf_fundamentals_aapl.json")
    f = parse_fundamentals("AAPL", d["info"], d["holdings"])
    assert f.type == "EQUITY"
    assert f.sector == "Technology"
    assert f.industry == "Consumer Electronics"
    assert f.pe_ratio is not None and 30 < f.pe_ratio < 45
    assert f.market_cap is not None and f.market_cap > 1e12
    assert f.summary is not None and "Apple" in f.summary
    assert f.top_holdings == []  # 개별주식은 보유종목 없음


def test_parse_etf_fundamentals_with_holdings() -> None:
    d = _load("yf_fundamentals_voo.json")
    f = parse_fundamentals("VOO", d["info"], d["holdings"])
    assert f.type == "ETF"
    assert f.category == "Large Blend"
    assert f.total_assets is not None and f.total_assets > 1e12
    assert len(f.top_holdings) == 10
    top = f.top_holdings[0]
    assert top.name  # 예: "NVIDIA Corp"
    assert top.weight > 1  # 비중 % (분수 아님)


def test_parse_long_summary_truncated() -> None:
    info = {"longName": "X", "longBusinessSummary": "가" * 800}
    f = parse_fundamentals("X", info, [])
    assert f.summary is not None and f.summary.endswith("…")
    assert len(f.summary) <= 601


def test_parse_missing_fields_stay_null() -> None:
    f = parse_fundamentals("Z", {"quoteType": "EQUITY"}, [])
    assert f.name is None
    assert f.pe_ratio is None
    assert f.sector is None
