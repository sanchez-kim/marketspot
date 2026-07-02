"""토스증권 잔고·거래 동기화 서비스 (Phase A, 스펙 §3.3).

기존 Transaction 모델(이동평균 fold → 평단·실현손익)이 **소스 오브 트루스**를
유지하고, 토스는 *거래를 공급*하는 소스다. 두 가지 흐름:

부트스트랩(최초 연동)
    ``holdings`` 스냅샷 → 종목별 "기초 보유" Transaction(BUY, date=None,
    price=averagePurchasePrice, source="toss-baseline"). 주문이력 소급 한도가
    미확인이라 과거 전체 재구성 대신 스냅샷 기점을 쓴다(§0 — 지어내지 않음).
    같은 account 의 baseline 이 이미 있으면 재실행을 거부한다(멱등).

증분 동기화
    ``orders?status=CLOSED&from=last_sync`` 커서 전체 순회 → 체결분만
    Transaction(source="toss", external_id=orderId). **orderId 멱등**(중복
    스킵), filledAt 오름차순 삽입, 완료 시 last_sync 갱신.

    ★ 매도 정합성: 토스가 브로커(사실의 원천)이므로 파생 보유를 초과하는
    SELL 도 거부하지 않고 그대로 기록한다(라우터의 초과매도 가드는 *수동 입력*
    보호용 — 여기서는 스토어에 직접 삽입해 우회한다). ``analytics.holdings._fold``
    는 SELL 을 ``min(t.quantity, h.quantity)`` 로 클램프해 수량이 음수로 가지
    않고 예외도 없다 → 초과분은 fold 에서 무시되고, 그 결과 불일치는
    ``drift_check`` 로 정직하게 드러난다(숨기지 않음).

드리프트 검증
    파생 포지션 수량 vs 토스 holdings 실수량 대조 → ``DriftWarning`` 목록.
    동기화 밖 거래(다른 도구·소급 한도 밖)를 숨기지 않고 응답에 담는다.

이 서비스는 **에러를 삼키지 않는다**(§0) — TossClient/HTTP 실패는 예외로
전파되며, DataStatus 변환은 라우터의 책임이다.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from ..analytics.holdings import currency_of, derive_holdings
from ..config import get_toss_last_sync, set_toss_last_sync
from ..models import DriftWarning, TossSyncResult, Transaction
from ..providers.toss_client import TossClient, TossOrder
from ..transaction_store import load_transactions, save_transactions

# 수량 비교 허용 오차(부동소수·소수점 체결 대비). 이보다 작은 차이는 일치로 본다.
_QTY_EPS = 1e-6
# filledAt/orderedAt 가 모두 없을 때 정렬용 하한(tz-aware datetime — 비교 가능).
_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)

# 토스에서 유입된 거래로 간주하는 source 들(드리프트 범위 판정용).
_TOSS_SOURCES = frozenset({"toss", "toss-baseline"})


class TossSyncError(RuntimeError):
    """동기화 도메인 오류(예: 이미 부트스트랩된 계좌 재실행)."""


LoadTxns = Callable[[], list[Transaction]]
SaveTxns = Callable[[list[Transaction]], None]
ClientFactory = Callable[[], TossClient]


class TossSyncService:
    """토스 연동 동기화 오케스트레이터.

    Parameters
    ----------
    client_factory:
        호출마다 새 ``TossClient`` 를 만드는 팩토리(키 캡처는 deps 팩토리 몫).
        한 메서드는 자기 클라이언트를 만들고 끝에 ``aclose`` 한다 — 토큰 단일
        관리자를 메서드 단위로 격리(1토큰 제약 안전).
    load_txns / save_txns:
        거래 저장소 접근(테스트에서 인메모리로 주입).
    get_last_sync / set_last_sync:
        마지막 증분 동기화 시각 IO(테스트에서 주입).
    """

    def __init__(
        self,
        client_factory: ClientFactory,
        *,
        load_txns: LoadTxns = load_transactions,
        save_txns: SaveTxns = save_transactions,
        get_last_sync: Callable[[], str] = get_toss_last_sync,
        set_last_sync: Callable[[str], None] = set_toss_last_sync,
    ) -> None:
        self._client_factory = client_factory
        self._load_txns = load_txns
        self._save_txns = save_txns
        self._get_last_sync = get_last_sync
        self._set_last_sync = set_last_sync

    # ── 상태 판정 ─────────────────────────────────────────────────────────────

    def has_baseline(self, account_seq: str) -> bool:
        """해당 계좌의 부트스트랩(기초 보유)이 이미 존재하는가."""
        prefix = _baseline_prefix(account_seq)
        return any(
            t.external_id is not None and t.external_id.startswith(prefix)
            for t in self._load_txns()
        )

    # ── 부트스트랩(최초 연동) ─────────────────────────────────────────────────

    async def bootstrap(self, account_seq: str) -> TossSyncResult:
        """holdings 스냅샷을 "기초 보유" 거래로 생성(멱등 — 이미 있으면 거부)."""
        txns = self._load_txns()
        prefix = _baseline_prefix(account_seq)
        if any(
            t.external_id is not None and t.external_id.startswith(prefix) for t in txns
        ):
            raise TossSyncError(f"계좌 {account_seq} 는 이미 부트스트랩됐습니다")

        client = self._client_factory()
        try:
            holdings = await client.get_holdings(account_seq)
        finally:
            await client.aclose()

        new: list[Transaction] = []
        for h in holdings:
            if h.quantity <= 0:
                continue
            symbol = h.symbol.upper()
            new.append(
                Transaction(
                    id=uuid.uuid4().hex,
                    date=None,  # 스냅샷 기점 — "기초 보유"(체결일 미상)
                    type="buy",
                    symbol=symbol,
                    quantity=h.quantity,
                    price=h.average_purchase_price,
                    currency=h.currency or currency_of(symbol),
                    source="toss-baseline",
                    external_id=f"{prefix}{symbol}",
                )
            )
        if new:
            self._save_txns([*txns, *new])
        return TossSyncResult(mode="bootstrap", added=len(new))

    # ── 증분 동기화 ───────────────────────────────────────────────────────────

    async def incremental(self, account_seq: str) -> TossSyncResult:
        """last_sync 이후 체결 주문을 멱등하게 유입(정렬 삽입 + last_sync 갱신)."""
        txns = self._load_txns()
        existing_ids = {t.external_id for t in txns if t.external_id is not None}
        last_sync = self._get_last_sync() or None

        orders = await self._fetch_closed_orders(account_seq, last_sync)

        # 체결분만(체결수량>0). 체결가가 없으면 가짜값을 만들지 않고 스킵(§0).
        filled: list[TossOrder] = []
        skipped_unpriced = 0
        for order in orders:
            ex = order.execution
            if ex is None or ex.filled_quantity is None or ex.filled_quantity <= 0:
                continue
            if ex.average_filled_price is None:
                skipped_unpriced += 1
                continue
            filled.append(order)

        # 신규(중복 orderId 스킵)만 filledAt 오름차순으로 삽입.
        fresh = [o for o in filled if o.order_id not in existing_ids]
        fresh.sort(key=_sort_key)
        new_txns = [_order_to_txn(o, account_seq) for o in fresh]
        if new_txns:
            self._save_txns([*txns, *new_txns])

        # last_sync 는 이번에 *본* 모든 체결의 최대 filledAt 으로 전진(중복 포함).
        # 그래야 전부 중복이어도 다음 폴링 창이 앞으로 이동한다(멱등·효율).
        max_filled = _max_filled_at(filled)
        if max_filled is not None:
            self._set_last_sync(max_filled.isoformat())

        return TossSyncResult(
            mode="incremental",
            added=len(new_txns),
            skipped_unpriced=skipped_unpriced,
        )

    async def _fetch_closed_orders(
        self, account_seq: str, from_: str | None
    ) -> list[TossOrder]:
        """커서 전체 순회로 CLOSED 주문을 모은다(next_cursor None → 마지막)."""
        client = self._client_factory()
        collected: list[TossOrder] = []
        try:
            cursor: str | None = None
            while True:
                page = await client.get_closed_orders(
                    account_seq, from_=from_, cursor=cursor
                )
                collected.extend(page.orders)
                if page.next_cursor is None:
                    break
                cursor = page.next_cursor
        finally:
            await client.aclose()
        return collected

    # ── 드리프트 검증 ─────────────────────────────────────────────────────────

    async def drift_check(self, account_seq: str) -> list[DriftWarning]:
        """파생 포지션 vs 토스 실잔고 대조(토스 유입 종목 범위).

        순수 수동 보유(다른 브로커 등, toss 소스 아님)는 토스 잔고에 없어도
        드리프트가 아니므로 범위에서 제외한다 — 토스에 있거나 토스에서 유입된
        종목만 대조한다(잘못된 경고 방지).
        """
        txns = self._load_txns()
        derived = {h.symbol.upper(): h.quantity for h in derive_holdings(txns)}
        toss_symbols = {t.symbol.upper() for t in txns if t.source in _TOSS_SOURCES}

        client = self._client_factory()
        try:
            holdings = await client.get_holdings(account_seq)
        finally:
            await client.aclose()
        toss_qty = {h.symbol.upper(): h.quantity for h in holdings}

        warnings: list[DriftWarning] = []
        for symbol in sorted(set(toss_qty) | toss_symbols):
            app_q = derived.get(symbol, 0.0)
            toss_q = toss_qty.get(symbol, 0.0)
            if abs(app_q - toss_q) > _QTY_EPS:
                warnings.append(
                    DriftWarning(symbol=symbol, app_qty=app_q, toss_qty=toss_q)
                )
        return warnings


# ── 헬퍼 ──────────────────────────────────────────────────────────────────────


def _baseline_prefix(account_seq: str) -> str:
    return f"baseline:{account_seq}:"


def _sort_key(order: TossOrder) -> datetime:
    ex = order.execution
    if ex is not None and ex.filled_at is not None:
        return ex.filled_at
    if order.ordered_at is not None:
        return order.ordered_at
    return _EPOCH


def _max_filled_at(orders: list[TossOrder]) -> datetime | None:
    times = [
        o.execution.filled_at
        for o in orders
        if o.execution is not None and o.execution.filled_at is not None
    ]
    return max(times) if times else None


def _order_to_txn(order: TossOrder, account_seq: str) -> Transaction:
    ex = order.execution
    assert ex is not None and ex.filled_quantity is not None  # 호출 전 필터로 보장
    assert ex.average_filled_price is not None
    symbol = order.symbol.upper()
    filled_at = ex.filled_at
    return Transaction(
        id=uuid.uuid4().hex,
        date=filled_at.date().isoformat() if filled_at is not None else None,
        type="buy" if order.side == "BUY" else "sell",
        symbol=symbol,
        quantity=ex.filled_quantity,
        price=ex.average_filled_price,
        currency=order.currency or currency_of(symbol),
        source="toss",
        external_id=order.order_id,
        fee=ex.commission,
        tax=ex.tax,
    )
