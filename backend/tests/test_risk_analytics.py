"""포트폴리오 리스크 순수 분석 테스트 (네트워크/시간 없음)."""

from __future__ import annotations

from datetime import UTC, datetime

from app.analytics.risk import (
    aligned_closes,
    herfindahl,
    pct_returns,
    pearson,
)
from app.models import Bar


def _bars(closes: list[float], start_day: int = 1) -> list[Bar]:
    out: list[Bar] = []
    for i, c in enumerate(closes):
        t = datetime(2026, 1, start_day + i, tzinfo=UTC)
        out.append(Bar(time=t, open=c, high=c, low=c, close=c, volume=1.0))
    return out


def test_herfindahl_equal_weights() -> None:
    # 4종목 균등(25%씩) → HHI = 4 * 0.25^2 = 0.25
    assert herfindahl([0.25, 0.25, 0.25, 0.25]) == 0.25


def test_herfindahl_normalizes_and_ignores_nonpositive() -> None:
    # 합이 1이 아니어도 정규화: [50,50] → 0.5; 0/음수는 무시
    assert herfindahl([50.0, 50.0, 0.0]) == 0.5


def test_herfindahl_empty_is_zero() -> None:
    assert herfindahl([]) == 0.0


def test_pct_returns_basic() -> None:
    assert pct_returns([100.0, 110.0, 99.0]) == [0.1, -0.1]


def test_pct_returns_skips_zero_prev() -> None:
    assert pct_returns([0.0, 5.0, 10.0]) == [1.0]


def test_pearson_perfect_positive() -> None:
    r = pearson([1.0, 2.0, 3.0, 4.0], [2.0, 4.0, 6.0, 8.0])
    assert r is not None
    assert abs(r - 1.0) < 1e-9


def test_pearson_perfect_negative() -> None:
    r = pearson([1.0, 2.0, 3.0], [3.0, 2.0, 1.0])
    assert r is not None
    assert abs(r - (-1.0)) < 1e-9


def test_pearson_none_when_zero_variance() -> None:
    assert pearson([5.0, 5.0, 5.0], [1.0, 2.0, 3.0]) is None


def test_pearson_none_when_too_short() -> None:
    assert pearson([1.0], [2.0]) is None


def test_aligned_closes_intersects_dates_and_preserves_order() -> None:
    series = {
        "AAA": _bars([10.0, 11.0, 12.0], start_day=1),  # 1,2,3일
        "BBB": _bars([20.0, 21.0], start_day=2),  # 2,3일
    }
    symbols, matrix = aligned_closes(series)
    assert symbols == ["AAA", "BBB"]
    # 공통 날짜 = 2,3일 → AAA[11,12], BBB[20,21]
    assert matrix == [[11.0, 12.0], [20.0, 21.0]]


def test_aligned_closes_skips_empty_series() -> None:
    series = {"AAA": _bars([10.0, 11.0]), "BBB": []}
    symbols, matrix = aligned_closes(series)
    assert symbols == ["AAA"]
    assert matrix == [[10.0, 11.0]]
