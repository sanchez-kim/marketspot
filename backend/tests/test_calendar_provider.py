"""다가오는 일정 파싱 테스트 (네트워크 없음)."""

from __future__ import annotations

from datetime import date

from app.providers.calendar_provider import parse_calendar, upcoming

# 실제 yfinance calendar 형태(AAPL, 2026-06-09 기준 녹화). 날짜는 ISO 문자열.
_AAPL_CAL = {
    "Dividend Date": "2026-05-14",
    "Ex-Dividend Date": "2026-05-11",
    "Earnings Date": ["2026-07-31"],
}


def test_parse_extracts_earnings_and_exdividend() -> None:
    events = parse_calendar("AAPL", _AAPL_CAL)
    by_type = {e.type: e for e in events}
    assert by_type["earnings"].date == date(2026, 7, 31)
    assert by_type["exDividend"].date == date(2026, 5, 11)
    assert by_type["earnings"].symbol == "AAPL"


def test_parse_empty_for_etf_no_calendar() -> None:
    assert parse_calendar("VOO", {}) == []


def test_parse_handles_date_object_and_missing() -> None:
    cal = {"Earnings Date": [date(2026, 9, 1)]}  # date 객체도 처리
    events = parse_calendar("X", cal)
    assert len(events) == 1
    assert events[0].date == date(2026, 9, 1)


def test_upcoming_filters_past_and_sorts() -> None:
    events = parse_calendar("AAPL", _AAPL_CAL)
    # 오늘=2026-06-01 → 5/11 지남(제외), 7/31 남음
    result = upcoming(events, date(2026, 6, 1), 6)
    assert [e.date for e in result] == [date(2026, 7, 31)]
    # 오늘=2026-05-01 → 둘 다 미래, 날짜순
    result2 = upcoming(events, date(2026, 5, 1), 6)
    assert [e.date for e in result2] == [date(2026, 5, 11), date(2026, 7, 31)]


def test_upcoming_respects_limit() -> None:
    events = parse_calendar("AAPL", _AAPL_CAL)
    assert len(upcoming(events, date(2026, 1, 1), 1)) == 1
