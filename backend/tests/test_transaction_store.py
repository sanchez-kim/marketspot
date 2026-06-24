# backend/tests/test_transaction_store.py
from __future__ import annotations

from pathlib import Path

from app.models import Position
from app.transaction_store import (
    bootstrap_transactions,
    load_transactions,
    migrate_positions_to_transactions,
    save_transactions,
)


def test_migration_preserves_quantity_and_cost() -> None:
    positions = [Position(symbol="VOO", quantity=10, avg_cost=500)]
    txns = migrate_positions_to_transactions(positions)
    assert len(txns) == 1
    t = txns[0]
    assert t.type == "buy"
    assert t.symbol == "VOO"
    assert t.quantity == 10
    assert t.price == 500
    assert t.currency == "USD"
    assert t.date is None
    assert t.id  # 비어있지 않음


def test_save_then_load_roundtrip(tmp_path: Path) -> None:
    p = str(tmp_path / "transactions.json")
    txns = migrate_positions_to_transactions(
        [Position(symbol="005930.KS", quantity=3, avg_cost=70000)]
    )
    save_transactions(txns, p)
    loaded = load_transactions(p)
    assert len(loaded) == 1
    assert loaded[0].currency == "KRW"
    assert loaded[0].symbol == "005930.KS"


def test_bootstrap_migrates_when_no_txn_file(tmp_path: Path) -> None:
    p = str(tmp_path / "transactions.json")
    result = bootstrap_transactions(
        p, lambda: [Position(symbol="AAPL", quantity=5, avg_cost=100)]
    )
    assert len(result) == 1
    # 파일이 생성되어 재로드 가능
    assert len(load_transactions(p)) == 1


def test_load_missing_file_returns_empty(tmp_path: Path) -> None:
    assert load_transactions(str(tmp_path / "nope.json")) == []
