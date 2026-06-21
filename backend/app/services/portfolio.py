"""포트폴리오 평가 서비스.

사용자가 입력한 포지션(원금)에 **실시간 시세**를 곱해 평가액/손익/비중을
계산한다. 시세가 없는 포지션은 평가액을 만들지 않고(가짜 금지) 상태만 표기하며
합계에서 제외한다.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from ..models import (
    DataStatus,
    PortfolioSummary,
    Position,
    PositionValuation,
)
from ..portfolio_store import load_positions
from .quotes import QuoteService

# 실제 가격이 존재하는 시세 상태
_HAS_PRICE = {DataStatus.LIVE, DataStatus.DELAYED, DataStatus.STALE}


class PortfolioService:
    def __init__(
        self,
        quote_service: QuoteService,
        positions_loader: Callable[[], list[Position]] = load_positions,
    ) -> None:
        self._quotes = quote_service
        self._load = positions_loader

    async def get_summary(self) -> PortfolioSummary:
        return await self.value(self._load())

    async def value(self, positions: list[Position]) -> PortfolioSummary:
        quotes = await self._quotes.get_quotes([p.symbol for p in positions])

        valuations: list[PositionValuation] = []
        total_value = 0.0
        total_cost = 0.0
        valued = 0
        as_of: datetime | None = None

        for p in positions:
            env = quotes.get(p.symbol.strip())
            cost_basis = p.quantity * p.avg_cost
            v = PositionValuation(
                symbol=p.symbol,
                quantity=p.quantity,
                avg_cost=p.avg_cost,
                cost_basis=cost_basis,
                status=env.status if env else DataStatus.NO_DATA,
            )
            if env and env.data is not None and env.status in _HAS_PRICE:
                price = env.data.price
                market_value = p.quantity * price
                pnl = market_value - cost_basis
                v.name = env.data.name
                v.currency = env.data.currency
                v.price = price
                v.market_value = market_value
                v.unrealized_pnl = pnl
                v.unrealized_pnl_pct = pnl / cost_basis * 100 if cost_basis else None
                total_value += market_value
                total_cost += cost_basis
                valued += 1
                if env.as_of is not None and (as_of is None or env.as_of > as_of):
                    as_of = env.as_of
            valuations.append(v)

        # 2차 패스: 비중(평가액 기준)
        if total_value > 0:
            for v in valuations:
                if v.market_value is not None:
                    v.weight = v.market_value / total_value * 100

        total_pnl = total_value - total_cost
        return PortfolioSummary(
            positions=valuations,
            total_value=total_value,
            total_cost=total_cost,
            total_pnl=total_pnl,
            total_pnl_pct=(total_pnl / total_cost * 100 if total_cost else None),
            valued_count=valued,
            unvalued_count=len(positions) - valued,
            as_of=as_of,
        )
