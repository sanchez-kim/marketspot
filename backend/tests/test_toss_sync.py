"""TossSyncService 동기화 로직 테스트 (결정적 — 실네트워크 없음).

TossClient 는 **페이크**로 주입한다(테스트 대상은 동기화 서비스이지 클라이언트가
아니므로 외부 의존을 페이크로 대체 — CLAUDE.md §1.2 위반 아님). 페이크는 실제
pydantic 응답 모델(TossHolding/TossOrder/TossExecution)을 반환해 서비스가 실제
필드로 fold·정렬·멱등·드리프트를 수행하는지 검증한다.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

import pytest

from app.analytics.holdings import derive_holdings
from app.models import Transaction
from app.providers.toss_client import (
    TossExecution,
    TossHolding,
    TossOrder,
    TossOrderPage,
)
from app.services.toss_sync import TossSyncError, TossSyncService


def _dt(day: int, hour: int = 0) -> datetime:
    return datetime(2026, 3, day, hour, 0, tzinfo=UTC)


class FakeTossClient:
    """서비스가 호출하는 메서드만 구현한 페이크(실 모델 반환)."""

    def __init__(
        self,
        *,
        holdings: list[TossHolding] | None = None,
        pages: dict[str | None, TossOrderPage] | None = None,
    ) -> None:
        self._holdings = holdings or []
        # cursor(None=첫 페이지) → 페이지. 미지정이면 빈 마지막 페이지.
        self._pages = pages or {None: TossOrderPage(orders=[], next_cursor=None)}
        self.closed = 0
        self.order_calls: list[tuple[str | None, str | None]] = []

    async def get_holdings(self, account_seq: int | str) -> list[TossHolding]:
        return self._holdings

    async def get_closed_orders(
        self,
        account_seq: int | str,
        from_: str | None = None,
        to: str | None = None,
        cursor: str | None = None,
    ) -> TossOrderPage:
        self.order_calls.append((from_, cursor))
        return self._pages[cursor]

    async def aclose(self) -> None:
        self.closed += 1


def _order(
    order_id: str,
    side: str,
    symbol: str,
    qty: float,
    price: float | None,
    *,
    filled_at: datetime | None,
    commission: float | None = None,
    tax: float | None = None,
    currency: str = "KRW",
) -> TossOrder:
    return TossOrder(
        order_id=order_id,
        symbol=symbol,
        side=side,
        status="CLOSED",
        currency=currency,
        ordered_at=filled_at,
        execution=TossExecution(
            filled_quantity=qty,
            average_filled_price=price,
            commission=commission,
            tax=tax,
            filled_at=filled_at,
        ),
    )


def _make_service(
    client: FakeTossClient,
    *,
    initial: list[Transaction] | None = None,
    last_sync: str = "",
) -> tuple[TossSyncService, dict[str, list[Transaction]], dict[str, str]]:
    store = {"txns": list(initial or [])}
    sync_box = {"v": last_sync}

    def load() -> list[Transaction]:
        return list(store["txns"])

    def save(txns: list[Transaction]) -> None:
        store["txns"] = list(txns)

    def get_ls() -> str:
        return sync_box["v"]

    def set_ls(v: str) -> None:
        sync_box["v"] = v

    factory: Callable[[], FakeTossClient] = lambda: client  # noqa: E731
    service = TossSyncService(
        factory,  # type: ignore[arg-type]
        load_txns=load,
        save_txns=save,
        get_last_sync=get_ls,
        set_last_sync=set_ls,
    )
    return service, store, sync_box


# ── 부트스트랩 ────────────────────────────────────────────────────────────────


async def test_bootstrap_creates_baseline_from_holdings() -> None:
    client = FakeTossClient(
        holdings=[
            TossHolding(
                symbol="005930",
                name="삼성전자",
                quantity=10,
                average_purchase_price=70000,
                currency="KRW",
                last_price=72000,
            ),
            TossHolding(  # 수량 0 은 스킵
                symbol="000660",
                quantity=0,
                average_purchase_price=0,
                currency="KRW",
            ),
        ]
    )
    service, store, _ = _make_service(client)

    result = await service.bootstrap("7")

    assert result.mode == "bootstrap"
    assert result.added == 1
    txns = store["txns"]
    assert len(txns) == 1
    t = txns[0]
    assert t.symbol == "005930"
    assert t.type == "buy"
    assert t.date is None  # 기초 보유(체결일 미상)
    assert t.price == 70000.0
    assert t.quantity == 10.0
    assert t.source == "toss-baseline"
    assert t.external_id == "baseline:7:005930"


async def test_bootstrap_is_idempotent_refuses_rerun() -> None:
    client = FakeTossClient(
        holdings=[
            TossHolding(symbol="005930", quantity=10, average_purchase_price=70000)
        ]
    )
    service, _, _ = _make_service(client)
    await service.bootstrap("7")
    assert service.has_baseline("7") is True

    with pytest.raises(TossSyncError):
        await service.bootstrap("7")


async def test_bootstrap_per_account_scoped() -> None:
    """다른 account 의 baseline 은 서로 막지 않는다(계좌별 멱등)."""
    client = FakeTossClient(
        holdings=[TossHolding(symbol="AAPL", quantity=3, average_purchase_price=100)]
    )
    service, store, _ = _make_service(client)
    await service.bootstrap("7")
    assert service.has_baseline("9") is False
    await service.bootstrap("9")  # 다른 계좌 → 허용
    assert len(store["txns"]) == 2


# ── 증분 동기화 ───────────────────────────────────────────────────────────────


async def test_incremental_inserts_fills_sorted_and_updates_last_sync() -> None:
    # 페이지에 정렬 뒤섞인 두 체결 — filledAt 오름차순으로 삽입돼야 한다.
    later = _order("ord-2", "BUY", "AAPL", 2, 190.0, filled_at=_dt(26, 10))
    earlier = _order("ord-1", "BUY", "AAPL", 1, 180.0, filled_at=_dt(25, 9))
    client = FakeTossClient(
        pages={None: TossOrderPage(orders=[later, earlier], next_cursor=None)}
    )
    service, store, sync_box = _make_service(client)

    result = await service.incremental("7")

    assert result.mode == "incremental"
    assert result.added == 2
    ids = [t.external_id for t in store["txns"]]
    assert ids == ["ord-1", "ord-2"]  # filledAt 오름차순
    t0 = store["txns"][0]
    assert t0.source == "toss"
    assert t0.price == 180.0
    assert t0.date == "2026-03-25"
    # last_sync 는 본 체결의 최대 filledAt 으로 전진.
    assert sync_box["v"] == _dt(26, 10).isoformat()


async def test_incremental_dedupes_by_order_id() -> None:
    existing = Transaction(
        id="x",
        date="2026-03-25",
        type="buy",
        symbol="AAPL",
        quantity=1,
        price=180.0,
        currency="USD",
        source="toss",
        external_id="ord-1",
    )
    dup = _order("ord-1", "BUY", "AAPL", 1, 180.0, filled_at=_dt(25))
    fresh = _order("ord-2", "BUY", "AAPL", 2, 190.0, filled_at=_dt(26))
    client = FakeTossClient(
        pages={None: TossOrderPage(orders=[dup, fresh], next_cursor=None)}
    )
    service, store, _ = _make_service(client, initial=[existing])

    result = await service.incremental("7")

    assert result.added == 1  # ord-1 은 중복 스킵
    ids = [t.external_id for t in store["txns"]]
    assert ids == ["ord-1", "ord-2"]


async def test_incremental_traverses_cursor_pages() -> None:
    p1 = _order("ord-1", "BUY", "AAPL", 1, 100.0, filled_at=_dt(25))
    p2 = _order("ord-2", "BUY", "AAPL", 1, 110.0, filled_at=_dt(26))
    client = FakeTossClient(
        pages={
            None: TossOrderPage(orders=[p1], next_cursor="c1"),
            "c1": TossOrderPage(orders=[p2], next_cursor=None),
        }
    )
    service, _, _ = _make_service(client, last_sync="2026-03-01")

    result = await service.incremental("7")

    assert result.added == 2
    # 첫 요청은 from_=last_sync·cursor=None, 다음은 cursor=c1.
    assert client.order_calls == [("2026-03-01", None), ("2026-03-01", "c1")]


async def test_incremental_skips_unfilled_and_counts_unpriced() -> None:
    unfilled = _order("ord-0", "BUY", "AAPL", 0, 100.0, filled_at=_dt(24))
    unpriced = _order("ord-1", "BUY", "AAPL", 5, None, filled_at=_dt(25))
    good = _order("ord-2", "BUY", "AAPL", 2, 190.0, filled_at=_dt(26))
    client = FakeTossClient(
        pages={None: TossOrderPage(orders=[unfilled, unpriced, good], next_cursor=None)}
    )
    service, store, _ = _make_service(client)

    result = await service.incremental("7")

    assert result.added == 1  # good 만
    assert result.skipped_unpriced == 1  # 체결됐으나 체결가 없음(가짜값 금지)
    assert [t.external_id for t in store["txns"]] == ["ord-2"]


async def test_incremental_records_fee_and_tax() -> None:
    order = _order(
        "ord-1", "BUY", "AAPL", 2, 190.0, filled_at=_dt(25), commission=0.1, tax=0.05
    )
    client = FakeTossClient(
        pages={None: TossOrderPage(orders=[order], next_cursor=None)}
    )
    service, store, _ = _make_service(client)
    await service.incremental("7")
    t = store["txns"][0]
    assert t.fee == 0.1
    assert t.tax == 0.05


# ── 초과 매도 정책(★) ─────────────────────────────────────────────────────────


async def test_oversell_recorded_not_rejected_and_fold_clamps() -> None:
    """토스가 사실의 원천 — 파생 보유 초과 SELL 도 기록한다(거부 아님).

    baseline 10 주 뒤 SELL 12 주가 오면: 거래는 그대로 저장되고, fold 는
    ``min(12,10)`` 로 클램프해 수량이 음수로 가거나 예외를 내지 않는다.
    """
    baseline = Transaction(
        id="b",
        date=None,
        type="buy",
        symbol="AAPL",
        quantity=10,
        price=100.0,
        currency="USD",
        source="toss-baseline",
        external_id="baseline:7:AAPL",
    )
    oversell = _order("ord-9", "SELL", "AAPL", 12, 120.0, filled_at=_dt(26))
    client = FakeTossClient(
        pages={None: TossOrderPage(orders=[oversell], next_cursor=None)}
    )
    service, store, _ = _make_service(client, initial=[baseline])

    result = await service.incremental("7")

    assert result.added == 1  # 거부하지 않고 기록
    sell = next(t for t in store["txns"] if t.external_id == "ord-9")
    assert sell.type == "sell"
    assert sell.quantity == 12.0
    # fold: 초과분은 0 으로 클램프 — 음수 수량·예외 없음.
    holdings = derive_holdings(store["txns"])
    assert all(h.quantity >= 0 for h in holdings)
    assert not any(h.symbol == "AAPL" for h in holdings)  # 전량 청산(0)


# ── 드리프트 검증 ─────────────────────────────────────────────────────────────


async def test_drift_check_detects_mismatch() -> None:
    baseline = Transaction(
        id="b",
        date=None,
        type="buy",
        symbol="005930",
        quantity=10,
        price=70000,
        currency="KRW",
        source="toss-baseline",
        external_id="baseline:7:005930",
    )
    # 토스 실잔고는 12 주 — 동기화 밖 거래 2 주 존재(드리프트).
    client = FakeTossClient(
        holdings=[
            TossHolding(symbol="005930", quantity=12, average_purchase_price=70000)
        ]
    )
    service, _, _ = _make_service(client, initial=[baseline])

    warnings = await service.drift_check("7")

    assert len(warnings) == 1
    w = warnings[0]
    assert w.symbol == "005930"
    assert w.app_qty == 10.0
    assert w.toss_qty == 12.0


async def test_drift_check_clean_when_matching() -> None:
    baseline = Transaction(
        id="b",
        date=None,
        type="buy",
        symbol="005930",
        quantity=10,
        price=70000,
        currency="KRW",
        source="toss-baseline",
        external_id="baseline:7:005930",
    )
    client = FakeTossClient(
        holdings=[
            TossHolding(symbol="005930", quantity=10, average_purchase_price=70000)
        ]
    )
    service, _, _ = _make_service(client, initial=[baseline])
    assert await service.drift_check("7") == []


async def test_drift_check_ignores_pure_manual_holdings() -> None:
    """토스와 무관한 순수 수동 보유(다른 브로커)는 드리프트로 보지 않는다."""
    manual = Transaction(
        id="m",
        date="2026-01-01",
        type="buy",
        symbol="QQQM",
        quantity=5,
        price=150.0,
        currency="USD",
        source="manual",
    )
    client = FakeTossClient(holdings=[])  # 토스엔 QQQM 없음
    service, _, _ = _make_service(client, initial=[manual])
    assert await service.drift_check("7") == []
