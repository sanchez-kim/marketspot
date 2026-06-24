"""포트폴리오 라우터.

GET /api/portfolio          — 저장된 거래내역을 실시간 시세로 평가해 반환한다.
GET /api/portfolio/transactions  — 전체 거래내역 목록 반환.
POST /api/portfolio/transactions — 거래 추가(매수/매도 검증 후 저장) → PortfolioSummary.
DELETE /api/portfolio/transactions/{txn_id} — 거래 삭제 → PortfolioSummary.
GET /api/portfolio/risk     — 포트폴리오 집중도·상관 요약.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..analytics.holdings import currency_of, derive_holdings
from ..deps import get_portfolio_service, get_risk_service
from ..models import PortfolioRisk, PortfolioSummary, Transaction
from ..services.portfolio import PortfolioService
from ..services.risk import RiskService
from ..transaction_store import load_transactions, save_transactions

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


class TxnCreate(BaseModel):
    type: Literal["buy", "sell"]
    symbol: str
    quantity: float
    price: float
    date: str | None = None


@router.get("")
async def get_portfolio(
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
) -> PortfolioSummary:
    return await service.get_summary()


@router.get("/transactions")
async def list_transactions() -> list[Transaction]:
    return load_transactions()


@router.post("/transactions")
async def add_transaction(
    body: TxnCreate,
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
) -> PortfolioSummary:
    if body.quantity <= 0:
        raise HTTPException(400, "수량은 0보다 커야 합니다")
    txns = load_transactions()
    new = Transaction(
        id=uuid.uuid4().hex,
        date=body.date,
        type=body.type,
        symbol=body.symbol.upper(),
        quantity=body.quantity,
        price=body.price,
        currency=currency_of(body.symbol),
    )
    # 초과매도 사전 검증: 현재 보유 수량보다 많은 매도 거부
    if body.type == "sell":
        held = next(
            (h.quantity for h in derive_holdings(txns) if h.symbol == new.symbol), 0.0
        )
        if body.quantity > held:
            raise HTTPException(400, f"보유 수량({held})을 초과해 매도할 수 없습니다")
    save_transactions([*txns, new])
    return await service.get_summary()


@router.delete("/transactions/{txn_id}")
async def delete_transaction(
    txn_id: str,
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
) -> PortfolioSummary:
    txns = [t for t in load_transactions() if t.id != txn_id]
    save_transactions(txns)
    return await service.get_summary()


@router.get("/risk")
async def get_portfolio_risk(
    service: Annotated[RiskService, Depends(get_risk_service)],
) -> PortfolioRisk:
    return await service.get_risk()
