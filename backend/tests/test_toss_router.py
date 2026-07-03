"""토스 라우터 테스트 (TestClient — 결정적, 실네트워크 없음).

키/계좌 설정은 tmp ``settings.json`` 으로 격리한다(STOCK_TERMINAL_DATA_DIR).
동기화 서비스와 클라이언트 팩토리는 의존성 오버라이드/monkeypatch 로 페이크를
주입한다 — 라우터의 봉투(DataEnvelope) 계약과 흐름만 검증한다.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app import deps
from app.config import ApiKeys, Settings, save_settings
from app.deps import get_toss_sync_service
from app.main import app
from app.models import DriftWarning, TossSyncResult
from app.providers.toss_client import TossAccount
from app.services.toss_sync import TossSyncError


def _write_settings(**kwargs: object) -> None:
    save_settings(Settings(**kwargs))


class FakeStatusClient:
    def __init__(
        self,
        accounts: list[TossAccount],
        *,
        error: Exception | None = None,
    ) -> None:
        self._accounts = accounts
        self._error = error
        self.closed = 0

    async def get_accounts(self) -> list[TossAccount]:
        if self._error is not None:
            raise self._error
        return self._accounts

    async def aclose(self) -> None:
        self.closed += 1


def _rate_limited_error() -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "https://toss.example/accounts")
    response = httpx.Response(429, request=request)
    return httpx.HTTPStatusError("rate limited", request=request, response=response)


def _toss_error(
    status_code: int, body: dict[str, object] | None
) -> httpx.HTTPStatusError:
    """토스 표준 에러 바디(``{"error":{"message":...}}``, 공식 문서 확인)를
    가진 실패 응답. ``body=None`` 이면 비-JSON 본문(파싱 실패 폴백 테스트용)."""
    request = httpx.Request("GET", "https://toss.example/accounts")
    content = json.dumps(body).encode() if body is not None else b"not json"
    response = httpx.Response(status_code, request=request, content=content)
    return httpx.HTTPStatusError("http error", request=request, response=response)


class StubSyncService:
    def __init__(
        self,
        *,
        baseline: bool,
        result: TossSyncResult,
        drift: list[DriftWarning],
        sync_error: Exception | None = None,
        drift_error: Exception | None = None,
    ) -> None:
        self._baseline = baseline
        self._result = result
        self._drift = drift
        self._sync_error = sync_error
        self._drift_error = drift_error
        self.calls: list[str] = []

    def has_baseline(self, account_seq: str) -> bool:
        return self._baseline

    async def bootstrap(self, account_seq: str) -> TossSyncResult:
        self.calls.append("bootstrap")
        if self._sync_error is not None:
            raise self._sync_error
        return self._result

    async def incremental(self, account_seq: str) -> TossSyncResult:
        self.calls.append("incremental")
        if self._sync_error is not None:
            raise self._sync_error
        return self._result

    async def drift_check(self, account_seq: str) -> list[DriftWarning]:
        if self._drift_error is not None:
            raise self._drift_error
        return self._drift


@pytest.fixture(autouse=True)
def _tmp_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("STOCK_TERMINAL_DATA_DIR", str(tmp_path))
    yield
    app.dependency_overrides.clear()


# ── status ────────────────────────────────────────────────────────────────────


def test_status_needs_key_when_unconfigured() -> None:
    _write_settings()  # 키 없음
    client = TestClient(app)
    resp = client.get("/api/toss/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "NEEDS_KEY"
    assert body["data"] is None


def test_status_lists_accounts_when_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_settings(
        api_keys=ApiKeys(toss_app_key="ak", toss_app_secret="sk"),
        toss_account_seq="7",
        toss_last_sync="2026-03-25T00:00:00+00:00",
    )
    fake = FakeStatusClient(
        [TossAccount(account_no="12345678901", account_seq=7, account_type="BROKERAGE")]
    )
    monkeypatch.setattr(
        "app.routers.toss.get_toss_client_factory", lambda: lambda: fake
    )
    client = TestClient(app)
    resp = client.get("/api/toss/status")
    body = resp.json()
    assert body["status"] == "LIVE"
    data = body["data"]
    assert data["connected"] is True
    assert data["selectedAccountSeq"] == "7"
    assert data["lastSync"] == "2026-03-25T00:00:00+00:00"
    assert len(data["accounts"]) == 1
    acc = data["accounts"][0]
    assert acc["accountSeq"] == "7"
    assert acc["label"] == "BROKERAGE (12345678901)"
    assert fake.closed == 1  # 클라이언트 정리됨


def test_status_rate_limited_on_429(monkeypatch: pytest.MonkeyPatch) -> None:
    _write_settings(
        api_keys=ApiKeys(toss_app_key="ak", toss_app_secret="sk"),
        toss_account_seq="7",
    )
    fake = FakeStatusClient([], error=_rate_limited_error())
    monkeypatch.setattr(
        "app.routers.toss.get_toss_client_factory", lambda: lambda: fake
    )
    client = TestClient(app)
    resp = client.get("/api/toss/status")
    assert resp.json()["status"] == "RATE_LIMITED"


def test_status_error_on_generic_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    _write_settings(
        api_keys=ApiKeys(toss_app_key="ak", toss_app_secret="sk"),
        toss_account_seq="7",
    )
    fake = FakeStatusClient([], error=httpx.ConnectError("boom"))
    monkeypatch.setattr(
        "app.routers.toss.get_toss_client_factory", lambda: lambda: fake
    )
    client = TestClient(app)
    resp = client.get("/api/toss/status")
    assert resp.json()["status"] == "ERROR"


def test_status_error_uses_toss_error_body_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """토스 표준 에러 바디의 message 를 뽑아 쓴다(공식 문서 확인, 2026-07)."""
    _write_settings(
        api_keys=ApiKeys(toss_app_key="ak", toss_app_secret="sk"),
        toss_account_seq="7",
    )
    err = _toss_error(
        500,
        {
            "error": {
                "requestId": "r1",
                "code": "E500",
                "message": "토스 서버 오류입니다",
            }
        },
    )
    fake = FakeStatusClient([], error=err)
    monkeypatch.setattr(
        "app.routers.toss.get_toss_client_factory", lambda: lambda: fake
    )
    client = TestClient(app)
    resp = client.get("/api/toss/status")
    body = resp.json()
    assert body["status"] == "ERROR"
    assert "토스 서버 오류입니다" in body["message"]


def test_status_error_falls_back_when_body_is_not_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """에러 바디가 예상 형식이 아니면 httpx 일반 문자열로 폴백(정보를 삼키지 않음)."""
    _write_settings(
        api_keys=ApiKeys(toss_app_key="ak", toss_app_secret="sk"),
        toss_account_seq="7",
    )
    err = _toss_error(500, None)
    fake = FakeStatusClient([], error=err)
    monkeypatch.setattr(
        "app.routers.toss.get_toss_client_factory", lambda: lambda: fake
    )
    client = TestClient(app)
    resp = client.get("/api/toss/status")
    body = resp.json()
    assert body["status"] == "ERROR"
    assert "http error" in body["message"]


# ── PUT account ────────────────────────────────────────────────────────────────


def test_put_account_persists_seq(monkeypatch: pytest.MonkeyPatch) -> None:
    _write_settings(api_keys=ApiKeys(toss_app_key="ak", toss_app_secret="sk"))
    fake = FakeStatusClient([])
    monkeypatch.setattr(
        "app.routers.toss.get_toss_client_factory", lambda: lambda: fake
    )
    client = TestClient(app)
    resp = client.put("/api/toss/account", json={"accountSeq": "42"})
    assert resp.status_code == 200
    assert resp.json()["data"]["selectedAccountSeq"] == "42"
    # 파일에 저장됐는지 재로딩으로 확인.
    from app.config import load_settings

    assert load_settings().toss_account_seq == "42"


def test_put_account_needs_key_when_unconfigured() -> None:
    _write_settings()
    client = TestClient(app)
    resp = client.put("/api/toss/account", json={"accountSeq": "42"})
    assert resp.json()["status"] == "NEEDS_KEY"


# ── POST sync ──────────────────────────────────────────────────────────────────


def test_sync_needs_key_when_unconfigured() -> None:
    _write_settings()
    client = TestClient(app)
    resp = client.post("/api/toss/sync")
    assert resp.json()["status"] == "NEEDS_KEY"


def test_sync_no_data_when_no_account_selected() -> None:
    _write_settings(api_keys=ApiKeys(toss_app_key="ak", toss_app_secret="sk"))
    client = TestClient(app)
    resp = client.post("/api/toss/sync")
    assert resp.json()["status"] == "NO_DATA"


def test_sync_bootstrap_when_no_baseline() -> None:
    _write_settings(
        api_keys=ApiKeys(toss_app_key="ak", toss_app_secret="sk"),
        toss_account_seq="7",
    )
    stub = StubSyncService(
        baseline=False,
        result=TossSyncResult(mode="bootstrap", added=2),
        drift=[DriftWarning(symbol="005930", app_qty=10, toss_qty=12)],
    )
    app.dependency_overrides[get_toss_sync_service] = lambda: stub
    client = TestClient(app)
    resp = client.post("/api/toss/sync")
    body = resp.json()
    assert body["status"] == "LIVE"
    assert stub.calls == ["bootstrap"]
    data = body["data"]
    assert data["mode"] == "bootstrap"
    assert data["added"] == 2
    assert data["drift"] == [{"symbol": "005930", "appQty": 10.0, "tossQty": 12.0}]


def test_sync_incremental_when_baseline_exists() -> None:
    _write_settings(
        api_keys=ApiKeys(toss_app_key="ak", toss_app_secret="sk"),
        toss_account_seq="7",
    )
    stub = StubSyncService(
        baseline=True,
        result=TossSyncResult(mode="incremental", added=3, skipped_unpriced=1),
        drift=[],
    )
    app.dependency_overrides[get_toss_sync_service] = lambda: stub
    client = TestClient(app)
    resp = client.post("/api/toss/sync")
    body = resp.json()
    assert stub.calls == ["incremental"]
    assert body["data"]["mode"] == "incremental"
    assert body["data"]["skippedUnpriced"] == 1


def test_sync_rate_limited_when_sync_raises_429() -> None:
    _write_settings(
        api_keys=ApiKeys(toss_app_key="ak", toss_app_secret="sk"),
        toss_account_seq="7",
    )
    stub = StubSyncService(
        baseline=False,
        result=TossSyncResult(mode="bootstrap", added=0),
        drift=[],
        sync_error=_rate_limited_error(),
    )
    app.dependency_overrides[get_toss_sync_service] = lambda: stub
    client = TestClient(app)
    resp = client.post("/api/toss/sync")
    body = resp.json()
    assert body["status"] == "RATE_LIMITED"
    assert body["data"] is None


def test_sync_error_when_sync_raises_generic_error() -> None:
    _write_settings(
        api_keys=ApiKeys(toss_app_key="ak", toss_app_secret="sk"),
        toss_account_seq="7",
    )
    stub = StubSyncService(
        baseline=True,
        result=TossSyncResult(mode="incremental", added=0),
        drift=[],
        sync_error=TossSyncError("boom"),
    )
    app.dependency_overrides[get_toss_sync_service] = lambda: stub
    client = TestClient(app)
    resp = client.post("/api/toss/sync")
    body = resp.json()
    assert body["status"] == "ERROR"
    assert body["data"] is None


def test_sync_preserves_result_when_drift_check_fails() -> None:
    """드리프트 확인이 실패해도 이미 성공한 동기화 결과는 지워지지 않는다.

    §0 정직성: 부분 성공(거래 저장 완료)을 숨기지 않는다. drift 는 "모른다"는
    뜻으로 빈 채 두고, message 로 드리프트 확인 실패를 알린다.
    """
    _write_settings(
        api_keys=ApiKeys(toss_app_key="ak", toss_app_secret="sk"),
        toss_account_seq="7",
    )
    stub = StubSyncService(
        baseline=True,
        result=TossSyncResult(mode="incremental", added=3),
        drift=[],
        drift_error=httpx.ConnectError("boom"),
    )
    app.dependency_overrides[get_toss_sync_service] = lambda: stub
    client = TestClient(app)
    resp = client.post("/api/toss/sync")
    body = resp.json()
    assert body["status"] == "LIVE"
    assert body["data"] is not None
    assert body["data"]["added"] == 3
    assert body["data"]["mode"] == "incremental"
    assert body["message"] is not None
    assert "드리프트" in body["message"]


def test_reset_service_caches_clears_toss_factories() -> None:
    """키 변경 시 재시작 없이 반영되도록 토스 팩토리 캐시가 비워지는지."""
    _write_settings(api_keys=ApiKeys(toss_app_key="ak", toss_app_secret="sk"))
    factory_before = deps.get_toss_client_factory()
    service_before = deps.get_toss_sync_service()
    deps.reset_service_caches()
    assert deps.get_toss_client_factory() is not factory_before
    assert deps.get_toss_sync_service() is not service_before
