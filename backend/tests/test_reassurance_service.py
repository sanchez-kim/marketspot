"""안심 서비스(하락 맥락화) 테스트 (네트워크 무).

정직성 검증: 데이터 부족/실패는 만들어내지 않고 상태로 표기, 진행 중 하락 제외,
개별 종목 단서, 캐시.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

import pytest

from app.models import Bar, DataEnvelope, DataStatus, Quote, SymbolMatch
from app.providers.registry import ProviderRegistry
from app.services.reassurance import ReassuranceService


def _bars(closes: Sequence[float], step_days: int) -> list[Bar]:
    base = datetime(2020, 1, 1, tzinfo=UTC)
    return [
        Bar(
            time=base + timedelta(days=i * step_days),
            open=c,
            high=c,
            low=c,
            close=c,
            volume=1.0,
        )
        for i, c in enumerate(closes)
    ]


class _BarsProvider:
    name = "fake-bars"

    def __init__(
        self,
        closes: Sequence[float],
        *,
        step_days: int = 1,
        status: DataStatus = DataStatus.DELAYED,
    ) -> None:
        self._closes = closes
        self._step = step_days
        self._status = status
        self.bars_calls = 0

    async def get_quote(self, symbol: str) -> DataEnvelope[Quote]:
        return DataEnvelope[Quote].empty(source=self.name, status=DataStatus.NO_DATA)

    async def get_bars(
        self, symbol: str, period: str, interval: str
    ) -> DataEnvelope[list[Bar]]:
        self.bars_calls += 1
        if self._status not in (DataStatus.LIVE, DataStatus.DELAYED, DataStatus.STALE):
            return DataEnvelope[list[Bar]].empty(
                source=self.name, status=self._status, message="no data"
            )
        bars = _bars(self._closes, self._step)
        return DataEnvelope.ok(
            bars, source=self.name, status=self._status, as_of=bars[-1].time
        )


class _Search:
    def __init__(self, type_: str | None) -> None:
        self._t = type_

    async def search(self, query: str, limit: int = 8) -> list[SymbolMatch]:
        if self._t is None:
            return []
        return [SymbolMatch(symbol=query, name=query, type=self._t)]


def _clock() -> float:
    return 1000.0


# -20% 빠졌다 회복 후 새 고점. step 200일 → 약 3.8년 span(이력 충분)
_RECOVER = [100, 110, 99, 88, 105, 110, 120]


def _svc(provider: _BarsProvider, search: _Search | None = None) -> ReassuranceService:
    reg = ProviderRegistry({"US": [provider]})
    return ReassuranceService(reg, search, clock=_clock)


@pytest.mark.asyncio
async def test_builds_context_with_base_rates() -> None:
    ctx = await _svc(
        _BarsProvider(_RECOVER, step_days=200), _Search("ETF")
    ).get_context("VOO")
    assert ctx.status is DataStatus.DELAYED
    assert ctx.current_drawdown_pct == pytest.approx(0.0)  # 새 고점
    assert ctx.worst_drawdown_pct == pytest.approx(-20.0)
    assert ctx.comparable_count == 1  # 5% 기준 이상 1건
    assert ctx.recovered_count == 1
    assert ctx.median_recovery_days == 400  # (5-3)*200
    assert ctx.limited_history is False  # ~3.8년
    assert ctx.note is None  # ETF 는 회복-단서 없음


@pytest.mark.asyncio
async def test_equity_gets_recovery_caveat() -> None:
    ctx = await _svc(
        _BarsProvider(_RECOVER, step_days=200), _Search("EQUITY")
    ).get_context("AAPL")
    assert ctx.asset_type == "EQUITY"
    assert ctx.note is not None  # 개별 종목 회복 미보장 단서


@pytest.mark.asyncio
async def test_short_history_flagged_not_fabricated() -> None:
    ctx = await _svc(_BarsProvider(_RECOVER, step_days=5)).get_context("NEW")
    assert ctx.limited_history is True  # span 30일
    assert ctx.history_years is not None and ctx.history_years < 1


@pytest.mark.asyncio
async def test_no_data_status_propagated() -> None:
    ctx = await _svc(_BarsProvider([], status=DataStatus.NEEDS_KEY)).get_context("XYZ")
    assert ctx.status is DataStatus.NEEDS_KEY
    assert ctx.current_drawdown_pct is None  # 가짜 숫자 ❌
    assert ctx.comparable_count == 0


@pytest.mark.asyncio
async def test_context_is_cached() -> None:
    provider = _BarsProvider(_RECOVER, step_days=200)
    svc = _svc(provider)
    await svc.get_context("VOO")
    await svc.get_context("VOO")
    assert provider.bars_calls == 1  # 두 번째는 캐시
