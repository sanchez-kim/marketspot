"""종목 기본정보 라우터."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from ..deps import get_fundamentals_provider
from ..models import Fundamentals
from ..providers.fundamentals_provider import YFinanceFundamentalsProvider

router = APIRouter(prefix="/api", tags=["fundamentals"])


@router.get("/fundamentals/{symbol}")
async def get_fundamentals(
    symbol: str,
    provider: Annotated[
        YFinanceFundamentalsProvider, Depends(get_fundamentals_provider)
    ],
) -> Fundamentals:
    return await provider.get(symbol)
