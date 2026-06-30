from datetime import UTC, datetime

from app.models import DataEnvelope, DataStatus, Quote
from app.providers.last_good import LastGoodStore


def _quote_env(status: DataStatus) -> DataEnvelope[Quote]:
    return DataEnvelope.ok(
        Quote(symbol="AAPL", price=100.0, change=1.0, change_pct=1.0, currency="USD"),
        source="yfinance",
        status=status,
        as_of=datetime(2026, 6, 30, tzinfo=UTC),
        delay_minutes=15,
    )


def test_remembers_and_serves_within_cap_restamped_stale() -> None:
    store = LastGoodStore()
    store.remember(("quote", "AAPL"), _quote_env(DataStatus.DELAYED), now=100.0)
    served = store.serve_stale(("quote", "AAPL"), now=200.0, max_age_s=3600.0)
    assert served is not None
    assert served.status is DataStatus.STALE
    assert served.data is not None and served.data.price == 100.0
    assert served.as_of == datetime(2026, 6, 30, tzinfo=UTC)  # 원본 보존
    assert served.delay_minutes == 15  # 과소표기 방지: 지연 보존
    assert served.source == "yfinance"
    assert served.message is not None and "실시간 조회 실패" in served.message


def test_does_not_serve_past_cap() -> None:
    store = LastGoodStore()
    store.remember(("quote", "AAPL"), _quote_env(DataStatus.DELAYED), now=0.0)
    assert store.serve_stale(("quote", "AAPL"), now=100000.0, max_age_s=3600.0) is None


def test_unknown_key_returns_none() -> None:
    store = LastGoodStore()
    assert store.serve_stale(("quote", "TSLA"), now=1.0, max_age_s=3600.0) is None


def test_does_not_remember_failure_statuses() -> None:
    store = LastGoodStore()
    store.remember(
        ("quote", "AAPL"),
        DataEnvelope[Quote].empty(source="yfinance", status=DataStatus.ERROR),
        now=1.0,
    )
    assert store.serve_stale(("quote", "AAPL"), now=2.0, max_age_s=3600.0) is None


def test_does_not_mutate_original() -> None:
    store = LastGoodStore()
    original = _quote_env(DataStatus.DELAYED)
    store.remember(("quote", "AAPL"), original, now=1.0)
    store.serve_stale(("quote", "AAPL"), now=2.0, max_age_s=3600.0)
    assert original.status is DataStatus.DELAYED  # 원본 불변


def test_lru_eviction_drops_oldest() -> None:
    store = LastGoodStore(max_entries=2)
    store.remember(("quote", "A"), _quote_env(DataStatus.DELAYED), now=1.0)
    store.remember(("quote", "B"), _quote_env(DataStatus.DELAYED), now=2.0)
    store.remember(("quote", "C"), _quote_env(DataStatus.DELAYED), now=3.0)  # A 축출
    assert store.serve_stale(("quote", "A"), now=4.0, max_age_s=3600.0) is None
    assert store.serve_stale(("quote", "B"), now=4.0, max_age_s=3600.0) is not None
