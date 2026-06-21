"""헬스/진단 라우터: 각 데이터 소스·AI 가용성 점검."""

from __future__ import annotations

import importlib.util

from fastapi import APIRouter

from ..config import load_settings
from ..models import CamelModel

router = APIRouter(prefix="/api/health", tags=["health"])


class HealthReport(CamelModel):
    ok: bool
    yfinance_installed: bool
    ai_backend: str
    notes: list[str]


@router.get("")
async def health() -> HealthReport:
    notes: list[str] = []
    yf_ok = importlib.util.find_spec("yfinance") is not None
    if not yf_ok:
        notes.append("yfinance 미설치 — 시세/차트가 ERROR 로 표기됩니다")

    settings = load_settings()
    backend = settings.ai.backend
    if backend == "gemini" and not settings.api_keys.gemini:
        notes.append("AI 백엔드가 gemini 이지만 키가 없습니다 — 규칙기반으로 폴백")

    return HealthReport(
        ok=True,
        yfinance_installed=yf_ok,
        ai_backend=backend,
        notes=notes,
    )
