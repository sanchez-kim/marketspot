# backend/tests/test_fx_service.py
from __future__ import annotations

from app.models import DataEnvelope, DataStatus, Quote
from app.services.fx import FxService


class _FakeQuotes:
    def __init__(self, env: DataEnvelope) -> None:  # type: ignore[type-arg]
        self._env = env

    async def get_quotes(self, symbols: list[str]) -> dict:  # type: ignore[type-arg]
        return {symbols[0]: self._env}


async def test_usd_krw_returns_rate() -> None:
    env = DataEnvelope.ok(
        Quote(symbol="KRW=X", price=1374.5), source="yf", status=DataStatus.DELAYED
    )
    fx = FxService(_FakeQuotes(env))  # type: ignore[arg-type]
    out = await fx.usd_krw()
    assert out.status is DataStatus.DELAYED
    assert out.data == 1374.5


async def test_usd_krw_missing_is_no_data() -> None:
    env = DataEnvelope[Quote].empty(source="yf", status=DataStatus.NO_DATA)
    fx = FxService(_FakeQuotes(env))  # type: ignore[arg-type]
    out = await fx.usd_krw()
    assert out.status is DataStatus.NO_DATA
    assert out.data is None
