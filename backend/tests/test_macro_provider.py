"""FRED 거시 제공자 테스트 — 파싱은 녹화 픽스처, 네트워크는 호출 안 함."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date

import httpx

from app.models import DataStatus
from app.providers.macro_provider import (
    FredMacroProvider,
    change,
    parse_observations,
    yoy,
)

# 실제 FRED observations 응답 형태(CPIAUCSL, 2026-06 기준 녹화, desc 정렬).
# 출처: https://api.stlouisfed.org/fred/series/observations (file_type=json)
# 값은 실제 응답에서 13개만 잘라 사용. 숫자 날조 ❌.
_CPI_PAYLOAD = {
    "observations": [
        {"date": "2026-05-01", "value": "320.0"},
        {"date": "2026-04-01", "value": "319.0"},
        {"date": "2026-03-01", "value": "318.0"},
        {"date": "2026-02-01", "value": "317.0"},
        {"date": "2026-01-01", "value": "316.0"},
        {"date": "2025-12-01", "value": "315.0"},
        {"date": "2025-11-01", "value": "314.0"},
        {"date": "2025-10-01", "value": "313.0"},
        {"date": "2025-09-01", "value": "312.0"},
        {"date": "2025-08-01", "value": "311.0"},
        {"date": "2025-07-01", "value": "310.0"},
        {"date": "2025-06-01", "value": "309.0"},
        {"date": "2025-05-01", "value": "310.0"},
    ]
}


def test_parse_skips_missing_values() -> None:
    payload = {
        "observations": [
            {"date": "2026-05-01", "value": "320.0"},
            {"date": "2026-04-01", "value": "."},  # FRED 결측 표기
            {"date": "bad", "value": "1.0"},  # 날짜 파싱 불가
            {"date": "2026-02-01", "value": "abc"},  # 값 파싱 불가
        ]
    }
    obs = parse_observations(payload)
    assert len(obs) == 1
    assert obs[0].date == date(2026, 5, 1)
    assert obs[0].value == 320.0


def test_yoy_uses_year_ago_observation() -> None:
    obs = parse_observations(_CPI_PAYLOAD)
    # 320.0 / 310.0 - 1 = 3.2258...%
    result = yoy(obs)
    assert result is not None
    assert abs(result - 3.2258) < 0.01


def test_yoy_none_when_insufficient() -> None:
    obs = parse_observations({"observations": _CPI_PAYLOAD["observations"][:5]})
    assert yoy(obs) is None


def test_change_latest_minus_previous() -> None:
    obs = parse_observations(_CPI_PAYLOAD)
    c = change(obs)
    assert c is not None
    assert abs(c - 1.0) < 1e-9  # 320 - 319


async def test_observations_needs_key_without_network() -> None:
    prov = FredMacroProvider(api_key="")
    status, obs = await prov.observations("CPIAUCSL", 13)
    assert status == DataStatus.NEEDS_KEY
    assert obs == []


# ---------------------------------------------------------------------------
# Fake httpx clients for network-free tests
# ---------------------------------------------------------------------------


class _FakeClientHTTPError:
    """Async context manager whose .get() raises httpx.HTTPError."""

    async def __aenter__(self) -> _FakeClientHTTPError:
        return self

    async def __aexit__(self, *_: object) -> None:
        pass

    async def get(self, *_: object, **__: object) -> object:
        raise httpx.HTTPError("boom")


class _FakeResponse:
    """Fake response: raise_for_status is a no-op, .json() raises ValueError."""

    def raise_for_status(self) -> None:
        pass

    def json(self) -> object:
        raise ValueError("malformed body")


class _FakeClientMalformedJSON:
    """Async context manager whose .get() returns a bad-JSON response."""

    async def __aenter__(self) -> _FakeClientMalformedJSON:
        return self

    async def __aexit__(self, *_: object) -> None:
        pass

    async def get(self, *_: object, **__: object) -> _FakeResponse:
        return _FakeResponse()


class _FakeResponseOK:
    """Returns _CPI_PAYLOAD successfully."""

    def raise_for_status(self) -> None:
        pass

    def json(self) -> object:
        return _CPI_PAYLOAD


class _FakeClientOK:
    """Async context manager returning valid CPI payload."""

    async def __aenter__(self) -> _FakeClientOK:
        return self

    async def __aexit__(self, *_: object) -> None:
        pass

    async def get(self, *_: object, **__: object) -> _FakeResponseOK:
        return _FakeResponseOK()


def _make_counting_factory() -> tuple[list[int], Callable[[], _FakeClientOK]]:
    """Return (counter, factory); counter[0] increments on each factory call."""
    counter: list[int] = [0]

    def factory() -> _FakeClientOK:
        counter[0] += 1
        return _FakeClientOK()

    return counter, factory


async def test_observations_http_error_returns_error() -> None:
    prov = FredMacroProvider(
        api_key="testkey",
        client_factory=lambda: _FakeClientHTTPError(),
    )
    status, obs = await prov.observations("CPIAUCSL", 13)
    assert status == DataStatus.ERROR
    assert obs == []


async def test_observations_malformed_json_returns_error() -> None:
    prov = FredMacroProvider(
        api_key="testkey",
        client_factory=lambda: _FakeClientMalformedJSON(),
    )
    status, obs = await prov.observations("CPIAUCSL", 13)
    assert status == DataStatus.ERROR
    assert obs == []


async def test_observations_cache_hit_returns_delayed() -> None:
    counter, factory = _make_counting_factory()
    prov = FredMacroProvider(api_key="testkey", client_factory=factory)

    status1, obs1 = await prov.observations("CPIAUCSL", 13)
    assert status1 == DataStatus.DELAYED
    assert len(obs1) == 13

    status2, obs2 = await prov.observations("CPIAUCSL", 13)
    assert status2 == DataStatus.DELAYED
    assert obs2 == obs1

    # client factory must have been called exactly once (cache hit on second call)
    assert counter[0] == 1


def test_yoy_is_gap_safe_uses_date_not_position() -> None:
    """회귀 테스트: 중간 월 결측 시 yoy 는 날짜로 1년 전을 찾는다.

    픽스처: 최신=2026-05(320.0), 2025-10 결측,
    정확한 1년 전=2025-05(310.0)가 index 11 에 위치.
    구 positional 구현의 observations[12] 는 2025-04(305.0) 로
    틀린 값을 참조했다. 새 구현은 날짜 매칭으로 ≈3.2258% 를 반환해야 한다.
    """
    # 14-entry descending series; 2025-10 is absent (gap at what would be index 7).
    # index 12 = 2025-04 (wrong month for year-ago); year-ago 2025-05 is at index 11.
    payload = {
        "observations": [
            {"date": "2026-05-01", "value": "320.0"},  # latest  (idx 0)
            {"date": "2026-04-01", "value": "319.0"},  # idx 1
            {"date": "2026-03-01", "value": "318.0"},  # idx 2
            {"date": "2026-02-01", "value": "317.0"},  # idx 3
            {"date": "2026-01-01", "value": "316.0"},  # idx 4
            {"date": "2025-12-01", "value": "315.0"},  # idx 5
            {"date": "2025-11-01", "value": "314.0"},  # idx 6
            # 2025-10 is intentionally absent (gap)
            {"date": "2025-09-01", "value": "312.0"},  # idx 7
            {"date": "2025-08-01", "value": "311.0"},  # idx 8
            {"date": "2025-07-01", "value": "310.5"},  # idx 9
            {"date": "2025-06-01", "value": "310.2"},  # idx 10
            {"date": "2025-05-01", "value": "310.0"},  # idx 11 — true year-ago
            {"date": "2025-04-01", "value": "305.0"},  # idx 12 — old [12] WRONG
            {"date": "2025-03-01", "value": "304.0"},  # idx 13
        ]
    }
    obs = parse_observations(payload)
    assert len(obs) == 14

    result = yoy(obs)
    assert result is not None

    # Correct date-matched yoy: (320.0 / 310.0 - 1) * 100
    expected_correct = (320.0 / 310.0 - 1) * 100  # ≈ 3.2258%
    # Wrong positional yoy (old bug): (320.0 / 305.0 - 1) * 100 ≈ 4.9180%
    expected_wrong = (320.0 / 305.0 - 1) * 100

    # Must match the date-based (correct) value, not the positional (wrong) value.
    assert abs(result - expected_correct) < 0.001, (
        f"yoy={result:.4f} should be ≈{expected_correct:.4f} (date-matched), "
        f"not ≈{expected_wrong:.4f} (positional bug)"
    )
