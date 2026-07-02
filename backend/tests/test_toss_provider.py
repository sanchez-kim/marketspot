"""TossQuoteProvider 테스트 (Phase A Wave 3, 결정적 — 실네트워크 없음).

TossClient 는 페이크로 주입한다(테스트 대상은 프로바이더의 폴백/캐시/변환
로직이지 클라이언트가 아니므로 외부 의존을 페이크로 대체 — CLAUDE.md §1.2
위반 아님). 키 유무는 ``STOCK_TERMINAL_DATA_DIR`` 로 격리한 tmp
``settings.json`` 으로 제어한다(tests/test_toss_router.py 와 동일 패턴).
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.config import ApiKeys, Settings, save_settings
from app.models import Bar, DataEnvelope, DataStatus, Quote
from app.providers.base import QuoteProvider
from app.providers.registry import ProviderRegistry
from app.providers.toss_client import TossCandle, TossClient, TossPrice
from app.providers.toss_provider import TossQuoteProvider


@pytest.fixture(autouse=True)
def _tmp_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("STOCK_TERMINAL_DATA_DIR", str(tmp_path))
    yield


def _configure_keys() -> None:
    save_settings(Settings(api_keys=ApiKeys(toss_app_key="k", toss_app_secret="s")))


def _no_keys() -> None:
    save_settings(Settings())  # 키 없음


def _candle(day: int, close: float) -> TossCandle:
    return TossCandle(
        time=datetime(2026, 3, day, tzinfo=UTC),
        open=close,
        high=close,
        low=close,
        close=close,
        volume=None,
    )


class FakeTossClient:
    """서비스가 호출하는 메서드만 구현한 페이크(실 모델 반환)."""

    def __init__(
        self,
        *,
        prices: list[TossPrice] | None = None,
        candles: list[TossCandle] | None = None,
    ) -> None:
        default_prices = [TossPrice(symbol="005930", last_price=72000, currency="KRW")]
        self._prices = prices if prices is not None else default_prices
        self._candles = candles if candles is not None else []
        self.closed = 0
        self.price_calls = 0
        self.candle_calls = 0

    async def get_prices(self, symbols: list[str]) -> list[TossPrice]:
        self.price_calls += 1
        return self._prices

    async def get_candles(
        self, symbol: str, interval: str, count: int
    ) -> list[TossCandle]:
        self.candle_calls += 1
        return self._candles

    async def aclose(self) -> None:
        self.closed += 1


def _make_provider(
    client: FakeTossClient | None,
    *,
    clock: Callable[[], float] = lambda: 0.0,
    factory_calls: list[int] | None = None,
) -> TossQuoteProvider:
    calls = factory_calls if factory_calls is not None else []

    def factory() -> TossClient:
        calls.append(1)
        assert client is not None  # 키 없음 케이스에선 절대 호출되면 안 됨
        return client  # type: ignore[return-value]

    def client_factory_provider() -> Callable[[], TossClient]:
        return factory

    return TossQuoteProvider(client_factory_provider, clock=clock)


def _explode_factory_provider() -> Callable[[], TossClient]:
    def factory() -> TossClient:
        raise AssertionError("클라이언트 팩토리가 호출되면 안 됨(네트워크 시도 없음)")

    return factory


# ── change/changePct 계산 ────────────────────────────────────────────────────


async def test_get_quote_computes_change_from_two_candles() -> None:
    _configure_keys()
    client = FakeTossClient(
        prices=[TossPrice(symbol="005930", last_price=72500, currency="KRW")],
        # 오름차순 2개 → prev_close 는 '마지막 직전'(둘째-끝) = 70000.
        candles=[_candle(24, 70000), _candle(25, 71000)],
    )
    provider = _make_provider(client)

    env = await provider.get_quote("005930")

    assert env.status is DataStatus.LIVE
    assert env.data is not None
    assert env.data.price == 72500
    assert env.data.change == pytest.approx(2500)
    assert env.data.change_pct == pytest.approx(2500 / 70000 * 100)


async def test_get_quote_uses_second_to_last_candle_even_if_unsorted() -> None:
    _configure_keys()
    client = FakeTossClient(
        prices=[TossPrice(symbol="005930", last_price=100, currency="KRW")],
        # 뒤섞인 순서로 와도 time 기준 정렬 후 마지막 직전 값을 prev_close 로.
        candles=[_candle(25, 90), _candle(23, 80), _candle(24, 85)],
    )
    provider = _make_provider(client)

    env = await provider.get_quote("005930")

    assert env.data is not None
    # 정렬: 23(80), 24(85), 25(90) → prev_close = 85(둘째-끝)
    assert env.data.change == pytest.approx(15)


# ── 캔들 부족 → None (지어내지 않음) ─────────────────────────────────────────


@pytest.mark.parametrize("candles", [[], [_candle(24, 70000)]])
async def test_get_quote_change_is_none_when_candles_insufficient(
    candles: list[TossCandle],
) -> None:
    _configure_keys()
    client = FakeTossClient(
        prices=[TossPrice(symbol="005930", last_price=72000, currency="KRW")],
        candles=candles,
    )
    provider = _make_provider(client)

    env = await provider.get_quote("005930")

    assert env.status is DataStatus.LIVE
    assert env.data is not None
    assert env.data.price == 72000
    assert env.data.change is None
    assert env.data.change_pct is None


# ── 키 없음 → NEEDS_KEY, 네트워크 시도 없음 ──────────────────────────────────


async def test_get_quote_needs_key_when_unconfigured_and_never_touches_client() -> None:
    _no_keys()
    provider = TossQuoteProvider(_explode_factory_provider)

    env = await provider.get_quote("005930")

    assert env.status is DataStatus.NEEDS_KEY
    assert env.data is None


# ── get_bars 는 항상 NO_DATA ──────────────────────────────────────────────────


async def test_get_bars_always_no_data_regardless_of_keys() -> None:
    _configure_keys()
    provider_with_keys = TossQuoteProvider(_explode_factory_provider)
    env1 = await provider_with_keys.get_bars("005930", "1Y", "1d")
    assert env1.status is DataStatus.NO_DATA

    _no_keys()
    provider_without_keys = TossQuoteProvider(_explode_factory_provider)
    env2 = await provider_without_keys.get_bars("005930", "1Y", "1d")
    assert env2.status is DataStatus.NO_DATA


# ── TTL 캐시 ──────────────────────────────────────────────────────────────────


async def test_ttl_cache_avoids_refetch_within_window_and_refetches_after() -> None:
    _configure_keys()
    client = FakeTossClient(
        prices=[TossPrice(symbol="005930", last_price=72000, currency="KRW")],
        candles=[_candle(24, 70000), _candle(25, 71000)],
    )
    clock_box = {"t": 0.0}
    calls: list[int] = []
    provider = _make_provider(client, clock=lambda: clock_box["t"], factory_calls=calls)

    env1 = await provider.get_quote("005930")
    assert env1.status is DataStatus.LIVE
    assert len(calls) == 1
    assert client.price_calls == 1

    # TTL(10s) 이내 → 재호출 없음.
    clock_box["t"] = 5.0
    env2 = await provider.get_quote("005930")
    assert env2.status is DataStatus.LIVE
    assert env2.data == env1.data
    assert len(calls) == 1  # 팩토리 재호출 안 됨
    assert client.price_calls == 1

    # TTL 경과 → 재호출.
    clock_box["t"] = 10.5
    env3 = await provider.get_quote("005930")
    assert env3.status is DataStatus.LIVE
    assert len(calls) == 2
    assert client.price_calls == 2


# ── ProviderRegistry 를 통한 KR 체인 폴백 ────────────────────────────────────


class _StubYfLikeProvider:
    """yfinance 자리를 대신하는 최소 스텁(항상 성공)."""

    name = "yf-stub"

    def __init__(self) -> None:
        self.quote_calls = 0

    async def get_quote(self, symbol: str) -> DataEnvelope[Quote]:
        self.quote_calls += 1
        return DataEnvelope.ok(
            Quote(symbol=symbol, price=99.0),
            source=self.name,
            status=DataStatus.LIVE,
        )

    async def get_bars(
        self, symbol: str, period: str, interval: str
    ) -> DataEnvelope[list[Bar]]:
        return DataEnvelope[list[Bar]].empty(
            source=self.name, status=DataStatus.NO_DATA
        )


async def test_kr_chain_falls_through_toss_to_next_provider_when_no_keys() -> None:
    _no_keys()
    toss = TossQuoteProvider(_explode_factory_provider)
    stub_yf = _StubYfLikeProvider()
    kr_chain: list[QuoteProvider] = [toss, stub_yf]
    registry = ProviderRegistry({"KR": kr_chain})

    env = await registry.get_quote("005930.KS")

    assert env.status is DataStatus.LIVE
    assert env.source == "yf-stub"
    assert stub_yf.quote_calls == 1
