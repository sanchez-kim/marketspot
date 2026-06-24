"""거래내역 → 보유 도출(이동평균법). 순수 함수, 네트워크/시간 의존 없음."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from ..models import Transaction
from ..providers.base import market_of


@dataclass
class DerivedHolding:
    symbol: str
    quantity: float
    avg_cost: float
    realized_pnl: float
    currency: str


def currency_of(symbol: str) -> str:
    return "KRW" if market_of(symbol) == "KR" else "USD"


def derive_holdings(txns: Sequence[Transaction]) -> list[DerivedHolding]:
    """종목별로 입력 순서대로 fold. 보유수량>0 인 종목만 반환(첫 등장 순서)."""
    state: dict[str, DerivedHolding] = {}
    order: list[str] = []
    for t in txns:
        sym = t.symbol.upper()
        h = state.get(sym)
        if h is None:
            h = DerivedHolding(sym, 0.0, 0.0, 0.0, currency_of(sym))
            state[sym] = h
            order.append(sym)
        if t.type == "buy":
            total = h.quantity * h.avg_cost + t.quantity * t.price
            h.quantity += t.quantity
            h.avg_cost = total / h.quantity if h.quantity else 0.0
        else:  # sell
            sold = min(t.quantity, h.quantity)  # 초과분은 클램프(라우터에서 사전 거부)
            h.realized_pnl += (t.price - h.avg_cost) * sold
            h.quantity -= sold
    return [state[s] for s in order if state[s].quantity > 0]
