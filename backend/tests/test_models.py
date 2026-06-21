"""DataEnvelope 모델/직렬화 테스트."""

from __future__ import annotations

import pytest

from app.models import DataEnvelope, DataStatus, Quote


def test_envelope_ok_carries_metadata() -> None:
    q = Quote(symbol="AAPL", price=188.35, change=2.6, change_pct=1.42)
    env = DataEnvelope.ok(
        q, source="yfinance", status=DataStatus.DELAYED, delay_minutes=15
    )
    assert env.data is not None
    assert env.status is DataStatus.DELAYED
    assert env.source == "yfinance"
    assert env.delay_minutes == 15


def test_envelope_empty_has_no_data() -> None:
    env = DataEnvelope[Quote].empty(
        source="dart", status=DataStatus.NEEDS_KEY, message="키 필요"
    )
    assert env.data is None
    assert env.status is DataStatus.NEEDS_KEY
    assert env.message == "키 필요"


def test_empty_rejects_data_present_status() -> None:
    # 데이터가 있는 상태(LIVE/DELAYED)로 empty 를 만들면 안 됨
    with pytest.raises(ValueError):
        DataEnvelope[Quote].empty(source="x", status=DataStatus.LIVE)


def test_serializes_to_camel_case() -> None:
    q = Quote(symbol="AAPL", price=188.35, change_pct=1.42)
    env = DataEnvelope.ok(q, source="yfinance", delay_minutes=15)
    dumped = env.model_dump(by_alias=True)
    assert "delayMinutes" in dumped
    assert dumped["data"]["changePct"] == 1.42
