"""안심 홈 평결 테스트 (네트워크 무).

손익 부호 → 톤, 하락 맥락 → 근거. 근거가 약하면 거짓 위로 대신 정직.
"""

from __future__ import annotations

import pytest

from app.config import PlanSettings
from app.models import (
    DataStatus,
    DrawdownContext,
    PortfolioSummary,
    PositionValuation,
)
from app.services.home import HomeService


class _Pf:
    def __init__(self, summary: PortfolioSummary) -> None:
        self._s = summary

    async def get_summary(self) -> PortfolioSummary:
        return self._s


class _Rx:
    def __init__(self, ctx: DrawdownContext) -> None:
        self._c = ctx

    async def get_context(self, symbol: str) -> DrawdownContext:
        return self._c


def _pos(symbol: str, mv: float | None = 100.0) -> PositionValuation:
    return PositionValuation(
        symbol=symbol,
        quantity=1,
        avg_cost=1,
        cost_basis=1,
        status=DataStatus.DELAYED,
        market_value=mv,
    )


def _summary(
    positions: list[PositionValuation], pnl: float | None, valued: int
) -> PortfolioSummary:
    return PortfolioSummary(
        positions=positions,
        total_value=1000.0,
        total_cost=900.0,
        total_pnl=100.0,
        total_pnl_pct=pnl,
        valued_count=valued,
        unvalued_count=len(positions) - valued,
    )


_SOLID = DrawdownContext(
    symbol="VOO",
    status=DataStatus.DELAYED,
    current_drawdown_pct=-8.0,
    history_years=10.0,
    comparable_count=14,
    recovered_count=14,
    median_recovery_days=49,
    limited_history=False,
)
_LIMITED = DrawdownContext(
    symbol="NEW",
    status=DataStatus.DELAYED,
    limited_history=True,
    comparable_count=0,
)
_NODATA = DrawdownContext(symbol="X", status=DataStatus.NO_DATA)


def _svc(summary: PortfolioSummary, ctx: DrawdownContext) -> HomeService:
    return HomeService(_Pf(summary), _Rx(ctx))


@pytest.mark.asyncio
async def test_no_holdings() -> None:
    v = await _svc(_summary([], None, 0), _SOLID).get_verdict()
    assert v.tone == "NO_HOLDINGS"
    assert v.todo == "—"


@pytest.mark.asyncio
async def test_profit_is_on_track() -> None:
    v = await _svc(_summary([_pos("VOO")], 12.3, 1), _SOLID).get_verdict()
    assert v.tone == "ON_TRACK"
    assert "없음" in v.todo
    assert v.total_pnl_pct == 12.3


@pytest.mark.asyncio
async def test_loss_with_solid_context_is_normal_dip() -> None:
    v = await _svc(_summary([_pos("VOO")], -6.5, 1), _SOLID).get_verdict()
    assert v.tone == "NORMAL_DIP"
    # 근거에 실제 기저율 수치가 들어간다
    assert "14번" in v.subline and "49일" in v.subline
    assert "없음" in v.todo


@pytest.mark.asyncio
async def test_loss_with_limited_context_is_unusual_not_fake_comfort() -> None:
    v = await _svc(_summary([_pos("NEW")], -30.0, 1), _LIMITED).get_verdict()
    assert v.tone == "UNUSUAL"
    assert "거짓 위로" in v.subline  # 가짜 안심 ❌


@pytest.mark.asyncio
async def test_plan_personalizes_verdict_on_dip() -> None:
    """투자원칙(하락에도 안 팔기)이 있으면 평결의 '할 일'이 내 약속으로 바뀐다."""
    svc = HomeService(
        _Pf(_summary([_pos("VOO")], -6.5, 1)),
        _Rx(_SOLID),
        plan_loader=lambda: PlanSettings(rules=["no_sell_on_dip"]),
    )
    v = await svc.get_verdict()
    assert v.tone == "NORMAL_DIP"
    assert "팔지 않" in v.todo  # 내 원칙이 평결에 반영됨


@pytest.mark.asyncio
async def test_all_quotes_failed_is_honest() -> None:
    v = await _svc(_summary([_pos("X", mv=None)], None, 0), _NODATA).get_verdict()
    assert v.tone == "UNUSUAL"
    assert "확인하기 어려" in v.headline
