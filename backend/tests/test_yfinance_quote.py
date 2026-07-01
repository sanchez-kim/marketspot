"""yfinance 시세 파싱 regression 테스트(네트워크 없음).

실제 ``FastInfo`` 를 흉내 낸 가짜 객체로 검증한다: dict 키는 camelCase 지만
속성은 snake_case 다. 이 구분을 놓쳐 시세가 NO_DATA 로 나오던 버그를 고정한다.
"""

from __future__ import annotations

import pytest

from app.models import DataStatus, Quote
from app.providers import yfinance_provider
from app.providers.yfinance_provider import (
    YFinanceProvider,
    _is_rate_limited,
    quote_from_fast_info,
)


class FakeFastInfo:
    """yfinance FastInfo 모사: snake_case 속성 + camelCase dict 키."""

    def __init__(self, last_price: float, previous_close: float, currency: str) -> None:
        self.last_price = last_price
        self.previous_close = previous_close
        self.currency = currency
        self._d = {
            "lastPrice": last_price,
            "previousClose": previous_close,
            "currency": currency,
        }

    def get(self, key: str, default: object = None) -> object:
        # 실제 FastInfo 처럼 camelCase 키만 인식 → 'last_price' 로는 못 찾음
        return self._d.get(key, default)


def test_parses_quote_via_attribute_access() -> None:
    fi = FakeFastInfo(last_price=696.06, previous_close=690.06, currency="USD")
    q = quote_from_fast_info("VOO", fi)
    assert q is not None
    assert q.price == 696.06
    assert q.currency == "USD"
    assert q.change is not None
    assert abs(q.change - 6.0) < 1e-6
    assert q.change_pct is not None
    assert q.change_pct > 0


def test_regression_dict_get_snake_case_would_fail() -> None:
    # 과거 버그 경로(.get('last_price'))는 None 을 반환했음을 명시적으로 고정
    fi = FakeFastInfo(last_price=100.0, previous_close=100.0, currency="USD")
    assert fi.get("last_price") is None  # camelCase 키만 있으므로
    # 그러나 올바른 구현(속성 접근)은 정상 동작해야 한다
    q = quote_from_fast_info("X", fi)
    assert q is not None
    assert q.price == 100.0


def test_no_price_returns_none() -> None:
    class Empty:
        pass

    assert quote_from_fast_info("X", Empty()) is None


async def test_unknown_symbol_is_no_data_not_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # yfinance fast_info raises KeyError('exchangeTimezoneName') for symbols it
    # has no data for. That's a data-availability gap (NO_DATA), not a system
    # failure (ERROR) — reporting ERROR misleads the user into thinking the app
    # is broken when the ticker simply does not exist.
    def boom(_yf: object, _sym: str) -> Quote | None:
        raise KeyError("exchangeTimezoneName")

    monkeypatch.setattr(yfinance_provider, "_fetch_quote", boom)
    env = await YFinanceProvider().get_quote("ZZZZNOTREAL")
    assert env.status is DataStatus.NO_DATA
    assert env.data is None


async def test_korean_quote_is_stale_not_delayed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # KR data via yfinance is end-of-day, not 15-min delayed. Bars already report
    # STALE; the quote path must agree instead of claiming US-style DELAYED/15.
    monkeypatch.setattr(
        yfinance_provider,
        "_fetch_quote",
        lambda _yf, sym: Quote(symbol=sym, price=70000.0),
    )
    env = await YFinanceProvider().get_quote("005930.KS")
    assert env.status is DataStatus.STALE
    assert env.delay_minutes is None


async def test_us_quote_stays_delayed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        yfinance_provider,
        "_fetch_quote",
        lambda _yf, sym: Quote(symbol=sym, price=688.1),
    )
    env = await YFinanceProvider().get_quote("VOO")
    assert env.status is DataStatus.DELAYED
    assert env.delay_minutes == 15


# ── Task 3: 전용 풀·타임아웃·레이트리밋 분류 ──────────────────────────────


async def test_rate_limit_exception_maps_to_rate_limited(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """메시지 기반 레이트리밋 폴백: _is_rate_limited 패턴 감지 → RATE_LIMITED 반환."""

    class FakeRateLimit(Exception):
        pass

    def boom(*a: object, **k: object) -> Quote | None:
        raise FakeRateLimit("Too Many Requests. Rate limited.")

    monkeypatch.setattr(yfinance_provider, "_fetch_quote", boom)
    env = await YFinanceProvider().get_quote("AAPL")
    assert env.status is DataStatus.RATE_LIMITED


async def test_timeout_maps_to_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """TimeoutError 는 ERROR 로 분류(재시도 없음)."""

    def boom(*a: object, **k: object) -> Quote | None:
        raise TimeoutError("응답 시간 초과")

    monkeypatch.setattr(yfinance_provider, "_fetch_quote", boom)
    env = await YFinanceProvider().get_quote("AAPL")
    assert env.status is DataStatus.ERROR


def test_is_rate_limited_detects_429_message() -> None:
    """_is_rate_limited: 429 메시지 감지 + KeyError 는 False."""
    assert _is_rate_limited(Exception("HTTP 429 Too Many Requests")) is True
    assert _is_rate_limited(KeyError("exchangeTimezoneName")) is False
