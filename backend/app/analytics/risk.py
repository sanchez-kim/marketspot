"""포트폴리오 리스크 분석 — 순수 함수, 네트워크/시간 의존 없음.

집중도(HHI)와 종목 간 상관(분산 효과 신호)을 계산한다. 데이터가 부족하면
None/빈 결과를 돌려주어 호출부가 정직하게 표기하도록 한다(가짜 값 ❌).
"""

from __future__ import annotations

import itertools
from collections.abc import Mapping, Sequence
from math import sqrt

from ..models import Bar


def herfindahl(weight_fractions: Sequence[float]) -> float:
    """허핀달 지수(HHI) = Σ wᵢ². 입력을 양수 합으로 정규화한다.

    0 에 가까울수록 분산, 1 에 가까울수록 한 종목 집중. 빈 입력은 0.
    """
    positives = [w for w in weight_fractions if w > 0]
    total = sum(positives)
    if total <= 0:
        return 0.0
    return sum((w / total) ** 2 for w in positives)


def pct_returns(closes: Sequence[float]) -> list[float]:
    """종가열 → 일간 수익률. 이전 종가가 0 이면 해당 구간은 건너뛴다.

    부동소수점 표현 오차를 제거하기 위해 소수점 10자리로 반올림한다.
    """
    out: list[float] = []
    for prev, cur in itertools.pairwise(closes):
        if prev:
            out.append(round(cur / prev - 1, 10))
    return out


def pearson(a: Sequence[float], b: Sequence[float]) -> float | None:
    """피어슨 상관계수. 겹치는 마지막 n개로 계산. n<2 또는 분산 0 이면 None."""
    n = min(len(a), len(b))
    if n < 2:
        return None
    xa = list(a[-n:])
    xb = list(b[-n:])
    ma = sum(xa) / n
    mb = sum(xb) / n
    cov = sum((x - ma) * (y - mb) for x, y in zip(xa, xb, strict=True))
    va = sum((x - ma) ** 2 for x in xa)
    vb = sum((y - mb) ** 2 for y in xb)
    if va <= 0 or vb <= 0:
        return None
    return cov / sqrt(va * vb)


def _closes_by_date(bars: Sequence[Bar]) -> dict[object, float]:
    return {b.time.date(): b.close for b in bars}


def aligned_closes(
    series: Mapping[str, Sequence[Bar]],
) -> tuple[list[str], list[list[float]]]:
    """공통 날짜(교집합) 기준으로 정렬된 종가 행렬.

    빈 시계열 종목은 제외하고, 나머지의 *공통* 거래일만 사용해 길이를 맞춘다.
    입력(dict) 순서를 보존한다. 종목이 하나면 그 종목의 날짜 전체를 쓴다.
    """
    present = [(s, _closes_by_date(bars)) for s, bars in series.items() if bars]
    if not present:
        return [], []
    common = set.intersection(*(set(m.keys()) for _, m in present))
    dates = sorted(common)  # type: ignore[type-var]
    symbols = [s for s, _ in present]
    matrix = [[m[d] for d in dates] for _, m in present]
    return symbols, matrix
