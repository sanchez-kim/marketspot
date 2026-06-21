"""안심 홈 서비스 — 한 줄 평결.

포트폴리오 손익(톤) + 최대 비중 종목의 하락 맥락(근거)을 묶어 "계획대로 가고
있나? 뭔가 해야 하나?"에 답한다. 기본 답은 거의 항상 *"할 일 없음 — 계속"*.
예측·매수매도 권유 금지. 근거 데이터가 없으면 거짓 위로 대신 정직하게 말한다.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from ..config import PlanSettings
from ..models import (
    DataStatus,
    DrawdownContext,
    HomeVerdict,
    PortfolioSummary,
)

_HAS_DATA = {DataStatus.LIVE, DataStatus.DELAYED, DataStatus.STALE}
_TODO_NONE = "지금 할 일: 없음 — 계획대로 계속"


class _PortfolioSource(Protocol):
    async def get_summary(self) -> PortfolioSummary: ...


class _ContextSource(Protocol):
    async def get_context(self, symbol: str) -> DrawdownContext: ...


# 사전 정의된 투자원칙 키(프론트와 공유) → 한국어 라벨
RULE_LABELS = {
    "buy_monthly": "매달 적립",
    "no_sell_on_dip": "하락에도 팔지 않기",
    "ignore_timing": "타이밍 안 보기",
    "long_term": "장기 보유",
}


class HomeService:
    def __init__(
        self,
        portfolio: _PortfolioSource,
        reassurance: _ContextSource,
        plan_loader: Callable[[], PlanSettings] = PlanSettings,
    ) -> None:
        self._portfolio = portfolio
        self._reassurance = reassurance
        self._plan_loader = plan_loader

    async def get_verdict(self) -> HomeVerdict:
        pf = await self._portfolio.get_summary()

        if not pf.positions:
            return HomeVerdict(
                tone="NO_HOLDINGS",
                headline="아직 보유 종목이 없어요",
                subline=(
                    "포트폴리오에 보유 종목(수량·평단)을 입력하면 손익·안심 평가가 "
                    "시작돼요. 관심종목은 아래에서 지켜보세요."
                ),
                todo="—",
            )

        raw = await self._reassurance.get_context(_largest(pf))
        ctx: DrawdownContext | None = raw if raw.status in _HAS_DATA else None

        if pf.valued_count == 0:  # 보유는 있으나 시세 전부 실패
            return HomeVerdict(
                tone="UNUSUAL",
                headline="지금은 시세를 확인하기 어려워요",
                subline="데이터를 못 불러왔어요. 거짓 평가 대신 솔직히 알려드릴게요.",
                todo="—",
                total_value=pf.total_value,
                context=ctx,
                as_of=pf.as_of,
            )

        pnl = pf.total_pnl_pct
        down = pnl is not None and pnl < 0

        if not down:
            verdict = _on_track(pnl, ctx)
        elif ctx is not None and _solid(ctx):
            verdict = _normal_dip(pnl, ctx)
        else:
            verdict = _unusual(pnl, ctx)

        _personalize(verdict, self._plan_loader(), down)
        verdict.total_value = pf.total_value
        verdict.total_pnl_pct = pnl
        verdict.context = ctx
        verdict.as_of = pf.as_of
        return verdict


def _personalize(v: HomeVerdict, plan: PlanSettings, down: bool) -> None:
    """투자원칙이 있으면 평결을 *내 약속* 기준으로 바꿔준다(Meadows 규칙 레버리지)."""
    rules = plan.rules
    if not rules:
        return
    if down and "no_sell_on_dip" in rules:
        v.todo = "당신의 원칙: 하락에도 팔지 않기 — 지금이 그 약속을 지킬 때예요."
    elif "buy_monthly" in rules:
        v.todo = "당신의 원칙: 매달 적립 — 계획대로 이어가세요."
    if down and "buy_monthly" in rules:
        v.subline += " 다음 적립 땐 더 싸게 담는 셈이에요."


def _largest(pf: PortfolioSummary) -> str:
    valued = [p for p in pf.positions if p.market_value is not None]
    if valued:
        return max(valued, key=lambda p: p.market_value or 0).symbol
    return pf.positions[0].symbol


def _solid(ctx: DrawdownContext | None) -> bool:
    """기저율로 안심시킬 만큼 근거가 탄탄한가."""
    return bool(
        ctx
        and not ctx.limited_history
        and ctx.comparable_count > 0
        and ctx.recovered_count > 0
    )


def _pct(v: float | None) -> str:
    return "—" if v is None else f"{v:+.1f}%"


def _on_track(pnl: float | None, ctx: DrawdownContext | None) -> HomeVerdict:
    sub = "계획대로 적립을 이어가세요."
    if ctx and ctx.current_drawdown_pct is not None:
        sub = (
            f"{ctx.symbol}는 현재 고점 대비 "
            f"{ctx.current_drawdown_pct:.1f}% — 안정 구간이에요."
        )
    return HomeVerdict(
        tone="ON_TRACK",
        headline=f"잘 가고 있어요 — 평가손익 {_pct(pnl)}",
        subline=sub,
        todo=_TODO_NONE,
    )


def _normal_dip(pnl: float | None, ctx: DrawdownContext) -> HomeVerdict:
    days = ctx.median_recovery_days
    recover = (
        f"보통 {days}일 안에 회복했어요" if days is not None else "모두 회복했어요"
    )
    sub = (
        f"{ctx.symbol}는 지난 {ctx.history_years:.0f}년간 이런 조정을 "
        f"{ctx.comparable_count}번 겪고 {ctx.recovered_count}번 회복했어요({recover}). "
        "적립 투자자에겐 더 싸게 사는 날입니다."
    )
    return HomeVerdict(
        tone="NORMAL_DIP",
        headline=f"지금은 마이너스({_pct(pnl)})지만, 흔한 일이에요",
        subline=sub,
        todo=_TODO_NONE,
    )


def _unusual(pnl: float | None, ctx: DrawdownContext | None) -> HomeVerdict:
    sub = "거짓 위로는 안 할게요 — 다만 분산·적립 계획은 이런 때를 견디도록 설계됐어요."
    if ctx and ctx.note:
        sub = f"{sub} {ctx.note}"
    elif ctx and ctx.limited_history:
        sub = f"{sub} (이력이 짧아 과거 비교는 참고만 하세요.)"
    return HomeVerdict(
        tone="UNUSUAL",
        headline=f"지금은 마이너스({_pct(pnl)})이고, 평소보다 신중할 구간이에요",
        subline=sub,
        todo="지금 할 일: 보통 없음 — 계획을 다시 확인하세요",
    )
