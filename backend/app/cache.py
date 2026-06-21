"""인메모리 TTL 캐시.

로컬 전용이라 Redis 불필요(DESIGN.md §1). 시간 함수를 주입할 수 있어
테스트가 결정적이다(CLAUDE.md §1.3 — sleep 으로 만료를 기다리지 않는다).
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic, TypeVar

V = TypeVar("V")


@dataclass
class _Entry(Generic[V]):
    value: V
    expires_at: float


class TTLCache(Generic[V]):
    def __init__(self, *, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._store: dict[str, _Entry[V]] = {}

    def get(self, key: str) -> V | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        if self._clock() >= entry.expires_at:
            del self._store[key]
            return None
        return entry.value

    def set(self, key: str, value: V, ttl_seconds: float) -> None:
        self._store[key] = _Entry(value=value, expires_at=self._clock() + ttl_seconds)

    def clear(self) -> None:
        self._store.clear()

    def __len__(self) -> int:
        return len(self._store)
