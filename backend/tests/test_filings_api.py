"""공시 API 계약 테스트 — 응답이 DataEnvelope[FilingList] 형태인지 검증.

fake 제공자로 네트워크만 대체하고 라우터/서비스/직렬화는 실제로 실행한다.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.deps import get_filings_service
from app.main import app
from app.models import DataStatus, Filing
from app.services.filings import FilingsService

from .fakes import FakeFilingsProvider

_FILING = Filing(
    form="8-K",
    title="Current report",
    filed=datetime(2026, 3, 1),
    url="https://example.com/8k",
    accession="0000000000-26-000009",
)


@pytest.fixture
def client() -> Iterator[TestClient]:
    svc = FilingsService({"US": FakeFilingsProvider([_FILING])})
    app.dependency_overrides[get_filings_service] = lambda: svc
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_filings_endpoint_returns_envelope(client: TestClient) -> None:
    resp = client.get("/api/filings", params={"symbol": "AAPL"})
    assert resp.status_code == 200
    env = resp.json()
    assert env["status"] == "DELAYED"
    assert env["source"] == "fake-filings"
    data = env["data"]
    assert data["market"] == "US"
    assert data["filings"][0]["form"] == "8-K"
    assert "reportDate" in data["filings"][0]  # camelCase 계약


def test_filings_endpoint_empty_status(client: TestClient) -> None:
    svc = FilingsService({"US": FakeFilingsProvider([], status=DataStatus.NO_DATA)})
    app.dependency_overrides[get_filings_service] = lambda: svc
    resp = client.get("/api/filings", params={"symbol": "AAPL"})
    assert resp.status_code == 200
    env = resp.json()
    assert env["status"] == "NO_DATA"
    assert env["data"] is None
