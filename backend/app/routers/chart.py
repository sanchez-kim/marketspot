"""차트 라우터."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from ..deps import get_chart_service
from ..models import ChartData, DataEnvelope
from ..services.chart import ChartService

router = APIRouter(prefix="/api/chart", tags=["chart"])

_PERIODS = {"1M", "3M", "6M", "1Y", "2Y", "5Y", "10Y"}
_INTERVALS = {"1D", "1W", "1M"}


@router.get("/{symbol}")
async def get_chart(
    symbol: str,
    service: Annotated[ChartService, Depends(get_chart_service)],
    period: Annotated[str, Query()] = "1Y",
    interval: Annotated[str, Query()] = "1D",
) -> DataEnvelope[ChartData]:
    period = period.upper()
    interval = interval.upper()
    if period not in _PERIODS:
        period = "1Y"
    if interval not in _INTERVALS:
        interval = "1D"
    return await service.get_chart(symbol, period, interval)
