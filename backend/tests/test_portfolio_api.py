"""포트폴리오 API 계약 테스트 — 응답이 PortfolioSummary(camelCase)인지 검증."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.deps import get_portfolio_service
from app.main import app
from app.models import Position
from app.services.portfolio import PortfolioService

from .test_portfolio_service import FakeQuotes


@pytest.fixture
def client() -> Iterator[TestClient]:
    positions = [
        Position(symbol="VOO", quantity=2, avg_cost=600),
        Position(symbol="QQQM", quantity=10, avg_cost=200),
    ]
    svc = PortfolioService(
        FakeQuotes({"VOO": 678.0, "QQQM": 290.0}),  # type: ignore[arg-type]
        positions_loader=lambda: positions,
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
