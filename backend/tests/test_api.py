"""API 계약 테스트 — 모든 응답이 DataEnvelope 형태인지 검증.

fake provider 로 네트워크만 대체하고, 라우터/서비스/직렬화 경로는 실제로
실행한다(CLAUDE.md §1.4 계약 테스트).
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.deps import get_chart_service, get_quote_service
from app.main import app
from app.models import DataStatus
from app.providers.registry import ProviderRegistry
from app.services.chart import ChartService
from app.services.quotes import QuoteService

from .fakes import FakeProvider


@pytest.fixture
def client() -> Iterator[TestClient]:
    reg = ProviderRegistry(
        {"US": [FakeProvider("fake", quote_status=DataStatus.DELAYED)]}
    )
    app.dependency_overrides[get_quote_service] = lambda: QuoteService(reg)
    app.dependency_overrides[get_chart_service] = lambda: ChartService(reg)
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_quotes_endpoint_returns_envelope(client: TestClient) -> None:
    resp = client.get("/api/quotes", params={"symbols": "AAPL,VOO"})
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {"AAPL", "VOO"}
    env = body["AAPL"]
    assert env["status"] == "DELAYED"
    assert env["source"] == "fake"
    assert env["data"]["symbol"] == "AAPL"
    assert "changePct" in env["data"]  # camelCase 계약


def test_chart_endpoint_returns_envelope(client: TestClient) -> None:
    resp = client.get("/api/chart/AAPL", params={"period": "1Y", "interval": "1D"})
    assert resp.status_code == 200
    env = resp.json()
    assert env["status"] in {"LIVE", "DELAYED", "STALE"}
    assert env["data"]["period"] == "1Y"
    assert env["data"]["interval"] == "1D"
    assert len(env["data"]["bars"]) > 0
    assert "rsi" in env["data"]["indicators"]


def test_chart_endpoint_normalizes_invalid_params(client: TestClient) -> None:
    resp = client.get("/api/chart/AAPL", params={"period": "BOGUS", "interval": "ZZ"})
    assert resp.status_code == 200
    env = resp.json()
    # 잘못된 값은 기본값으로 정규화
    assert env["data"]["period"] == "1Y"
    assert env["data"]["interval"] == "1D"


def test_health_endpoint(client: TestClient) -> None:
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
