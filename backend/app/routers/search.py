"""심볼 검색 라우터 (자동완성)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from ..deps import get_search_provider
from ..models import SymbolMatch
from ..providers.search_provider import SearchProvider

router = APIRouter(prefix="/api", tags=["search"])


@router.get("/search")
async def search_symbols(
    provider: Annotated[SearchProvider, Depends(get_search_provider)],
    q: Annotated[str, Query()],
    limit: Annotated[int, Query(ge=1, le=20)] = 8,
) -> list[SymbolMatch]:
    return await provider.search(q, limit)
