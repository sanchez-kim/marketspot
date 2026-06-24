"""포트폴리오 API 계약 테스트 — 응답이 PortfolioSummary(camelCase)인지 검증."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.transaction_store as ts
from app.deps import get_portfolio_service
from app.main import app
from app.models import Transaction
from app.services.fx import FxService
from app.services.portfolio import PortfolioService
from app.transaction_store import load_transactions

from .test_portfolio_service import FakeQuotes


@pytest.fixture
def client() -> Iterator[TestClient]:
    txns = [
        Transaction(
            id="1",
            date=None,
            type="buy",
            symbol="VOO",
            quantity=2,
            price=600,
            currency="USD",
        ),
        Transaction(
            id="2",
            date=None,
            type="buy",
            symbol="QQQM",
            quantity=10,
            price=200,
            currency="USD",
        ),
    ]
    quotes = FakeQuotes({"VOO": 678.0, "QQQM": 290.0})
    svc = PortfolioService(
        quotes,  # type: ignore[arg-type]
        FxService(quotes),  # type: ignore[arg-type]
        txns_loader=lambda: txns,
    )
    app.dependency_overrides[get_portfolio_service] = lambda: svc
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def crud_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[TestClient]:
    """거래 CRUD 엔드포인트용 격리 클라이언트.

    - transaction_store._default_path 를 tmp 파일로 패치 → 실제 파일 오염 없음.
    - PortfolioService 는 fake 시세(네트워크 없음) + real load_transactions(격리 파일).
    """
    txns_path = str(tmp_path / "transactions.json")
    monkeypatch.setattr(ts, "_default_path", lambda: txns_path)

    quotes = FakeQuotes({"VOO": 500.0, "AAPL": 100.0})
    svc = PortfolioService(
        quotes,  # type: ignore[arg-type]
        FxService(quotes),  # type: ignore[arg-type]
        txns_loader=load_transactions,
    )
    app.dependency_overrides[get_portfolio_service] = lambda: svc
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_get_portfolio_returns_summary(client: TestClient) -> None:
    resp = client.get("/api/portfolio")
    assert resp.status_code == 200
    body = resp.json()
    # camelCase 계약
    assert {"positions", "totalValue", "totalPnl", "totalPnlPct", "valuedCount"} <= set(
        body.keys()
    )
    assert body["totalValue"] == pytest.approx(4256)
    pos0 = body["positions"][0]
    assert pos0["symbol"] == "VOO"
    assert "marketValue" in pos0
    assert "unrealizedPnlPct" in pos0
    assert pos0["status"] == "DELAYED"


# ---------------------------------------------------------------------------
# 거래 CRUD 테스트 (격리 픽스처 사용)
# ---------------------------------------------------------------------------


def test_add_buy_then_list_and_summary(crud_client: TestClient) -> None:
    r = crud_client.post(
        "/api/portfolio/transactions",
        json={
            "type": "buy",
            "symbol": "VOO",
            "quantity": 10,
            "price": 500,
            "date": "2026-06-01",
        },
    )
    assert r.status_code == 200
    summary = r.json()
    assert any(
        p["symbol"] == "VOO" and p["quantity"] == 10 for p in summary["positions"]
    )

    lst = crud_client.get("/api/portfolio/transactions").json()
    assert len(lst) == 1
    assert lst[0]["currency"] == "USD"
    assert lst[0]["id"]


def test_oversell_is_rejected(crud_client: TestClient) -> None:
    crud_client.post(
        "/api/portfolio/transactions",
        json={"type": "buy", "symbol": "AAPL", "quantity": 5, "price": 100},
    )
    r = crud_client.post(
        "/api/portfolio/transactions",
        json={"type": "sell", "symbol": "AAPL", "quantity": 9, "price": 120},
    )
    assert r.status_code == 400
    assert "보유" in r.json()["detail"]


def test_delete_transaction(crud_client: TestClient) -> None:
    crud_client.post(
        "/api/portfolio/transactions",
        json={"type": "buy", "symbol": "VOO", "quantity": 1, "price": 500},
    )
    tid = crud_client.get("/api/portfolio/transactions").json()[0]["id"]
    r = crud_client.delete(f"/api/portfolio/transactions/{tid}")
    assert r.status_code == 200
    assert crud_client.get("/api/portfolio/transactions").json() == []
