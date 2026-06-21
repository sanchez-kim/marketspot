"""하락 분석 순수 함수 테스트 (네트워크/시간 무).

합성 가격경로로 *알려진 정답*을 검증한다 — 에피소드 검출, 낙폭 깊이, 회복일,
진행 중 제외, 기저율. 숫자를 지어내지 않고 구성한 경로의 수학적 사실만 본다.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

import pytest

from app.analytics.drawdown import analyze_drawdowns, base_rates
from app.models import Bar


def _bars(closes: Sequence[float], step_days: int = 1) -> list[Bar]:
    base = datetime(2020, 1, 1, tzinfo=UTC)
    return [
        Bar(
            time=base + timedelta(days=i * step_days),
            open=c,
            high=c,
            low=c,
            close=c,
            volume=1.0,
        )
        for i, c in enumerate(closes)
    ]


# 고점110에서 88까지(-20%) 빠졌다 회복 후 새 고점120
_RECOVER = [100, 110, 99, 88, 105, 110, 120]


def test_detects_single_drawdown_and_recovery() -> None:
    stats = analyze_drawdowns(_bars(_RECOVER))
    assert stats is not None
    assert len(stats.episodes) == 1
    ep = stats.episodes[0]
    assert ep.depth == pytest.approx(-0.20)  # 88/110 - 1
    assert not ep.ongoing
    assert ep.recovery_days == 2  # 저점(i=3) → 회복(i=5)


def test_current_drawdown_zero_at_new_peak() -> None:
    stats = analyze_drawdowns(_bars(_RECOVER))
    assert stats is not None
    assert stats.current_drawdown == pytest.approx(0.0)
    assert stats.peak == pytest.approx(120)
    assert stats.worst == pytest.approx(-0.20)


def test_current_drawdown_is_non_positive_property() -> None:
    stats = analyze_drawdowns(_bars([100, 90, 120, 110, 130, 100]))
    assert stats is not None
    assert stats.current_drawdown <= 0
    assert stats.peak == pytest.approx(130)  # 기간 내 최고가


def test_ongoing_drawdown_excluded_from_recovered() -> None:
    # 120 고점 후 90까지 빠지고 96에서 끝남(회복 못 함)
    stats = analyze_drawdowns(_bars([100, 120, 110, 90, 96]))
    assert stats is not None
    ep = stats.episodes[-1]
    assert ep.ongoing
    assert stats.current_drawdown == pytest.approx(96 / 120 - 1)  # -20%
    rates = base_rates(stats, 0.20)
    assert rates.comparable_count == 1  # -25% 저점은 기준 충족
    assert rates.recovered_count == 0  # 단 진행 중이라 회복 통계 제외
    assert rates.median_recovery_days is None


def test_base_rates_threshold_filters() -> None:
    stats = analyze_drawdowns(_bars(_RECOVER))
    assert stats is not None
    # -20% 조정 하나뿐 → 5% 기준은 1건, 30% 기준은 0건
    assert base_rates(stats, 0.05).comparable_count == 1
    assert base_rates(stats, 0.05).recovered_count == 1
    assert base_rates(stats, 0.30).comparable_count == 0


def test_too_short_returns_none() -> None:
    assert analyze_drawdowns(_bars([100])) is None
    assert analyze_drawdowns([]) is None
