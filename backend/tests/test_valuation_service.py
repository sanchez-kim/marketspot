"""밸류 컨텍스트 테스트 — 순수 위치 계산 + 서비스 조합(기본정보·봉은 fake)."""

from __future__ import annotations

from datetime import UTC, datetime

from app.models import Bar, DataEnvelope, DataStatus, Fundamentals
from app.providers.registry import ProviderRegistry
from app.services.valuation import ValuationService, week52_position


def test_week52_position_midpoint() -> None:
    assert week52_position(150.0, 100.0, 200.0) == 50.0


def test_week52_position_at_high() -> None:
    assert week52_position(200.0, 100.0, 200.0) == 100.0


def test_week52_position_none_when_degenerate() -> None:
    assert week52_position(100.0, 100.0, 100.0) is None  # high==low


class _FundProv:
    name = "fake-fund"

    def __init__(self, fund: Fundamentals) -> None:
        self._fund = fund

    async def get(self, symbol: str) -> Fundamentals:
        return self._fund


class _BarsProv:
    name = "fake-bars"

    async def get_quote(self, symbol: str) -> DataEnvelope:  # type: ignore[type-arg]
        from app.models import Quote

        return DataEnvelope.ok(
            Quote(symbol=symbol, price=250.0), source=self.name, status=DataStatus.LIVE
        )

    async def get_bars(
        self, symbol: str, period: str, interval: str
    ) -> DataEnvelope[list[Bar]]:
        # 마지막 종가 250, 직전 200개 평균 < 250 → 과열(+) 신호
        bars = [
            Bar(
                time=datetime(2025, 1, 1, tzinfo=UTC),
                open=100.0,
                high=100.0,
                low=100.0,
                close=100.0 + i * 0.5,
                volume=1.0,
            )
            for i in range(220)
        ]
        bars[-1] = Bar(
            time=datetime(2026, 1, 1, tzinfo=UTC),
            open=250.0,
            high=250.0,
            low=250.0,
            close=250.0,
            volume=1.0,
        )
        return DataEnvelope.ok(bars, source=self.name, status=DataStatus.DELAYED)


def _service(fund: Fundamentals) -> ValuationService:
    prov = _BarsProv()
    registry = ProviderRegistry({"US": [prov], "KR": [prov]})
    return ValuationService(_FundProv(fund), registry)


async def test_valuation_combines_fundamentals_and_overheating() -> None:
    fund = Fundamentals(
        symbol="AAPL",
        status=DataStatus.DELAYED,
        name="Apple",
        type="EQUITY",
        pe_ratio=30.0,
        dividend_yield=0.5,
        week52_high=260.0,
        week52_low=160.0,
    )
    svc = _service(fund)
    val = await svc.get("AAPL")
    assert val.status == DataStatus.DELAYED
    assert val.pe_ratio == 30.0
    assert val.pe_5y_avg is None  # yfinance 한계 — 정직하게 비움
    assert val.note is not None
    assert val.week52_position_pct == 90.0  # (250-160)/(260-160)*100
    assert val.vs_ma200_pct is not None and val.vs_ma200_pct > 0


async def test_valuation_propagates_no_data() -> None:
    fund = Fundamentals(symbol="ZZZZ", status=DataStatus.NO_DATA, message="없음")
    svc = _service(fund)
    val = await svc.get("ZZZZ")
    assert val.status == DataStatus.NO_DATA
    assert val.message is not None
