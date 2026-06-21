"""공시 서비스 라우팅 테스트(네트워크 없음).

시장(US/KR)별로 올바른 제공자가 선택되는지, 제공자가 없으면 정직한 상태가
나오는지 검증한다.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from app.models import DataStatus, Filing
from app.providers.filings_provider import DartProvider
from app.services.filings import FilingsService

from .fakes import FakeFilingsProvider

_FILING = Filing(
    form="10-K",
    title="Annual report",
    filed=datetime(2026, 1, 2),
    url="https://example.com/x",
    accession="0000000000-26-000001",
)


@pytest.mark.asyncio
async def test_us_symbol_routes_to_sec_provider() -> None:
    svc = FilingsService(
        {"US": FakeFilingsProvider([_FILING]), "KR": DartProvider(api_key="")}
    )
    env = await svc.get_filings("AAPL")
    assert env.source == "fake-filings"
    assert env.status is DataStatus.DELAYED
    assert env.data is not None
    assert env.data.filings[0].form == "10-K"


@pytest.mark.asyncio
async def test_kr_symbol_routes_to_dart_needs_key() -> None:
    svc = FilingsService(
        {"US": FakeFilingsProvider([_FILING]), "KR": DartProvider(api_key="")}
    )
    env = await svc.get_filings("005930.KS")
    assert env.source == "dart"
    assert env.status is DataStatus.NEEDS_KEY


@pytest.mark.asyncio
async def test_missing_market_provider_returns_no_data() -> None:
    svc = FilingsService({"US": FakeFilingsProvider([_FILING])})
    env = await svc.get_filings("005930.KS")  # KR 제공자 없음
    assert env.status is DataStatus.NO_DATA
    assert env.data is None
