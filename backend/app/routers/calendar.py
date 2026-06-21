"""다가오는 일정 라우터."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from ..deps import get_calendar_provider
from ..models import CalendarEvent
from ..providers.calendar_provider import YFinanceCalendarProvider

router = APIRouter(prefix="/api", tags=["calendar"])


@router.get("/calendar")
async def get_calendar(
    provider: Annotated[YFinanceCalendarProvider, Depends(get_calendar_provider)],
    symbols: Annotated[str, Query()],
    limit: Annotated[int, Query(ge=1, le=20)] = 6,
) -> list[CalendarEvent]:
    return await provider.get_events(symbols.split(","), limit)
