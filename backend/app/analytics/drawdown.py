"""하락(drawdown) 분석 — 순수 함수, 네트워크/시간 의존 없음.

"안심 레이어"의 핵심 계산. 고점 대비 낙폭과 과거 조정의 **정직한 기저율**을
만든다. 예측하지 않으며, 진행 중인 하락은 회복 통계에서 제외한다(look-ahead
금지). 데이터가 부족하면 그렇게 표기하도록 호출부에 사실만 돌려준다.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ..models import Bar


@dataclass(frozen=True)
class DrawdownEpisode:
    """고점에서 이탈해 저점을 찍고(회복했으면) 이전 고점까지 돌아온 한 구간."""

    start: datetime  # 고점에서 이탈하기 시작한 날
    trough: datetime  # 저점 날
    depth: float  # 저점에서의 낙폭(음수, 예: -0.34)
    recovery: datetime | None  # 이전 고점 회복 날 (None = 아직 진행 중)

    @property
    def ongoing(self) -> bool:
        return self.recovery is None

    @property
    def recovery_days(self) -> int | None:
        if self.recovery is None:
            return None
        return (self.recovery - self.trough).days


@dataclass(frozen=True)
class DrawdownStats:
    episodes: list[DrawdownEpisode]
    current_drawdown: float  # 현재 고점 대비 낙폭(≤ 0)
    peak: float  # 기간 내 최고 종가(running max)
    peak_date: datetime
    worst: float  # 역사상 최저 낙폭(가장 음수)
    span_days: int  # 데이터가 실제로 커버하는 일수


@dataclass(frozen=True)
class BaseRates:
    """현재 낙폭(또는 기준값) '이상으로 깊었던' 과거 조정의 집계."""

    threshold: float  # 기준 낙폭(양수, 예: 0.05)
    comparable_count: int  # 기준 이상으로 깊었던 조정 수
    recovered_count: int  # 그중 회복 완료(진행 중 제외)
    median_recovery_days: int | None
    max_recovery_days: int | None


def analyze_drawdowns(bars: list[Bar]) -> DrawdownStats | None:
    """봉 목록 → 낙폭 통계. 봉이 2개 미만이면 None."""
    if len(bars) < 2:
        return None

    closes = [b.close for b in bars]
    times = [b.time for b in bars]

    episodes: list[DrawdownEpisode] = []
    peak = closes[0]
    peak_date = times[0]
    in_dd = False
    start = times[0]
    trough = closes[0]
    trough_date = times[0]

    for i, c in enumerate(closes):
        if c >= peak:
            if in_dd:  # 이전 고점 회복 → 에피소드 종료
                episodes.append(
                    DrawdownEpisode(start, trough_date, trough / peak - 1, times[i])
                )
                in_dd = False
            peak = c
            peak_date = times[i]
        else:
            if not in_dd:  # 고점에서 이탈 시작
                in_dd = True
                start = times[i]
                trough = c
                trough_date = times[i]
            elif c < trough:  # 저점 갱신
                trough = c
                trough_date = times[i]

    if in_dd:  # 마지막 구간이 아직 진행 중
        episodes.append(DrawdownEpisode(start, trough_date, trough / peak - 1, None))

    current = closes[-1] / peak - 1
    worst = min((e.depth for e in episodes), default=0.0)
    span = (times[-1] - times[0]).days
    return DrawdownStats(
        episodes=episodes,
        current_drawdown=current,
        peak=peak,
        peak_date=peak_date,
        worst=worst,
        span_days=span,
    )


def base_rates(stats: DrawdownStats, threshold: float) -> BaseRates:
    """기준 낙폭(threshold, 양수) 이상 깊었던 과거 조정의 회복 기저율.

    진행 중(ongoing)인 조정은 회복 통계에서 제외한다 — 아직 끝나지 않았으므로
    '회복했다'고 셀 수 없다(정직성).
    """
    comparable = [e for e in stats.episodes if e.depth <= -threshold]
    recovered = [e for e in comparable if not e.ongoing]
    rdays = sorted(e.recovery_days for e in recovered if e.recovery_days is not None)
    median = rdays[len(rdays) // 2] if rdays else None
    longest = rdays[-1] if rdays else None
    return BaseRates(
        threshold=threshold,
        comparable_count=len(comparable),
        recovered_count=len(recovered),
        median_recovery_days=median,
        max_recovery_days=longest,
    )
