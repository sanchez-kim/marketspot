"""포트폴리오 저장/로드 테스트 (임시 디렉터리)."""

from __future__ import annotations

import pytest

from app.models import Position
from app.portfolio_store import load_positions, save_positions


@pytest.fixture
def tmp_data_dir(tmp_path, monkeypatch):  # type: ignore[no-untyped-def]
    monkeypatch.setenv("STOCK_TERMINAL_DATA_DIR", str(tmp_path))
    return tmp_path


def test_save_then_load_roundtrip(tmp_data_dir) -> None:  # type: ignore[no-untyped-def]
    positions = [
        Position(symbol="VOO", quantity=2.5, avg_cost=600.0),
        Position(symbol="QQQM", quantity=10, avg_cost=200.0),
    ]
    save_positions(positions)
    loaded = load_positions()
    assert loaded == positions


def test_load_missing_file_returns_empty(tmp_data_dir) -> None:  # type: ignore[no-untyped-def]
    assert load_positions() == []
