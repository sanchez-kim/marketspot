"""Settings API — persistence regression tests (CLAUDE.md §1).

Verifies that ui.baseCurrency and ui.onboarded round-trip through
PUT /api/settings and survive a subsequent GET.

Isolation seam: data_dir() reads STOCK_TERMINAL_DATA_DIR env var
(app/config.py line 19), so monkeypatching that env var redirects
all file I/O to tmp_path.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app


def test_ui_base_currency_and_onboarded_persist(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # 설정 파일을 임시 경로로 격리
    monkeypatch.setenv("STOCK_TERMINAL_DATA_DIR", str(tmp_path))
    client = TestClient(app)
    # 기본값
    ui = client.get("/api/settings").json()["ui"]
    assert ui["baseCurrency"] == "USD"
    assert ui["onboarded"] is False
    # PUT 으로 변경 → 라운드트립
    out = client.put(
        "/api/settings", json={"ui": {"baseCurrency": "KRW", "onboarded": True}}
    ).json()
    assert out["ui"]["baseCurrency"] == "KRW"
    assert out["ui"]["onboarded"] is True
    # 재조회에도 유지
    again = client.get("/api/settings").json()["ui"]
    assert again["baseCurrency"] == "KRW"
    assert again["onboarded"] is True
