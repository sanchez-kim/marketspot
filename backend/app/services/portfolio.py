"""포트폴리오 평가 서비스.

사용자 **거래내역(매수/매도)** 에서 보유를 도출(이동평균법)하고, **실시간 시세**를
곱해 평가액/미실현·실현손익/비중을 계산한다. 시세가 없는 포지션은 평가액을
만들지 않고(가짜 금지) 상태만 표기하며 합계에서 제외한다. 통화별 합계는
``FxService`` 의 환율로 KRW/USD 양 통화로 환산하되, 환율이 없으면 환산이 필요한
쪽을 null 로 둔다(정직성).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from ..analytics.holdings import combine_currency_totals, derive_holdings
from ..models import (
    DataStatus,
    PortfolioSummary,
    PositionValuation,
    Transaction,
)
from ..transaction_store import load_transactions
from .fx import FxService
from .quotes import QuoteService

# 실제 가격이 존재하는 시세 상태
_HAS_PRICE = {DataStatus.LIVE, DataStatus.DELAYED, DataStatus.STALE}


class PortfolioService:
    def __init__(
        self,
        quote_service: QuoteService,
        fx_service: FxService,
        txns_loader: Callable[[], list[Transaction]] = load_transactions,
    ) -> None:
        self._quotes = quote_service
        self._fx = fx_service
        self._load = txns_loader

    async def get_summary(self) -> PortfolioSummary:
        holdings = derive_holdings(self._load())
        quotes = await self._quotes.get_quotes([h.symbol for h in holdings])
        fx = await self._fx.usd_krw()

        valuations: list[PositionValuation] = []
        mv_by_ccy: dict[str, float] = {}
        unreal_by_ccy: dict[str, float] = {}
        real_by_ccy: dict[str, float] = {}
        total_value = 0.0
        total_cost = 0.0
        total_realized = 0.0
        valued = 0
        as_of: datetime | None = None

        for h in holdings:
            env = quotes.get(h.symbol.strip())
            cost_basis = h.quantity * h.avg_cost
            v = PositionValuation(
                symbol=h.symbol,
                quantity=h.quantity,
                avg_cost=h.avg_cost,
                cost_basis=cost_basis,
                currency=h.currency,
                realized_pnl=h.realized_pnl,
                status=env.status if env else DataStatus.NO_DATA,
            )
            total_realized += h.realized_pnl
            real_by_ccy[h.currency] = real_by_ccy.get(h.currency, 0.0) + h.realized_pnl
            if env and env.data is not None and env.status in _HAS_PRICE:
                price = env.data.price
                market_value = h.quantity * price
                pnl = market_value - cost_basis
                v.name = env.data.name
                v.price = price
                v.market_value = market_value
                v.unrealized_pnl = pnl
                v.unrealized_pnl_pct = pnl / cost_basis * 100 if cost_basis else None
                total_value += market_value
                total_cost += cost_basis
                valued += 1
                mv_by_ccy[h.currency] = mv_by_ccy.get(h.currency, 0.0) + market_value
                unreal_by_ccy[h.currency] = unreal_by_ccy.get(h.currency, 0.0) + pnl
                if env.as_of is not None and (as_of is None or env.as_of > as_of):
                    as_of = env.as_of
            valuations.append(v)

        # 2차 패스: 비중(평가액 기준)
        if total_value > 0:
            for v in valuations:
                if v.market_value is not None:
                    v.weight = v.market_value / total_value * 100

        rate = fx.data
        value = combine_currency_totals(mv_by_ccy, fx_rate=rate)
        unreal = combine_currency_totals(unreal_by_ccy, fx_rate=rate)
        real = combine_currency_totals(real_by_ccy, fx_rate=rate)
        total_pnl = total_value - total_cost
        return PortfolioSummary(
            positions=valuations,
            total_value=total_value,
            total_cost=total_cost,
            total_pnl=total_pnl,
            total_pnl_pct=(total_pnl / total_cost * 100 if total_cost else None),
            total_realized=total_realized,
            valued_count=valued,
            unvalued_count=len(holdings) - valued,
            as_of=as_of,
            value_krw=value.krw,
            value_usd=value.usd,
            unrealized_krw=unreal.krw,
            unrealized_usd=unreal.usd,
            realized_krw=real.krw,
            realized_usd=real.usd,
            fx_rate=rate,
            fx_status=fx.status,
        )
