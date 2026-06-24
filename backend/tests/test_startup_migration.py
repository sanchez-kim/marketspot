"""Startup migration — TDD (CLAUDE.md §1).

Tests that _migrate_transactions_on_startup() correctly migrates
data/portfolio.json → data/transactions.json at app startup so that
existing users' holdings are not silently lost.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.models import Position
from app.transaction_store import load_transactions


def _write_portfolio(data_dir: Path, positions: list[Position]) -> None:
    portfolio_path = data_dir / "portfolio.json"
    payload = [p.model_dump(by_alias=True) for p in positions]
    portfolio_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


@pytest.fixture
def isolated_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect data_dir() to tmp_path for both stores."""
    monkeypatch.setenv("STOCK_TERMINAL_DATA_DIR", str(tmp_path))
    return tmp_path


def test_before_migration_load_transactions_returns_empty(
    isolated_data_dir: Path,
) -> None:
    """RED guard: no transactions.json → load_transactions returns []."""
    positions = [
        Position(symbol="VOO", quantity=5, avg_cost=450.0),
        Position(symbol="QQQM", quantity=3, avg_cost=180.0),
    ]
    _write_portfolio(isolated_data_dir, positions)

    # transactions.json does NOT exist yet
    assert not (isolated_data_dir / "transactions.json").exists()
    assert load_transactions() == []


def test_migrate_transactions_on_startup_creates_transactions(
    isolated_data_dir: Path,
) -> None:
    """GREEN: after calling migration fn, transactions.json exists with correct data."""
    positions = [
        Position(symbol="VOO", quantity=5, avg_cost=450.0),
        Position(symbol="QQQM", quantity=3, avg_cost=180.0),
    ]
    _write_portfolio(isolated_data_dir, positions)

    # import the function under test — ImportError/AttributeError == RED before fix
    from app.main import _migrate_transactions_on_startup

    _migrate_transactions_on_startup()

    # transactions.json must now exist
    assert (isolated_data_dir / "transactions.json").exists()

    txns = load_transactions()
    assert len(txns) == 2

    by_symbol = {t.symbol: t for t in txns}
    assert "VOO" in by_symbol
    assert "QQQM" in by_symbol

    voo = by_symbol["VOO"]
    assert voo.type == "buy"
    assert voo.quantity == 5
    assert voo.price == 450.0
    assert voo.currency == "USD"

    qqqm = by_symbol["QQQM"]
    assert qqqm.type == "buy"
    assert qqqm.quantity == 3
    assert qqqm.price == 180.0
    assert qqqm.currency == "USD"


def test_migration_is_idempotent(isolated_data_dir: Path) -> None:
    """Calling migration twice does not duplicate transactions."""
    positions = [Position(symbol="AAPL", quantity=2, avg_cost=175.0)]
    _write_portfolio(isolated_data_dir, positions)

    from app.main import _migrate_transactions_on_startup

    _migrate_transactions_on_startup()
    _migrate_transactions_on_startup()

    txns = load_transactions()
    assert len(txns) == 1


def test_migration_noop_when_no_portfolio(isolated_data_dir: Path) -> None:
    """No portfolio.json and no transactions.json → migration is a no-op."""
    from app.main import _migrate_transactions_on_startup

    _migrate_transactions_on_startup()  # must not raise

    assert not (isolated_data_dir / "transactions.json").exists()
    assert load_transactions() == []
