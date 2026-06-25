"""로컬 설정 저장 (DESIGN.md §8).

로그인 없음 — 단일 프로필을 ``settings.json`` 으로 보관한다. API 키는 로컬
파일에만 저장되며, 응답에서는 마스킹한다(평문 노출 금지).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from pydantic import Field

from .models import CamelModel


def data_dir() -> Path:
    path = Path(os.environ.get("STOCK_TERMINAL_DATA_DIR", "./data"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def _settings_path() -> Path:
    return data_dir() / "settings.json"


class ApiKeys(CamelModel):
    alpaca: str = ""
    finnhub: str = ""
    dart: str = ""
    fred: str = ""
    kis: str = ""
    gemini: str = ""


class AISettings(CamelModel):
    backend: str = "ollama"  # ollama | gemini | rule
    # ★ Ollama 0.30+ 가 MLX(애플 실리콘) 모델을 지원한다. qwen3.5:9b-mlx 는
    #   think:false 를 존중(사고 토큰 0)하면서 애플 실리콘에서 빠르게 동작한다.
    #   (구버전 Ollama 에선 비전 모델 qwen3-vl 이 think 를 못 꺼 느렸음.)
    model: str = "qwen3.5:9b-mlx"
    beginner_mode: bool = True  # 초보자 설명 톤 (user-investor-profile)


class UISettings(CamelModel):
    theme: str = "dark"
    density: str = "comfortable"  # comfortable | normal | compact
    up_color: str = "green"  # green(미국식) | red(한국식)
    default_period: str = "1Y"  # 적립식 투자자 관점 중장기 기본
    base_currency: str = "USD"  # 포트폴리오 합계 표시 통화 (USD | KRW)
    onboarded: bool = False  # 첫 방문 투어 완료 여부


class DashboardLayout(CamelModel):
    """홈 카드 배치(사용자 커스터마이징). 카드 id 의 좌/우 열 순서 + 숨김."""

    left: list[str] = Field(default_factory=lambda: ["plan", "portfolio", "watchlist"])
    right: list[str] = Field(
        default_factory=lambda: ["mood", "news", "events", "learn"]
    )
    hidden: list[str] = Field(default_factory=list)


class PlanSettings(CamelModel):
    """투자원칙 — 사용자가 한 번 선언하면 안심 평결이 *이 계획 기준*으로 말한다.

    rules 는 사전 정의된 원칙 키 목록(예: "no_sell_on_dip"). DESIGN §0 의
    Meadows '규칙' 레버리지 — 흔들릴 때 자기 약속을 되비춘다.
    """

    style: str = "dca"  # dca(적립식) | lump(거치식)
    monthly_contribution: float = 0.0  # 월 적립액(0=미설정)
    rules: list[str] = Field(default_factory=list)  # 선택한 원칙 키들
    horizon_years: int = 0  # 투자 기간(0=미설정)
    note: str = ""  # 자유 메모


class Settings(CamelModel):
    # 초보 ETF 투자자 기본값 (user-investor-profile)
    watchlist: list[str] = Field(
        default_factory=lambda: ["VOO", "QQQM", "AAPL", "NVDA"]
    )
    default_symbol: str = "VOO"
    api_keys: ApiKeys = Field(default_factory=ApiKeys)
    ai: AISettings = Field(default_factory=AISettings)
    ui: UISettings = Field(default_factory=UISettings)
    plan: PlanSettings = Field(default_factory=PlanSettings)
    dashboard: DashboardLayout = Field(default_factory=DashboardLayout)


class SafeApiKeys(CamelModel):
    """키 값 대신 '설정 여부' 만 노출."""

    alpaca: bool = False
    finnhub: bool = False
    dart: bool = False
    fred: bool = False
    kis: bool = False
    gemini: bool = False


class SafeSettings(CamelModel):
    """클라이언트로 내보내는 안전한 설정(키 마스킹)."""

    watchlist: list[str]
    default_symbol: str
    api_keys: SafeApiKeys
    ai: AISettings
    ui: UISettings
    plan: PlanSettings
    dashboard: DashboardLayout


def load_settings() -> Settings:
    path = _settings_path()
    if not path.exists():
        settings = Settings()
        save_settings(settings)
        return settings
    raw = json.loads(path.read_text(encoding="utf-8"))
    return Settings.model_validate(raw)


def save_settings(settings: Settings) -> None:
    path = _settings_path()
    path.write_text(
        json.dumps(settings.model_dump(by_alias=True), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def to_safe(settings: Settings) -> SafeSettings:
    keys = settings.api_keys
    return SafeSettings(
        watchlist=settings.watchlist,
        default_symbol=settings.default_symbol,
        api_keys=SafeApiKeys(
            alpaca=bool(keys.alpaca),
            finnhub=bool(keys.finnhub),
            dart=bool(keys.dart),
            fred=bool(keys.fred),
            kis=bool(keys.kis),
            gemini=bool(keys.gemini),
        ),
        ai=settings.ai,
        ui=settings.ui,
        plan=settings.plan,
        dashboard=settings.dashboard,
    )
