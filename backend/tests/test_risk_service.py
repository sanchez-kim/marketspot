"""리스크 서비스 테스트 — 실제 분석 로직 실행, 시세 이력만 fake."""

from __future__ import annotations

from datetime import UTC, datetime

from app.models import Bar, DataEnvelope, DataStatus, Position
from app.providers.registry import ProviderRegistry
from app.services.portfolio import PortfolioService
from app.services.risk import RiskService


class _BarsProvider:
    """심볼별로 미리 정한 종가열을 봉으로 돌려주는 fake(시세는 종가=가격).

    no_bars: 이 집합에 속한 심볼은 quote(가격)는 있지만 bar 이력이 없는 것으로 취급.
    """

    name = "fake-bars"

    def __init__(
        self,
        series: dict[str, list[float]],
        no_bars: set[str] | None = None,
    ) -> None:
        self._series = series
        self._no_bars: set[str] = {s.upper() for s in (no_bars or set())}

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
        upper = symbol.upper()
        closes = self._series.get(upper)
        if not closes or upper in self._no_bars:
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


def _service(
    series: dict[str, list[float]],
    no_bars: set[str] | None = None,
) -> RiskService:
    prov = _BarsProvider(series, no_bars=no_bars)
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


async def test_risk_partial_exclusion_bar_less_symbol() -> None:
    # CCC has a price (quote) but NO bar history → must appear in excluded.
    # DDD has full bar history → contributes to the return series.
    # With only one symbol having returns, correlations must be empty.
    svc = _service(
        {"CCC": [50.0, 55.0, 60.0], "DDD": [100.0, 110.0, 121.0]},
        no_bars={"CCC"},
    )
    risk = await svc.get_risk()
    assert risk.status == DataStatus.DELAYED
    assert "CCC" in risk.excluded
    assert "DDD" not in risk.excluded
    assert risk.correlations == []


async def test_risk_excludes_position_with_no_quote() -> None:
    # GGG has no quote at all (unvalued — no price) so it never enters the
    # weighted analysis. The PortfolioRisk.excluded contract ("시세/이력 없어
    # 상관 계산 제외") requires it to be disclosed, not silently dropped.
    prov = _BarsProvider({"FFF": [100.0, 110.0, 121.0]})
    registry = ProviderRegistry({"US": [prov], "KR": [prov]})
    positions = [
        Position(symbol="FFF", quantity=1.0, avg_cost=1.0),
        Position(symbol="GGG", quantity=1.0, avg_cost=1.0),
    ]
    portfolio = PortfolioService(_QuoteSvc(registry), lambda: positions)  # type: ignore[arg-type]
    risk = await RiskService(registry, portfolio).get_risk()
    assert "GGG" in risk.excluded
    assert "FFF" not in risk.excluded
