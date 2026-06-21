"""스파크라인 종가 라우터."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from ..deps import get_spark_service
from ..services.spark import SparkService

router = APIRouter(prefix="/api", tags=["spark"])


@router.get("/spark")
async def get_spark(
    service: Annotated[SparkService, Depends(get_spark_service)],
    symbols: Annotated[str, Query()],
    period: Annotated[str, Query()] = "3M",
) -> dict[str, list[float]]:
    return await service.get(symbols.split(","), period)
