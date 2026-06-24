from __future__ import annotations

import pytest

from app.analytics.holdings import currency_of, derive_holdings
from app.models import Transaction


def _t(**kw: object) -> Transaction:
    base = {"id": "x", "date": None, "currency": "USD"}
    base.update(kw)
    return Transaction.model_validate(base)


def test_currency_of_by_market() -> None:
    assert currency_of("VOO") == "USD"
    assert currency_of("005930.KS") == "KRW"
    assert currency_of("035720.KQ") == "KRW"


def test_moving_average_cost_on_buys() -> None:
    txns = [
        _t(type="buy", symbol="VOO", quantity=10, price=500),
        _t(type="buy", symbol="VOO", quantity=10, price=600),
    ]
    [h] = derive_holdings(txns)
    assert h.symbol == "VOO"
    assert h.quantity == 20
    assert h.avg_cost == 550  # (10*500 + 10*600)/20
    assert h.realized_pnl == 0


def test_sell_keeps_avg_cost_and_accrues_realized() -> None:
    txns = [
        _t(type="buy", symbol="VOO", quantity=10, price=500),
        _t(type="sell", symbol="VOO", quantity=4, price=700),
    ]
    [h] = derive_holdings(txns)
    assert h.quantity == 6
    assert h.avg_cost == 500  # 매도는 평단 불변
    assert h.realized_pnl == pytest.approx((700 - 500) * 4)  # 800


def test_fully_sold_symbol_drops_from_positions_but_keeps_realized() -> None:
    txns = [
        _t(type="buy", symbol="AAPL", quantity=5, price=100),
        _t(type="sell", symbol="AAPL", quantity=5, price=120),
        _t(type="buy", symbol="VOO", quantity=1, price=500),
    ]
    result = derive_holdings(txns)
    symbols = [h.symbol for h in result]
    assert "AAPL" not in symbols  # 수량 0 → 포지션 제외
    assert "VOO" in symbols
