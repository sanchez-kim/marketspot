"""포트폴리오 리스크 서비스 — 집중도(HHI) + 종목 간 상관(분산 신호).

기존 포트폴리오 평가(비중)와 1년 일봉을 재사용한다. 이력이 모자란 종목은
상관 계산에서 정직하게 제외한다(가짜 ❌). 예측은 하지 않는다.
"""

from __future__ import annotations

from datetime import datetime

from ..analytics.risk import aligned_closes, herfindahl, pct_returns, pearson
from ..models import (
    Bar,
    CorrelationPair,
    DataStatus,
    HoldingWeight,
    PortfolioRisk,
)
from ..providers.registry import ProviderRegistry
from .portfolio import PortfolioService

_PERIOD = "1Y"
_INTERVAL = "1D"
_HAS_DATA = {DataStatus.LIVE, DataStatus.DELAYED, DataStatus.STALE}


class RiskService:
    def __init__(self, registry: ProviderRegistry, portfolio: PortfolioService) -> None:
        self._registry = registry
        self._portfolio = portfolio

    async def get_risk(self) -> PortfolioRisk:
        summary = await self._portfolio.get_summary()
        valued = [v for v in summary.positions if v.weight is not None]
        if not valued:
            return PortfolioRisk(
                status=DataStatus.NO_DATA,
                message="평가 가능한 보유 포지션이 없습니다",
            )

        weights = [
            HoldingWeight(symbol=v.symbol.upper(), weight=round(v.weight or 0.0, 2))
            for v in valued
        ]
        hhi = herfindahl([(v.weight or 0.0) / 100 for v in valued])
        top = max(valued, key=lambda v: v.weight or 0.0)

        # 1년 일봉을 모아 공통 거래일로 정렬 → 상관 계산
        series: dict[str, list[Bar]] = {}
        for v in valued:
            env = await self._registry.get_bars(v.symbol, _PERIOD, _INTERVAL)
            if env.data is not None and env.status in _HAS_DATA:
                series[v.symbol.upper()] = env.data
        symbols, matrix = aligned_closes(series)
        returns = [pct_returns(row) for row in matrix]

        pairs: list[CorrelationPair] = []
        corr_values: list[float] = []
        for i in range(len(symbols)):
            for j in range(i + 1, len(symbols)):
                c = pearson(returns[i], returns[j])
                if c is not None:
                    pairs.append(
                        CorrelationPair(a=symbols[i], b=symbols[j], corr=round(c, 2))
                    )
                    corr_values.append(c)

        avg = round(sum(corr_values) / len(corr_values), 2) if corr_values else None
        excluded = [v.symbol.upper() for v in valued if v.symbol.upper() not in symbols]
        lookback = len(matrix[0]) if matrix else None
        as_of: datetime | None = summary.as_of

        return PortfolioRisk(
            status=DataStatus.DELAYED,
            as_of=as_of,
            concentration_hhi=round(hhi, 4),
            top_symbol=top.symbol.upper(),
            top_weight=round(top.weight or 0.0, 2),
            weights=weights,
            correlations=pairs,
            avg_correlation=avg,
            lookback_days=lookback,
            excluded=excluded,
        )
