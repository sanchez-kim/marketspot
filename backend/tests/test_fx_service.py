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


async def test_usd_krw_price_status_with_none_data_does_not_raise() -> None:
    """Regression: envelope with data=None but a price-bearing status (e.g. LIVE)
    must NOT cause usd_krw() to raise ValueError via DataEnvelope.empty().
    Instead it should return a degraded envelope with data=None and a
    non-price status (ERROR).
    """
    # Construct a malformed-but-plausible envelope: status=LIVE, data=None.
    # We bypass ok()/empty() and instantiate directly because ok() requires
    # non-None data and empty() rejects LIVE/DELAYED.
    bad_env: DataEnvelope[Quote] = DataEnvelope[Quote](
        status=DataStatus.LIVE, source="yf", data=None
    )
    fx = FxService(_FakeQuotes(bad_env))  # type: ignore[arg-type]
    out = await fx.usd_krw()  # must not raise
    assert out.data is None
    assert out.status not in (DataStatus.LIVE, DataStatus.DELAYED)
