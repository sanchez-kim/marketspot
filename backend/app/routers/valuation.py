"""밸류 컨텍스트 라우터 — 근거 ①."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from ..deps import get_valuation_service
from ..models import ValuationContext
from ..services.valuation import ValuationService

router = APIRouter(prefix="/api", tags=["valuation"])


@router.get("/valuation/{symbol}")
async def get_valuation(
    symbol: str,
    service: Annotated[ValuationService, Depends(get_valuation_service)],
) -> ValuationContext:
    return await service.get(symbol)
