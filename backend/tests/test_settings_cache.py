"""설정(API 키) 변경 시 키 의존 서비스 캐시가 즉시 무효화되는지 검증.

버그: deps 의 서비스 팩토리가 @lru_cache 라 키를 최초 1회만 읽어, PUT /api/settings
로 키를 넣어도 서버 재시작 전까지 NEEDS_KEY 가 풀리지 않았다.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import deps
from app.main import app


def test_put_settings_clears_key_dependent_service_caches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("STOCK_TERMINAL_DATA_DIR", str(tmp_path))
    # 키 의존 서비스를 한 번 만들어 캐시에 올림(빈 키 상태)
    deps.get_conditions_service.cache_clear()
    deps.get_filings_service.cache_clear()
    cond_before = deps.get_conditions_service()
    filings_before = deps.get_filings_service()

    client = TestClient(app)
    resp = client.put(
        "/api/settings", json={"apiKeys": {"fred": "FREDKEY", "dart": "DARTKEY"}}
    )
    assert resp.status_code == 200

    # PUT 이후엔 새 인스턴스로 재생성되어야 한다(키를 다시 읽도록)
    assert deps.get_conditions_service() is not cond_before
    assert deps.get_filings_service() is not filings_before
