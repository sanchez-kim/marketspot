"""Provider 인터페이스 (DESIGN.md §3).

모든 제공자는 동일 인터페이스를 구현하므로 교체/추가가 쉽고, 반환 타입이
``DataEnvelope`` 라 상태 표기가 구조적으로 강제된다.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..models import Bar, DataEnvelope, Quote


@runtime_checkable
class QuoteProvider(Protocol):
    """시세/봉 데이터 제공자."""

    name: str

    async def get_quote(self, symbol: str) -> DataEnvelope[Quote]: ...

    async def get_bars(
        self, symbol: str, period: str, interval: str
    ) -> DataEnvelope[list[Bar]]: ...


def market_of(symbol: str) -> str:
    """심볼로부터 시장을 추정한다.

    한국 종목은 ``.KS`` / ``.KQ`` 접미사를 쓴다(예: ``005930.KS``).
    그 외는 미국으로 간주한다.
    """
    upper = symbol.upper()
    if upper.endswith((".KS", ".KQ")):
        return "KR"
    return "US"
