"""Provider 폴백/라우팅 테스트 (DESIGN §3 핵심 로직)."""

from __future__ import annotations

import pytest

from app.models import DataStatus
from app.providers.registry import ProviderRegistry

from .fakes import FakeProvider


@pytest.mark.asyncio
async def test_first_provider_with_data_wins_and_short_circuits() -> None:
    p1 = FakeProvider("p1", quote_status=DataStatus.LIVE)
    p2 = FakeProvider("p2", quote_status=DataStatus.LIVE)
    reg = ProviderRegistry({"US": [p1, p2]})

    env = await reg.get_quote("AAPL")

    assert env.status is DataStatus.LIVE
    assert env.source == "p1"
    assert p1.quote_calls == 1
    assert p2.quote_calls == 0  # 첫 제공자 성공 → 두번째 호출 안 함


@pytest.mark.asyncio
async def test_falls_back_to_next_provider_on_no_data() -> None:
    p1 = FakeProvider("p1", quote_status=DataStatus.NO_DATA)
    p2 = FakeProvider("p2", quote_status=DataStatus.LIVE)
    reg = ProviderRegistry({"US": [p1, p2]})

    env = await reg.get_quote("AAPL")

    assert env.status is DataStatus.LIVE
    assert env.source == "p2"  # 실제 사용된 출처가 기록됨
    assert p1.quote_calls == 1
    assert p2.quote_calls == 1


@pytest.mark.asyncio
async def test_provider_exception_becomes_error_and_continues() -> None:
    p1 = FakeProvider("p1", raise_on_quote=True)
    p2 = FakeProvider("p2", quote_status=DataStatus.LIVE)
    reg = ProviderRegistry({"US": [p1, p2]})

    env = await reg.get_quote("AAPL")

    assert env.status is DataStatus.LIVE
    assert env.source == "p2"


@pytest.mark.asyncio
async def test_all_fail_prefers_actionable_status() -> None:
    # NEEDS_KEY 가 NO_DATA 보다 우선(사용자가 행동 가능)
    p1 = FakeProvider("p1", quote_status=DataStatus.NO_DATA)
    p2 = FakeProvider("p2", quote_status=DataStatus.NEEDS_KEY)
    reg = ProviderRegistry({"US": [p1, p2]})

    env = await reg.get_quote("AAPL")

    assert env.data is None
    assert env.status is DataStatus.NEEDS_KEY


@pytest.mark.asyncio
async def test_empty_chain_returns_no_data() -> None:
    reg = ProviderRegistry({"US": []})
    env = await reg.get_quote("AAPL")
    assert env.status is DataStatus.NO_DATA
    assert env.data is None


@pytest.mark.asyncio
async def test_routes_korean_symbol_to_kr_chain() -> None:
    us = FakeProvider("us", quote_status=DataStatus.LIVE)
    kr = FakeProvider("kr", quote_status=DataStatus.LIVE)
    reg = ProviderRegistry({"US": [us], "KR": [kr]})

    env = await reg.get_quote("005930.KS")

    assert env.source == "kr"
    assert kr.quote_calls == 1
    assert us.quote_calls == 0
