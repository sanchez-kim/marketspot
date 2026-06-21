"""공시 제공자 파싱 테스트(네트워크 없음).

★ 실제 녹화한 SEC 응답(tests/fixtures, 출처·날짜는 fixtures/README.md)을
파싱해 동작을 검증한다. 숫자/문자열을 지어내지 않는다(CLAUDE.md §1.3).
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from app.models import DataStatus
from app.providers.filings_provider import (
    DartProvider,
    build_ticker_index,
    parse_submissions,
)

_FIX = Path(__file__).parent / "fixtures"


def _load(name: str) -> dict[str, object]:
    data: dict[str, object] = json.loads((_FIX / name).read_text(encoding="utf-8"))
    return data


def test_parse_aapl_submissions_real_fixture() -> None:
    result = parse_submissions(_load("sec_submissions_aapl.json"), limit=20)
    assert result.entity == "Apple Inc."
    assert result.cik == "0000320193"
    assert result.market == "US"
    assert len(result.filings) == 12  # 픽스처에 12건 녹화됨

    # 첫 항목: 실제 값(2026-05-29 접수, Form 4). 날조 아님.
    first = result.filings[0]
    assert first.form == "4"
    assert first.filed == datetime(2026, 5, 29)
    assert first.accession == "0001140361-26-023363"
    # URL 은 대시 제거 + CIK 정수 경로
    assert (
        first.url
        == "https://www.sec.gov/Archives/edgar/data/320193/000114036126023363/"
        "xslF345X06/form4.xml"
    )


def test_parse_voo_fund_filings_real_fixture() -> None:
    """ETF(VOO)는 신탁 단위로 보고된다 — entity 에 신탁명이 그대로 나온다."""
    result = parse_submissions(_load("sec_submissions_voo.json"), limit=20)
    assert result.entity == "VANGUARD INDEX FUNDS"
    assert result.filings[0].form == "NPORT-P"  # 펀드 포트폴리오 공시


def test_parse_respects_limit() -> None:
    result = parse_submissions(_load("sec_submissions_aapl.json"), limit=3)
    assert len(result.filings) == 3


def test_parse_empty_when_no_recent() -> None:
    result = parse_submissions({"cik": 1, "name": "X"}, limit=10)
    assert result.filings == []
    assert result.entity == "X"


def test_build_ticker_index_merges_stock_and_fund() -> None:
    index = build_ticker_index(
        _load("sec_company_tickers.json"), _load("sec_company_tickers_mf.json")
    )
    # 일반주식
    assert index["AAPL"] == "0000320193"
    # 펀드/ETF
    assert index["VOO"] == "0000036405"
    assert index["QQQM"] == "0001378872"


def test_build_ticker_index_prefers_stock_over_fund() -> None:
    """QQQ 는 주식 매핑과 펀드 매핑에 모두 존재 — 주식 CIK 가 우선이어야."""
    stock = {"0": {"cik_str": 1067839, "ticker": "QQQ", "title": "INVESCO QQQ"}}
    fund = {"fields": ["cik", "s", "c", "symbol"], "data": [[9999, "S1", "C1", "QQQ"]]}
    index = build_ticker_index(stock, fund)
    assert index["QQQ"] == "0001067839"


@pytest.mark.asyncio
async def test_dart_needs_key_without_key() -> None:
    env = await DartProvider(api_key="").get_filings("005930.KS")
    assert env.status is DataStatus.NEEDS_KEY
    assert env.data is None


@pytest.mark.asyncio
async def test_dart_no_data_with_key_unwired() -> None:
    """키가 있어도 corp_code 미연동이면 NO_DATA 로 정직하게 표기(가짜 ❌)."""
    env = await DartProvider(api_key="dummy").get_filings("005930.KS")
    assert env.status is DataStatus.NO_DATA
    assert env.data is None
