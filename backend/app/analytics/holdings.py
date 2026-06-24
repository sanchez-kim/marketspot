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


@dataclass
class CurrencyTotals:
    krw: float | None
    usd: float | None


def combine_currency_totals(
    by_currency: dict[str, float], *, fx_rate: float | None
) -> CurrencyTotals:
    """통화별 합계를 KRW/USD 양 통화로 환산. 환산 불가면 해당 통화 None."""
    usd = by_currency.get("USD", 0.0)
    krw = by_currency.get("KRW", 0.0)
    has_usd = "USD" in by_currency
    has_krw = "KRW" in by_currency
    if fx_rate:
        return CurrencyTotals(krw=krw + usd * fx_rate, usd=usd + krw / fx_rate)
    # 환율 없음: 단일 통화면 그 통화만 채움
    return CurrencyTotals(
        krw=krw if (has_krw and not has_usd) else None,
        usd=usd if (has_usd and not has_krw) else None,
    )


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
