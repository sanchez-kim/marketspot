"""마지막 정상값(last-good) 보관소.

yfinance 등 단일 공급원이 *일시적으로* 실패할 때(ERROR/RATE_LIMITED), 직전에
성공한 실제 값을 STALE 로 재표기해 돌려준다(가짜 값 생성 ❌, §0). 상한을 넘은
오래된 값은 신선한 척하지 않고 None 을 돌려 실패를 전파한다.

동시성: 이벤트 루프 스레드에서만 접근한다(asyncio.to_thread 내부 금지).
시각(now)은 호출자(레지스트리)가 monotonic 으로 주입한다 — 결정적 테스트.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Any

from ..models import DataEnvelope, DataStatus

StoreKey = tuple[str, ...]

_GOOD = {DataStatus.LIVE, DataStatus.DELAYED, DataStatus.STALE}
_STALE_MESSAGE = "실시간 조회 실패 — 마지막 정상 데이터 기준"


class LastGoodStore:
    def __init__(self, max_entries: int = 256) -> None:
        self._max = max_entries
        self._store: OrderedDict[StoreKey, tuple[DataEnvelope[Any], float]] = (
            OrderedDict()
        )

    def remember(self, key: StoreKey, envelope: DataEnvelope[Any], now: float) -> None:
        if envelope.status not in _GOOD or envelope.data is None:
            return
        self._store[key] = (envelope, now)
        self._store.move_to_end(key)
        while len(self._store) > self._max:
            self._store.popitem(last=False)

    def serve_stale(
        self, key: StoreKey, now: float, max_age_s: float
    ) -> DataEnvelope[Any] | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        envelope, fetched = entry
        if now - fetched > max_age_s:
            return None
        self._store.move_to_end(key)
        # 원본 불변 — copy 후 STALE 로 재표기. as_of/delay_minutes/source 보존.
        return envelope.model_copy(
            update={"status": DataStatus.STALE, "message": _STALE_MESSAGE}
        )
