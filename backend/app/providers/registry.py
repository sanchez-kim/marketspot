"""Provider 라우팅 + 폴백 체인 (DESIGN.md §3).

시장(US/KR)에 따라 제공자 체인을 고르고, 앞에서부터 시도해 **실제로 데이터가
있는** 첫 응답을 반환한다. 모두 실패하면 사용자가 행동할 수 있는(NEEDS_KEY 등)
상태를 우선해 정직하게 보고한다.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TypeVar

from ..models import Bar, DataEnvelope, DataStatus, Quote
from .base import QuoteProvider, market_of

T = TypeVar("T")

# 데이터가 실제로 존재하는 상태들
_HAS_DATA = {DataStatus.LIVE, DataStatus.DELAYED, DataStatus.STALE}

# 모두 실패했을 때 사용자에게 보여줄 상태의 우선순위(앞일수록 우선)
_FALLBACK_PRIORITY = [
    DataStatus.NEEDS_KEY,
    DataStatus.RATE_LIMITED,
    DataStatus.ERROR,
    DataStatus.NO_DATA,
]


class ProviderRegistry:
    def __init__(self, chains: dict[str, list[QuoteProvider]]) -> None:
        self._chains = chains

    def chain_for(self, symbol: str) -> list[QuoteProvider]:
        return self._chains.get(market_of(symbol), [])

    async def get_quote(self, symbol: str) -> DataEnvelope[Quote]:
        return await self._run(symbol, lambda p: p.get_quote(symbol))

    async def get_bars(
        self, symbol: str, period: str, interval: str
    ) -> DataEnvelope[list[Bar]]:
        return await self._run(symbol, lambda p: p.get_bars(symbol, period, interval))

    async def _run(
        self,
        symbol: str,
        call: Callable[[QuoteProvider], Awaitable[DataEnvelope[T]]],
    ) -> DataEnvelope[T]:
        chain = self.chain_for(symbol)
        if not chain:
            return DataEnvelope[T].empty(
                source="registry",
                status=DataStatus.NO_DATA,
                message=f"'{symbol}' 시장에 대한 데이터 제공자가 없습니다",
            )

        failures: list[DataEnvelope[T]] = []
        for provider in chain:
            try:
                env = await call(provider)
            except Exception as exc:  # noqa: BLE001 - 어떤 제공자 오류도 상태로 변환
                failures.append(
                    DataEnvelope[T].empty(
                        source=provider.name,
                        status=DataStatus.ERROR,
                        message=f"{provider.name} 조회 실패: {exc}",
                    )
                )
                continue
            if env.status in _HAS_DATA and env.data is not None:
                return env
            failures.append(env)

        return self._pick_failure(failures)

    @staticmethod
    def _pick_failure(failures: list[DataEnvelope[T]]) -> DataEnvelope[T]:
        if not failures:
            return DataEnvelope[T].empty(source="registry", status=DataStatus.NO_DATA)
        for status in _FALLBACK_PRIORITY:
            for env in failures:
                if env.status is status:
                    return env
        return failures[-1]
