"""리스크 서비스 테스트 — 실제 분석 로직 실행, 시세 이력만 fake."""

from __future__ import annotations

from datetime import UTC, datetime

from app.models import Bar, DataEnvelope, DataStatus, Position
from app.providers.registry import ProviderRegistry
from app.services.portfolio import PortfolioService
from app.services.risk import RiskService


class _BarsProvider:
    """심볼별로 미리 정한 종가열을 봉으로 돌려주는 fake(시세는 종가=가격)."""

    name = "fake-bars"

    def __init__(self, series: dict[str, list[float]]) -> None:
        self._series = series

    async def get_quote(self, symbol: str) -> DataEnvelope:  # type: ignore[type-arg]
        from app.models import Quote

        closes = self._series.get(symbol.upper())
        if not closes:
            return DataEnvelope[Quote].empty(
                source=self.name, status=DataStatus.NO_DATA
            )
        return DataEnvelope.ok(
            Quote(symbol=symbol, price=closes[-1]),
            source=self.name,
            status=DataStatus.DELAYED,
        )

    async def get_bars(
        self, symbol: str, period: str, interval: str
    ) -> DataEnvelope[list[Bar]]:
        closes = self._series.get(symbol.upper())
        if not closes:
            return DataEnvelope[list[Bar]].empty(
                source=self.name, status=DataStatus.NO_DATA
            )
        bars = [
            Bar(
                time=datetime(2026, 1, 1 + i, tzinfo=UTC),
                open=c,
                high=c,
                low=c,
                close=c,
                volume=1.0,
            )
            for i, c in enumerate(closes)
        ]
        return DataEnvelope.ok(
            bars, source=self.name, status=DataStatus.DELAYED, as_of=bars[-1].time
        )


def _service(series: dict[str, list[float]]) -> RiskService:
    prov = _BarsProvider(series)
    registry = ProviderRegistry({"US": [prov], "KR": [prov]})
    positions = [Position(symbol=s, quantity=1.0, avg_cost=1.0) for s in series]
    portfolio = PortfolioService(_QuoteSvc(registry), lambda: positions)  # type: ignore[arg-type]  # duck-typed fake for tests
    return RiskService(registry, portfolio)


class _QuoteSvc:
    """PortfolioService 가 기대하는 get_quotes 를 registry 로 위임."""

    def __init__(self, registry: ProviderRegistry) -> None:
        self._registry = registry

    async def get_quotes(self, symbols: list[str]) -> dict:  # type: ignore[type-arg]
        out = {}
        for s in symbols:
            out[s.strip()] = await self._registry.get_quote(s)
        return out


async def test_risk_reports_concentration_and_correlation() -> None:
    # AAA, BBB 완전 동조(같은 수익률) → 상관 1.0, 균등비중 → HHI 0.5
    svc = _service(
        {
            "AAA": [100.0, 110.0, 121.0, 133.1],
            "BBB": [100.0, 110.0, 121.0, 133.1],
        }
    )
    risk = await svc.get_risk()
    assert risk.status == DataStatus.DELAYED
    assert risk.concentration_hhi == 0.5
    assert risk.top_weight == 50.0
    assert risk.avg_correlation == 1.0
    assert len(risk.correlations) == 1
    assert risk.excluded == []


async def test_risk_empty_portfolio_is_no_data() -> None:
    svc = _service({})
    risk = await svc.get_risk()
    assert risk.status == DataStatus.NO_DATA
    assert risk.message is not None
