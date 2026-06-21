"""시세 라우터."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from ..deps import get_quote_service
from ..models import DataEnvelope, Quote
from ..services.quotes import QuoteService

router = APIRouter(prefix="/api/quotes", tags=["quotes"])


@router.get("")
async def get_quotes(
    symbols: Annotated[str, Query(description="쉼표로 구분한 심볼들")],
    service: Annotated[QuoteService, Depends(get_quote_service)],
) -> dict[str, DataEnvelope[Quote]]:
    symbol_list = symbols.split(",")
    return await service.get_quotes(symbol_list)
