"""거시 환경 서비스 — FRED(금리·CPI) + yfinance 지수 추세 결합(근거 ③).

예측하지 않는다: 발표값·방향·이동평균선 대비 위치 같은 *사실*만 제공한다.
FRED 상태(NEEDS_KEY/ERROR 등)는 그대로 메트릭에 전파한다(가짜 ❌).
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from typing import Protocol

from ..models import (
    DataStatus,
    IndexTrend,
    MacroConditions,
    MacroMetric,
)
from ..providers.macro_provider import Observation, change, yoy
from ..providers.registry import ProviderRegistry


class _FredLike(Protocol):
    """Structural interface for any FRED-like provider (enables test fakes)."""

    async def observations(
        self, series_id: str, limit: int
    ) -> tuple[DataStatus, list[Observation]]: ...


# (라벨, yfinance 심볼) — 핵심 지수
_INDICES = [
    ("S&P 500", "^GSPC"),
    ("나스닥", "^IXIC"),
]
_PERIOD = "1Y"
_INTERVAL = "1D"
_HAS_DATA = {DataStatus.LIVE, DataStatus.DELAYED, DataStatus.STALE}


def _sma(closes: Sequence[float], n: int) -> float | None:
    if len(closes) < n or n <= 0:
        return None
    return sum(closes[-n:]) / n


class MacroConditionsService:
    def __init__(
        self,
        fred: _FredLike,
        registry: ProviderRegistry,
        *,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._fred = fred
        self._registry = registry
        self._now = now

    async def get_conditions(self) -> MacroConditions:
        rate, cpi, indices = await asyncio.gather(
            self._rate_metric(), self._cpi_metric(), self._index_trends()
        )
        return MacroConditions(rate=rate, cpi=cpi, indices=indices, as_of=self._now())

    async def _rate_metric(self) -> MacroMetric:
        status, obs = await self._fred.observations("DFF", 30)
        if not obs:
            return MacroMetric(
                label="미 기준금리(실효)",
                unit="%",
                status=status,
                source="fred",
            )
        ch = change(obs)
        return MacroMetric(
            label="미 기준금리(실효)",
            value=round(obs[0].value, 2),
            unit="%",
            as_of=obs[0].date,
            change=round(ch, 2) if ch is not None else None,
            status=status,
            source="fred",
        )

    async def _cpi_metric(self) -> MacroMetric:
        status, obs = await self._fred.observations("CPIAUCSL", 13)
        y = yoy(obs)
        if y is None:
            return MacroMetric(
                label="CPI(전년 대비)",
                unit="%",
                status=status,
                source="fred",
                note="전년 동월 데이터가 부족합니다" if obs else None,
            )
        return MacroMetric(
            label="CPI(전년 대비)",
            value=round(y, 1),
            unit="%",
            as_of=obs[0].date,
            status=status,
            source="fred",
        )

    async def _index_trends(self) -> list[IndexTrend]:
        out: list[IndexTrend] = []
        for label, sym in _INDICES:
            env = await self._registry.get_bars(sym, _PERIOD, _INTERVAL)
            if env.data is None or env.status not in _HAS_DATA:
                out.append(IndexTrend(label=label, symbol=sym, status=env.status))
                continue
            closes = [b.close for b in env.data]
            price = closes[-1]
            ma50 = _sma(closes, 50)
            ma200 = _sma(closes, 200)
            out.append(
                IndexTrend(
                    label=label,
                    symbol=sym,
                    price=round(price, 2),
                    vs_ma50_pct=(round((price / ma50 - 1) * 100, 1) if ma50 else None),
                    vs_ma200_pct=(
                        round((price / ma200 - 1) * 100, 1) if ma200 else None
                    ),
                    status=env.status,
                )
            )
        return out
