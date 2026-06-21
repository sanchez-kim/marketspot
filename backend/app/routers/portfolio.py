"""포트폴리오 라우터.

GET 은 저장된 포지션을 실시간 시세로 평가해 반환한다. PUT 은 포지션 목록을
통째로 교체(프론트가 전체 목록을 보냄 — 관심종목과 동일한 단순 모델)하고
저장 후 평가 결과를 반환한다.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from ..deps import get_portfolio_service
from ..models import PortfolioSummary, Position
from ..portfolio_store import save_positions
from ..services.portfolio import PortfolioService

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


@router.get("")
async def get_portfolio(
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
) -> PortfolioSummary:
    return await service.get_summary()


@router.put("")
async def replace_portfolio(
    positions: list[Position],
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
) -> PortfolioSummary:
    save_positions(positions)
    return await service.value(positions)
