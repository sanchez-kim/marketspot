"""밸류 컨텍스트 서비스 — 기본정보 + 가격 위치(근거 ①).

PER·배당·52주 밴드(기존 Fundamentals)에 52주 위치와 200일선 대비(과열도)를
더한다. 판단(싸다/비싸다)은 하지 않고 사실만 제공한다. 5년 평균 PER 은
yfinance 한계로 제공하지 않으며 그 사실을 note 로 알린다(가짜 ❌).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from ..models import DataStatus, Fundamentals, ValuationContext
from ..providers.registry import ProviderRegistry

_PERIOD = "1Y"
_INTERVAL = "1D"
_HAS_DATA = {DataStatus.LIVE, DataStatus.DELAYED, DataStatus.STALE}
_PE_NOTE = "5년 평균 PER 은 무료 데이터 한계로 제공하지 않습니다(현재 PER만)."


class _FundamentalsProvider(Protocol):
    """기본정보 제공자 프로토콜 — 테스트용 fake 와 실제 제공자 모두 충족."""

    async def get(self, symbol: str) -> Fundamentals: ...


def week52_position(price: float, low: float, high: float) -> float | None:
    """52주 밴드 내 위치(%). high==low 면 None."""
    if high <= low:
        return None
    return round((price - low) / (high - low) * 100, 1)


def _sma(closes: Sequence[float], n: int) -> float | None:
    if len(closes) < n or n <= 0:
        return None
    return sum(closes[-n:]) / n


class ValuationService:
    def __init__(
        self,
        fundamentals: _FundamentalsProvider,
        registry: ProviderRegistry,
    ) -> None:
        self._fund = fundamentals
        self._registry = registry

    async def get(self, symbol: str) -> ValuationContext:
        fund: Fundamentals = await self._fund.get(symbol)
        if fund.status not in _HAS_DATA:
            return ValuationContext(
                symbol=symbol.upper(),
                status=fund.status,
                message=fund.message or "기본정보를 가져오지 못했습니다",
            )

        price: float | None = None
        vs_ma200: float | None = None
        position: float | None = None

        env = await self._registry.get_bars(symbol, _PERIOD, _INTERVAL)
        if env.data is not None and env.status in _HAS_DATA and env.data:
            closes = [b.close for b in env.data]
            price = closes[-1]
            ma200 = _sma(closes, 200)
            if ma200:
                vs_ma200 = round((price / ma200 - 1) * 100, 1)
            if fund.week52_low is not None and fund.week52_high is not None:
                position = week52_position(price, fund.week52_low, fund.week52_high)

        return ValuationContext(
            symbol=symbol.upper(),
            status=fund.status,
            pe_ratio=fund.pe_ratio,
            pe_5y_avg=None,
            dividend_yield=fund.dividend_yield,
            week52_high=fund.week52_high,
            week52_low=fund.week52_low,
            week52_position_pct=position,
            price=price,
            vs_ma200_pct=vs_ma200,
            note=_PE_NOTE,
        )
