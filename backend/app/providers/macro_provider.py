"""FRED(미 세인트루이스 연준) 거시 시계열 제공자.

기준금리(DFF)·CPI(CPIAUCSL) 등 공식 거시 데이터를 가져온다. API 키가 없으면
``NEEDS_KEY`` 로 정직하게 표기한다(가짜 ❌). HTTP 클라이언트는 주입 가능해
테스트에서 네트워크 없이 검증한다.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from typing import Any, Protocol, runtime_checkable

import httpx

from ..cache import TTLCache
from ..models import DataStatus

_FRED_URL = "https://api.stlouisfed.org/fred/series/observations"
_TTL = 6 * 3600.0  # 6시간 (거시 지표는 천천히 변함)


@runtime_checkable
class _HttpClient(Protocol):
    """덕 타이핑: async context manager + GET 메서드."""

    async def __aenter__(self) -> _HttpClient: ...

    async def __aexit__(self, *args: Any) -> None: ...

    async def get(self, url: str, *, params: Any = None) -> Any: ...


@dataclass(frozen=True)
class Observation:
    date: date
    value: float


def parse_observations(payload: Mapping[str, object]) -> list[Observation]:
    """FRED observations dict → 관측치 목록(순수 함수).

    결측 표기(``"."``)·빈 값·파싱 불가 항목은 정직하게 제외한다.
    """
    raw = payload.get("observations")
    out: list[Observation] = []
    if not isinstance(raw, Sequence):
        return out
    for o in raw:
        if not isinstance(o, Mapping):
            continue
        d = o.get("date")
        v = o.get("value")
        if not isinstance(d, str) or not isinstance(v, str):
            continue
        if v in ("", "."):
            continue
        try:
            parsed_date = date.fromisoformat(d[:10])
            parsed_value = float(v)
        except ValueError:
            continue
        out.append(Observation(parsed_date, parsed_value))
    return out


def yoy(observations: Sequence[Observation]) -> float | None:
    """전년 동월 대비 변화율(%). desc 정렬 가정: obs[0] 최신, obs[12] 1년 전."""
    if len(observations) < 13:
        return None
    cur = observations[0].value
    prev = observations[12].value
    if prev == 0:
        return None
    return (cur / prev - 1) * 100


def change(observations: Sequence[Observation]) -> float | None:
    """최신값 - 직전값(방향). 관측치가 2개 미만이면 None."""
    if len(observations) < 2:
        return None
    return observations[0].value - observations[1].value


class FredMacroProvider:
    name = "fred"

    def __init__(
        self,
        api_key: str,
        *,
        clock: Callable[[], float] = time.monotonic,
        client_factory: Callable[[], _HttpClient] | None = None,
    ) -> None:
        self._key = api_key
        self._cache: TTLCache[list[Observation]] = TTLCache(clock=clock)
        self._client_factory = client_factory or (lambda: httpx.AsyncClient(timeout=10))

    async def observations(
        self, series_id: str, limit: int
    ) -> tuple[DataStatus, list[Observation]]:
        if not self._key:
            return DataStatus.NEEDS_KEY, []

        cache_key = f"{series_id}:{limit}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return DataStatus.DELAYED, cached

        params = {
            "series_id": series_id,
            "api_key": self._key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": str(limit),
        }
        try:
            async with self._client_factory() as client:
                resp = await client.get(_FRED_URL, params=params)
                resp.raise_for_status()
                payload = resp.json()
        # 네트워크/HTTP 오류 또는 malformed body → 상태로 변환(가짜 ❌)
        except (httpx.HTTPError, ValueError):
            return DataStatus.ERROR, []

        obs = parse_observations(payload) if isinstance(payload, Mapping) else []
        if not obs:
            return DataStatus.NO_DATA, []
        self._cache.set(cache_key, obs, _TTL)
        return DataStatus.DELAYED, obs
