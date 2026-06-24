"""포트폴리오 평가 서비스 테스트 (네트워크 없음).

거래내역에서 보유를 도출하고, 시세로 평가하며, '시세 없는 포지션' 의 정직한
처리(평가액 null·합계 제외)와 실현손익·양통화 합계를 검증한다(CLAUDE.md §0).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

import pytest

from app.models import DataEnvelope, DataStatus, Quote, Transaction
from app.services.fx import FxService
from app.services.portfolio import PortfolioService


class FakeQuotes:
    """심볼→가격(또는 None=시세없음)을 돌려주는 가짜 시세 서비스.

    환율 심볼(KRW=X)도 prices 에 포함하면 FxService 가 환율을 얻는다.
    """

    def __init__(self, prices: dict[str, float | None]) -> None:
        self._prices = prices

    async def get_quotes(
        self, symbols: Sequence[str]
    ) -> dict[str, DataEnvelope[Quote]]:
        out: dict[str, DataEnvelope[Quote]] = {}
        for s in symbols:
            key = s.strip()
            price = self._prices.get(key)
            if price is None:
                out[key] = DataEnvelope[Quote].empty(
                    source="fake", status=DataStatus.NO_DATA, message="no data"
                )
            else:
                out[key] = DataEnvelope.ok(
                    Quote(symbol=key, price=price, name=key, currency="USD"),
                    source="fake",
                    status=DataStatus.DELAYED,
                    as_of=datetime(2026, 1, 2, tzinfo=UTC),
                )
        return out


def _txn(**kw: object) -> Transaction:
    base: dict[str, object] = {"id": "x", "date": None, "currency": "USD"}
    base.update(kw)
    return Transaction.model_validate(base)


def _svc(prices: dict[str, float | None], txns: list[Transaction]) -> PortfolioService:
    quotes = FakeQuotes(prices)
    return PortfolioService(quotes, FxService(quotes), txns_loader=lambda: txns)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_summary_derives_positions_and_realized() -> None:
    txns = [
        _txn(type="buy", symbol="VOO", quantity=10, price=500),
        _txn(type="sell", symbol="VOO", quantity=4, price=700),
    ]
    summary = await _svc({"VOO": 680.0, "KRW=X": 1300.0}, txns).get_summary()
    [pos] = summary.positions
    assert pos.symbol == "VOO"
    assert pos.quantity == 6
    assert pos.avg_cost == 500
    assert pos.realized_pnl == 800  # (700-500)*4
    assert pos.market_value == 6 * 680.0
    assert summary.fx_rate == 1300.0
    assert summary.value_usd == 6 * 680.0  # 단일 USD
    assert summary.total_realized == 800


@pytest.mark.asyncio
async def test_valuation_math_and_weights() -> None:
    txns = [
        _txn(type="buy", symbol="VOO", quantity=2, price=600),
        _txn(type="buy", symbol="QQQM", quantity=10, price=200),
    ]
    summary = await _svc({"VOO": 678.0, "QQQM": 290.0}, txns).get_summary()

    voo = summary.positions[0]
    assert voo.cost_basis == pytest.approx(1200)
    assert voo.market_value == pytest.approx(1356)
    assert voo.unrealized_pnl == pytest.approx(156)
    assert voo.unrealized_pnl_pct == pytest.approx(13.0)
    assert voo.status is DataStatus.DELAYED

    assert summary.total_value == pytest.approx(4256)
    assert summary.total_cost == pytest.approx(3200)
    assert summary.total_pnl == pytest.approx(1056)
    assert summary.total_pnl_pct == pytest.approx(33.0)
    assert summary.valued_count == 2
    assert summary.unvalued_count == 0

    # 비중 합은 100%
    weights = [p.weight for p in summary.positions]
    assert sum(w for w in weights if w is not None) == pytest.approx(100.0)


@pytest.mark.asyncio
async def test_missing_quote_is_not_fabricated() -> None:
    txns = [
        _txn(type="buy", symbol="VOO", quantity=1, price=600),
        _txn(type="buy", symbol="ZZZZ", quantity=5, price=10),  # 시세 없음
    ]
    summary = await _svc({"VOO": 700.0, "ZZZZ": None}, txns).get_summary()

    zzzz = summary.positions[1]
    assert zzzz.status is DataStatus.NO_DATA
    assert zzzz.price is None
    assert zzzz.market_value is None
    assert zzzz.unrealized_pnl is None
    assert zzzz.weight is None
    assert zzzz.cost_basis == pytest.approx(50)  # 원금은 사용자 입력이라 표시

    # 합계는 시세 있는 VOO 만 반영
    assert summary.total_value == pytest.approx(700)
    assert summary.total_cost == pytest.approx(600)
    assert summary.valued_count == 1
    assert summary.unvalued_count == 1


@pytest.mark.asyncio
async def test_empty_portfolio() -> None:
    summary = await _svc({}, []).get_summary()
    assert summary.positions == []
    assert summary.total_value == 0
    assert summary.total_pnl_pct is None
    assert summary.valued_count == 0
    assert summary.total_realized == 0


@pytest.mark.asyncio
async def test_zero_cost_basis_has_null_pct() -> None:
    """평단 0(무상 취득 등)이면 수익률 분모가 0 → null(0으로 나누지 않음)."""
    txns = [_txn(type="buy", symbol="FREE", quantity=3, price=0)]
    summary = await _svc({"FREE": 50.0}, txns).get_summary()
    pos = summary.positions[0]
    assert pos.market_value == pytest.approx(150)
    assert pos.unrealized_pnl == pytest.approx(150)
    assert pos.unrealized_pnl_pct is None
    assert summary.total_pnl_pct is None
