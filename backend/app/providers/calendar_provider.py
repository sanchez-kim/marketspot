"""다가오는 일정 제공자 (yfinance ``calendar`` — 실적·배당락).

주식은 실적 발표일·배당락일을 준다. ETF 등 일정이 없으면 빈 목록(가짜 ❌).
'놀랄 일 없게' = 안심 + 정보.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, date, datetime

from ..cache import TTLCache
from ..models import CalendarEvent

JsonDict = Mapping[str, object]
_TTL = 6 * 3600.0  # 6시간 (일정은 거의 안 변함)


def _to_date(v: object) -> date | None:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if isinstance(v, str) and v:
        try:
            return date.fromisoformat(v[:10])
        except ValueError:
            return None
    return None


def parse_calendar(symbol: str, cal: JsonDict) -> list[CalendarEvent]:
    """yfinance calendar dict → 이벤트 목록 (순수 함수)."""
    out: list[CalendarEvent] = []
    sym = symbol.upper()

    earnings = cal.get("Earnings Date")
    edate: date | None = None
    if isinstance(earnings, (list, tuple)) and earnings:
        edate = _to_date(earnings[0])
    else:
        edate = _to_date(earnings)
    if edate is not None:
        out.append(CalendarEvent(symbol=sym, type="earnings", date=edate))

    exdiv = _to_date(cal.get("Ex-Dividend Date"))
    if exdiv is not None:
        out.append(CalendarEvent(symbol=sym, type="exDividend", date=exdiv))

    return out


def upcoming(
    events: Sequence[CalendarEvent], today: date, limit: int
) -> list[CalendarEvent]:
    """오늘 이후 일정만 날짜순으로 정렬해 limit 개."""
    future = [e for e in events if e.date >= today]
    future.sort(key=lambda e: e.date)
    return future[:limit]


class YFinanceCalendarProvider:
    name = "yfinance-calendar"

    def __init__(self, *, clock: Callable[[], float] = time.monotonic) -> None:
        self._cache: TTLCache[list[CalendarEvent]] = TTLCache(clock=clock)

    async def _events_for(self, symbol: str) -> list[CalendarEvent]:
        key = symbol.upper()
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        try:
            import yfinance as yf

            # 동기 yfinance → 스레드로 오프로드(이벤트 루프 비차단)
            cal = await asyncio.to_thread(lambda: yf.Ticker(symbol).calendar)
        except Exception:  # noqa: BLE001 - 일정 없으면 빈 목록(가짜 ❌)
            return []
        events = parse_calendar(symbol, cal) if isinstance(cal, Mapping) else []
        self._cache.set(key, events, _TTL)
        return events

    async def get_events(
        self, symbols: list[str], limit: int = 6
    ) -> list[CalendarEvent]:
        uniq = list(dict.fromkeys(s.strip() for s in symbols if s.strip()))
        gathered = await asyncio.gather(*(self._events_for(s) for s in uniq))
        flat = [e for evs in gathered for e in evs]
        return upcoming(flat, datetime.now(UTC).date(), limit)
