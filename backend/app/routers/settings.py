"""설정 라우터 (로컬, 키 마스킹)."""

from __future__ import annotations

from fastapi import APIRouter

from ..config import SafeSettings, Settings, load_settings, save_settings, to_safe
from ..deps import reset_service_caches
from ..models import CamelModel

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingsUpdate(CamelModel):
    """부분 업데이트. 빈 문자열 키는 '변경 없음' 으로 취급."""

    watchlist: list[str] | None = None
    default_symbol: str | None = None
    api_keys: dict[str, str] | None = None
    ai: dict[str, object] | None = None
    ui: dict[str, object] | None = None
    plan: dict[str, object] | None = None
    dashboard: dict[str, object] | None = None


@router.get("")
async def get_settings() -> SafeSettings:
    return to_safe(load_settings())


@router.put("")
async def update_settings(update: SettingsUpdate) -> SafeSettings:
    current = load_settings()
    data = current.model_dump()

    if update.watchlist is not None:
        data["watchlist"] = update.watchlist
    if update.default_symbol is not None:
        data["default_symbol"] = update.default_symbol
    if update.api_keys is not None:
        # 빈 문자열은 변경 없음으로 간주(기존 키 유지)
        for k, v in update.api_keys.items():
            if v:
                data["api_keys"][k] = v
    if update.ai is not None:
        data["ai"].update(update.ai)
    if update.ui is not None:
        data["ui"].update(update.ui)
    if update.plan is not None:
        data["plan"].update(update.plan)
    if update.dashboard is not None:
        # 레이아웃은 전체 교체(부분 병합 아님 — 프론트가 완전한 배치를 보냄)
        data["dashboard"] = update.dashboard

    new_settings = Settings.model_validate(data)
    save_settings(new_settings)
    # 키를 캡처한 서비스 캐시를 비워 새 API 키가 즉시 반영되게 한다(재시작 불필요).
    reset_service_caches()
    return to_safe(new_settings)
