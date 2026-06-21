"""매크로 지수 스트립 (DESIGN.md §4 /macro/strip).

ETF 적립식 투자자의 '타이밍 맥락'에 필요한 핵심 지표를 한 줄로 제공한다:
주요 지수 + 환율 + 미 10년물 금리.
"""

from __future__ import annotations

import asyncio

from ..models import CamelModel, DataEnvelope, Quote
from ..providers.registry import ProviderRegistry

# (라벨, yfinance 심볼)
_STRIP = [
    ("S&P 500", "^GSPC"),
    ("나스닥", "^IXIC"),
    ("KOSPI", "^KS11"),
    ("USD/KRW", "KRW=X"),
    ("미 10Y", "^TNX"),
]


class StripItem(CamelModel):
    label: str
    symbol: str
    quote: DataEnvelope[Quote]


class MacroService:
    def __init__(self, registry: ProviderRegistry) -> None:
        self._registry = registry

    async def get_strip(self) -> list[StripItem]:
        quotes = await asyncio.gather(
            *(self._registry.get_quote(sym) for _, sym in _STRIP)
        )
        return [
            StripItem(label=label, symbol=sym, quote=q)
            for (label, sym), q in zip(_STRIP, quotes, strict=True)
        ]
