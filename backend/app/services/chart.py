"""차트 서비스: 봉 조회 + 보조지표 계산 + 캐시.

★ 핵심 정확성(REQUIREMENTS FR-1, DESIGN §5): 캐시 키에 ``(symbol, period,
interval)`` 을 모두 포함한다. 따라서 기간/인터벌을 바꾸면 반드시 다른
데이터셋이 로드되어 차트가 실제로 바뀐다.
"""

from __future__ import annotations

from ..cache import TTLCache
from ..indicators import compute_indicators
from ..models import ChartData, DataEnvelope, DataStatus
from ..providers.registry import ProviderRegistry

# 인터벌별 캐시 TTL(초). 짧은 봉일수록 자주 갱신.
_TTL_BY_INTERVAL = {
    "1D": 60.0,
    "1W": 300.0,
    "1M": 3600.0,
}
_DEFAULT_TTL = 60.0


def chart_cache_key(symbol: str, period: str, interval: str) -> str:
    return f"{symbol.upper()}|{period.upper()}|{interval.upper()}"


class ChartService:
    def __init__(
        self,
        registry: ProviderRegistry,
        cache: TTLCache[DataEnvelope[ChartData]] | None = None,
    ) -> None:
        self._registry = registry
        self._cache: TTLCache[DataEnvelope[ChartData]] = cache or TTLCache()

    async def get_chart(
        self, symbol: str, period: str, interval: str
    ) -> DataEnvelope[ChartData]:
        key = chart_cache_key(symbol, period, interval)
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        bars_env = await self._registry.get_bars(symbol, period, interval)
        if bars_env.data is None:
            # 빈/에러 상태를 그대로 전파(가짜 데이터 금지). 캐시하지 않음.
            return DataEnvelope[ChartData].empty(
                source=bars_env.source,
                status=bars_env.status,
                message=bars_env.message,
            )

        closes = [b.close for b in bars_env.data]
        indicators = compute_indicators(closes)
        chart = ChartData(
            symbol=symbol.upper(),
            period=period.upper(),
            interval=interval.upper(),
            bars=bars_env.data,
            indicators=indicators,
        )
        env: DataEnvelope[ChartData] = DataEnvelope.ok(
            chart,
            source=bars_env.source,
            status=bars_env.status,
            as_of=bars_env.as_of,
            delay_minutes=bars_env.delay_minutes,
        )
        if env.status is not DataStatus.ERROR:
            ttl = _TTL_BY_INTERVAL.get(interval.upper(), _DEFAULT_TTL)
            self._cache.set(key, env, ttl)
        return env
