"""안심 홈 라우터 — 한 줄 평결."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from ..deps import get_home_service
from ..models import HomeVerdict
from ..services.home import HomeService

router = APIRouter(prefix="/api", tags=["home"])


@router.get("/home")
async def get_home(
    service: Annotated[HomeService, Depends(get_home_service)],
) -> HomeVerdict:
    return await service.get_verdict()
