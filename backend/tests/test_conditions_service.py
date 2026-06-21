"""거시 환경 서비스 테스트 — FRED 는 fake, 지수 추세는 fake 봉으로 실제 계산."""

from __future__ import annotations

from datetime import UTC, date, datetime

from app.models import Bar, DataEnvelope, DataStatus
from app.providers.macro_provider import Observation
from app.providers.registry import ProviderRegistry
from app.services.conditions import MacroConditionsService


class _FakeFred:
    """series_id 별로 미리 정한 (status, observations) 를 돌려준다."""

    def __init__(self, table: dict[str, tuple[DataStatus, list[Observation]]]) -> None:
        self._table = table

    async def observations(
        self, series_id: str, limit: int
    ) -> tuple[DataStatus, list[Observation]]:
        return self._table.get(series_id, (DataStatus.NO_DATA, []))


class _IndexProvider:
    name = "fake-index"

    async def get_quote(self, symbol: str) -> DataEnvelope:  # type: ignore[type-arg]
        from app.models import Quote

        return DataEnvelope.ok(
            Quote(symbol=symbol, price=100.0), source=self.name, status=DataStatus.LIVE
        )

    async def get_bars(
        self, symbol: str, period: str, interval: str
    ) -> DataEnvelope[list[Bar]]:
        # 220개 상승 봉: 마지막 종가가 MA50/MA200 보다 위 → 양(+) 추세
        bars = [
            Bar(
                time=datetime(2025, 1, 1, tzinfo=UTC),
                open=float(i),
                high=float(i),
                low=float(i),
                close=float(100 + i),
                volume=1.0,
            )
            for i in range(220)
        ]
        return DataEnvelope.ok(bars, source=self.name, status=DataStatus.DELAYED)


def _service(fred_table: dict) -> MacroConditionsService:  # type: ignore[type-arg]
    prov = _IndexProvider()
    registry = ProviderRegistry({"US": [prov], "KR": [prov]})
    fixed = datetime(2026, 6, 21, tzinfo=UTC)
    return MacroConditionsService(_FakeFred(fred_table), registry, now=lambda: fixed)


def _cpi_obs() -> list[Observation]:
    vals = [320.0 - i for i in range(13)]  # desc, 1년 전 = 308.0
    return [Observation(date(2026, 5, 1), v) for v in vals[:1]] + [
        Observation(date(2025, 12, 1), v) for v in vals[1:]
    ]


async def test_conditions_combines_fred_and_index_trend() -> None:
    svc = _service(
        {
            "DFF": (
                DataStatus.DELAYED,
                [
                    Observation(date(2026, 6, 20), 5.25),
                    Observation(date(2026, 6, 19), 5.50),
                ],
            ),
            "CPIAUCSL": (DataStatus.DELAYED, _cpi_obs()),
        }
    )
    cond = await svc.get_conditions()
    assert cond.rate.value == 5.25
    assert cond.rate.change == -0.25  # 인하 방향
    assert cond.rate.status == DataStatus.DELAYED
    assert cond.cpi.value is not None and cond.cpi.status == DataStatus.DELAYED
    assert len(cond.indices) >= 1
    first = cond.indices[0]
    assert first.vs_ma200_pct is not None and first.vs_ma200_pct > 0


async def test_conditions_propagates_needs_key() -> None:
    svc = _service(
        {
            "DFF": (DataStatus.NEEDS_KEY, []),
            "CPIAUCSL": (DataStatus.NEEDS_KEY, []),
        }
    )
    cond = await svc.get_conditions()
    assert cond.rate.status == DataStatus.NEEDS_KEY
    assert cond.rate.value is None
    assert cond.cpi.status == DataStatus.NEEDS_KEY
