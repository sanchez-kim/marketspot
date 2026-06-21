"""안심 레이어 라우터 — 하락 맥락화."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from ..deps import get_reassurance_service
from ..models import DrawdownContext
from ..services.reassurance import ReassuranceService

router = APIRouter(prefix="/api", tags=["context"])


@router.get("/context")
async def get_contexts(
    service: Annotated[ReassuranceService, Depends(get_reassurance_service)],
    symbols: Annotated[str, Query()],
) -> list[DrawdownContext]:
    """쉼표 구분 심볼들의 하락 맥락(홈 대시보드 일괄 조회)."""
    return await service.get_contexts(symbols.split(","))


@router.get("/context/{symbol}")
async def get_context(
    symbol: str,
    service: Annotated[ReassuranceService, Depends(get_reassurance_service)],
) -> DrawdownContext:
    return await service.get_context(symbol)
