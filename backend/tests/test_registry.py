"""Provider 폴백/라우팅 테스트 (DESIGN §3 핵심 로직)."""

from __future__ import annotations

import pytest

from app.models import DataStatus
from app.providers.last_good import LastGoodStore
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


# ---------------------------------------------------------------------------
# last-good 통합 테스트 (Task 2)
# FakeProvider 는 RATE_LIMITED 를 직접 생성하지 못한다 —
# raise_on_quote=True(→ERROR) 로 일시 실패 폴백을 검증한다.
# ---------------------------------------------------------------------------


async def test_transient_error_serves_last_good_as_stale() -> None:
    # 1) 성공 → 저장.  2) 실패 → STALE 폴백.
    store = LastGoodStore()
    clk: dict[str, float] = {"v": 0.0}
    reg = ProviderRegistry(
        {"US": [FakeProvider("p1", quote_status=DataStatus.DELAYED)]},
        store=store,
        clock=lambda: clk["v"],
    )
    ok = await reg.get_quote("AAPL")
    assert ok.status is DataStatus.DELAYED
    # 이제 제공자가 실패하도록 교체
    clk["v"] = 10.0
    reg2 = ProviderRegistry(
        {"US": [FakeProvider("p1", raise_on_quote=True)]},
        store=store,
        clock=lambda: clk["v"],
    )
    served = await reg2.get_quote("AAPL")
    assert served.status is DataStatus.STALE
    assert served.data is not None
    assert served.source == "p1"  # 원본 소스 보존


async def test_no_data_is_not_overridden_by_stale() -> None:
    store = LastGoodStore()
    reg = ProviderRegistry(
        {"US": [FakeProvider("p1", quote_status=DataStatus.DELAYED)]},
        store=store,
        clock=lambda: 0.0,
    )
    await reg.get_quote("AAPL")  # 저장됨
    reg2 = ProviderRegistry(
        {"US": [FakeProvider("p1", quote_status=DataStatus.NO_DATA)]},
        store=store,
        clock=lambda: 1.0,
    )
    out = await reg2.get_quote("AAPL")
    assert out.status is DataStatus.NO_DATA  # 폴백 안 함(상장폐지 신호 보존)


async def test_needs_key_is_not_overridden_by_stale() -> None:
    store = LastGoodStore()
    reg = ProviderRegistry(
        {"US": [FakeProvider("p1", quote_status=DataStatus.DELAYED)]},
        store=store,
        clock=lambda: 0.0,
    )
    await reg.get_quote("AAPL")
    reg2 = ProviderRegistry(
        {"US": [FakeProvider("p1", quote_status=DataStatus.NEEDS_KEY)]},
        store=store,
        clock=lambda: 1.0,
    )
    out = await reg2.get_quote("AAPL")
    assert out.status is DataStatus.NEEDS_KEY  # 조치 가능 신호 보존


async def test_no_last_good_returns_failure() -> None:
    store = LastGoodStore()
    reg = ProviderRegistry(
        {"US": [FakeProvider("p1", raise_on_quote=True)]},
        store=store,
        clock=lambda: 0.0,
    )
    out = await reg.get_quote("AAPL")
    assert out.status is DataStatus.ERROR  # 저장된 적 없으면 실패 그대로


async def test_existing_constructor_without_store_still_works() -> None:
    # 무회귀: 기존 위치 인자 호출이 동작해야 한다.
    p = FakeProvider("p1", quote_status=DataStatus.DELAYED)
    reg = ProviderRegistry({"US": [p]})
    out = await reg.get_quote("AAPL")
    assert out.status is DataStatus.DELAYED
