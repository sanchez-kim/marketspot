"""거래내역 로컬 저장 (data/transactions.json) + 기존 포지션 마이그레이션."""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable

from .analytics.holdings import currency_of
from .config import data_dir
from .models import Position, Transaction


def _default_path() -> str:
    return str(data_dir() / "transactions.json")


def load_transactions(path: str | None = None) -> list[Transaction]:
    p = path or _default_path()
    try:
        raw = json.loads(open(p, encoding="utf-8").read())
    except FileNotFoundError:
        return []
    if not isinstance(raw, list):
        return []
    return [Transaction.model_validate(item) for item in raw]


def save_transactions(txns: list[Transaction], path: str | None = None) -> None:
    payload = [t.model_dump(by_alias=True) for t in txns]
    with open(path or _default_path(), "w", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False, indent=2))


def migrate_positions_to_transactions(positions: list[Position]) -> list[Transaction]:
    return [
        Transaction(
            id=uuid.uuid4().hex,
            date=None,
            type="buy",
            symbol=p.symbol,
            quantity=p.quantity,
            price=p.avg_cost,
            currency=currency_of(p.symbol),
        )
        for p in positions
    ]


def bootstrap_transactions(
    path: str | None,
    positions_loader: Callable[[], list[Position]],
) -> list[Transaction]:
    """txns 파일이 있으면 그대로, 없으면 기존 포지션을 마이그레이션해 저장."""
    existing = load_transactions(path)
    if existing:
        return existing
    migrated = migrate_positions_to_transactions(positions_loader())
    if migrated:
        save_transactions(migrated, path)
    return migrated
