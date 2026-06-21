"""TTL 캐시 테스트 — 주입한 가짜 시계로 결정적 검증(sleep 없음)."""

from __future__ import annotations

from app.cache import TTLCache


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def test_set_get_within_ttl() -> None:
    clock = FakeClock()
    cache: TTLCache[str] = TTLCache(clock=clock)
    cache.set("k", "v", ttl_seconds=10)
    assert cache.get("k") == "v"
    clock.now = 9.9
    assert cache.get("k") == "v"


def test_expires_after_ttl() -> None:
    clock = FakeClock()
    cache: TTLCache[str] = TTLCache(clock=clock)
    cache.set("k", "v", ttl_seconds=10)
    clock.now = 10.0
    assert cache.get("k") is None
    assert len(cache) == 0  # 만료 시 제거


def test_missing_key_returns_none() -> None:
    cache: TTLCache[int] = TTLCache()
    assert cache.get("nope") is None


def test_clear() -> None:
    cache: TTLCache[int] = TTLCache()
    cache.set("a", 1, 100)
    cache.set("b", 2, 100)
    assert len(cache) == 2
    cache.clear()
    assert len(cache) == 0
