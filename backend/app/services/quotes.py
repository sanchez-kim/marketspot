"""시세 서비스: 여러 심볼을 병렬 조회."""

from __future__ import annotations

import asyncio

from ..models import DataEnvelope, Quote
from ..providers.registry import ProviderRegistry


class QuoteService:
    def __init__(self, registry: ProviderRegistry) -> None:
        self._registry = registry

    async def get_quotes(self, symbols: list[str]) -> dict[str, DataEnvelope[Quote]]:
        unique = list(dict.fromkeys(s.strip() for s in symbols if s.strip()))
        results = await asyncio.gather(*(self._registry.get_quote(s) for s in unique))
        return dict(zip(unique, results, strict=True))
