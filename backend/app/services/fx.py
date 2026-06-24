"""환율 서비스 — USD/KRW(yfinance KRW=X). 가짜 환율 금지(없으면 상태 전파)."""

from __future__ import annotations

from ..models import DataEnvelope, DataStatus
from .quotes import QuoteService

_FX_SYMBOL = "KRW=X"  # 1 USD 당 KRW
_HAS_PRICE = {DataStatus.LIVE, DataStatus.DELAYED, DataStatus.STALE}


class FxService:
    def __init__(self, quote_service: QuoteService) -> None:
        self._quotes = quote_service

    async def usd_krw(self) -> DataEnvelope[float]:
        quotes = await self._quotes.get_quotes([_FX_SYMBOL])
        env = quotes.get(_FX_SYMBOL)
        if env and env.data is not None and env.status in _HAS_PRICE:
            return DataEnvelope.ok(
                env.data.price, source=env.source, status=env.status, as_of=env.as_of
            )
        # DataEnvelope.empty() rejects LIVE/DELAYED (those imply data is present).
        # If the upstream envelope carries a price-bearing status but data=None,
        # coerce to ERROR — the data is missing, so a price status is wrong anyway.
        raw_status = env.status if env else DataStatus.NO_DATA
        safe_status = (
            DataStatus.ERROR
            if raw_status in (DataStatus.LIVE, DataStatus.DELAYED)
            else raw_status
        )
        return DataEnvelope[float].empty(
            source=env.source if env else "yfinance",
            status=safe_status,
            message="환율(USD/KRW)을 가져오지 못했습니다",
        )
