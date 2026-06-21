"""안심 레이어 서비스 — 하락 맥락화.

기존 차트 봉(10년치)을 재사용해 ``DrawdownContext`` 를 만든다. 예측하지 않고
역사적 기저율만 제공하며, 데이터가 부족하거나 조회에 실패하면 정직하게
표기한다(가짜 숫자/안심 ❌).
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable

from ..analytics.drawdown import analyze_drawdowns, base_rates
from ..cache import TTLCache
from ..models import Bar, DataEnvelope, DataStatus, DrawdownContext
from ..providers.registry import ProviderRegistry
from ..providers.search_provider import SearchProvider

_PERIOD = "10Y"
_INTERVAL = "1D"
_THRESHOLD_FLOOR = 0.05  # 현재 낙폭이 얕아도 최소 5% 기준으로 기저율 산출
_MIN_YEARS = 3.0  # 이보다 짧으면 기저율 비신뢰
_CONTEXT_TTL = 3600.0  # 1시간 (천천히 변함)

_HAS_DATA = {DataStatus.LIVE, DataStatus.DELAYED, DataStatus.STALE}


class ReassuranceService:
    def __init__(
        self,
        registry: ProviderRegistry,
        search: SearchProvider | None = None,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._registry = registry
        self._search = search
        self._cache: TTLCache[DrawdownContext] = TTLCache(clock=clock)

    async def get_context(self, symbol: str) -> DrawdownContext:
        key = symbol.upper()
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        env: DataEnvelope[list[Bar]] = await self._registry.get_bars(
            symbol, _PERIOD, _INTERVAL
        )
        if env.data is None or env.status not in _HAS_DATA:
            return DrawdownContext(
                symbol=symbol,
                status=env.status,
                message=env.message or "시세 이력을 가져오지 못했습니다",
            )

        ctx = await self._build(symbol, env)
        self._cache.set(key, ctx, _CONTEXT_TTL)
        return ctx

    async def get_contexts(self, symbols: list[str]) -> list[DrawdownContext]:
        """여러 종목의 하락 맥락을 동시에(각각 캐시) — 홈 대시보드용."""
        unique = list(dict.fromkeys(s.strip() for s in symbols if s.strip()))
        return await asyncio.gather(*(self.get_context(s) for s in unique))

    async def _build(
        self, symbol: str, env: DataEnvelope[list[Bar]]
    ) -> DrawdownContext:
        bars = env.data or []
        stats = analyze_drawdowns(bars)
        if stats is None:
            return DrawdownContext(
                symbol=symbol,
                status=DataStatus.NO_DATA,
                message="이력이 너무 짧아 분석할 수 없습니다",
            )

        history_years = stats.span_days / 365.25
        threshold = max(abs(stats.current_drawdown), _THRESHOLD_FLOOR)
        rates = base_rates(stats, threshold)
        limited = history_years < _MIN_YEARS
        asset_type = await self._asset_type(symbol)

        return DrawdownContext(
            symbol=symbol,
            status=env.status,
            as_of=env.as_of or bars[-1].time,
            asset_type=asset_type,
            current_price=bars[-1].close,
            peak_price=stats.peak,
            peak_date=stats.peak_date,
            current_drawdown_pct=round(stats.current_drawdown * 100, 1),
            history_years=round(history_years, 1),
            threshold_pct=round(threshold * 100, 1),
            comparable_count=rates.comparable_count,
            recovered_count=rates.recovered_count,
            median_recovery_days=rates.median_recovery_days,
            max_recovery_days=rates.max_recovery_days,
            worst_drawdown_pct=round(stats.worst * 100, 1),
            limited_history=limited,
            note=_note(asset_type),
        )

    async def _asset_type(self, symbol: str) -> str | None:
        """검색 제공자로 종류를 최선껏 조회(실패하면 None — 단서만 생략)."""
        if self._search is None:
            return None
        try:
            matches = await self._search.search(symbol, 1)
        except Exception:  # noqa: BLE001 - 종류 미상은 None 으로 충분(가짜 ❌)
            return None
        return matches[0].type if matches else None


def _note(asset_type: str | None) -> str | None:
    if asset_type == "EQUITY":
        return "개별 종목은 분산된 ETF와 달리 회복이 보장되지 않습니다."
    return None
