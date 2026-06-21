"""공시 서비스.

시장(US/KR)에 따라 제공자를 고른다 — 미국은 SEC EDGAR(키 불필요), 한국은
DART(키 필요). ``market_of`` 규칙을 시세/차트와 공유한다.
"""

from __future__ import annotations

from ..models import DataEnvelope, DataStatus, FilingList
from ..providers.base import market_of
from ..providers.filings_provider import FilingsProvider


class FilingsService:
    def __init__(self, providers: dict[str, FilingsProvider]) -> None:
        self._providers = providers

    async def get_filings(
        self, symbol: str, limit: int = 20
    ) -> DataEnvelope[FilingList]:
        provider = self._providers.get(market_of(symbol))
        if provider is None:
            return DataEnvelope[FilingList].empty(
                source="filings",
                status=DataStatus.NO_DATA,
                message=f"'{symbol}' 시장의 공시 제공자가 없습니다",
            )
        return await provider.get_filings(symbol, limit)
