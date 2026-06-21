"""매크로 스트립 라우터."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from ..deps import get_macro_service
from ..services.macro import MacroService, StripItem

router = APIRouter(prefix="/api/macro", tags=["macro"])


@router.get("/strip")
async def get_strip(
    service: Annotated[MacroService, Depends(get_macro_service)],
) -> list[StripItem]:
    return await service.get_strip()
