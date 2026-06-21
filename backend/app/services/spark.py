"""스파크라인용 종가 배치.

관심종목별 짧은 기간 종가만 가볍게 모아 미니 차트에 쓴다. 기존 봉 경로를
재사용하고 종가만 추려 보낸다.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable

from ..cache import TTLCache
from ..providers.registry import ProviderRegistry

_TTL = 300.0  # 5분


class SparkService:
    def __init__(
        self, registry: ProviderRegistry, *, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self._registry = registry
        self._cache: TTLCache[list[float]] = TTLCache(clock=clock)

    async def get(
        self, symbols: list[str], period: str = "3M"
    ) -> dict[str, list[float]]:
        uniq = list(dict.fromkeys(s.strip() for s in symbols if s.strip()))
        pairs = await asyncio.gather(*(self._one(s, period) for s in uniq))
        return dict(pairs)

    async def _one(self, symbol: str, period: str) -> tuple[str, list[float]]:
        key = f"{symbol.upper()}|{period}"
        cached = self._cache.get(key)
        if cached is not None:
            return symbol.upper(), cached
        env = await self._registry.get_bars(symbol, period, "1D")
        closes = [b.close for b in env.data] if env.data else []
        if closes:
            self._cache.set(key, closes, _TTL)
        return symbol.upper(), closes
