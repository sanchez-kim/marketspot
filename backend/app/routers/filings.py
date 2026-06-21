"""공시 라우터."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from ..deps import get_filings_service
from ..models import DataEnvelope, FilingList
from ..services.filings import FilingsService

router = APIRouter(prefix="/api", tags=["filings"])


@router.get("/filings")
async def get_filings(
    service: Annotated[FilingsService, Depends(get_filings_service)],
    symbol: Annotated[str, Query()],
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> DataEnvelope[FilingList]:
    return await service.get_filings(symbol, limit)
