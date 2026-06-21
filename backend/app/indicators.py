"""보조지표 계산 (순수 함수, 결정적).

서버에서 계산해 차트 응답에 함께 실어 보낸다(DESIGN.md §13). 모든 함수는
입력 리스트와 **동일 길이** 의 리스트를 반환하며, 값이 정의되지 않는 warmup
구간은 ``None`` 으로 둔다(가짜 0 으로 채우지 않음).

외부 의존성 없이 순수 파이썬으로 구현 → 테스트가 결정적이다(CLAUDE.md §1.3).
"""

from __future__ import annotations

import math

from .models import IndicatorSeries


def sma(values: list[float], period: int) -> list[float | None]:
    """단순이동평균."""
    if period <= 0:
        raise ValueError("period 는 1 이상이어야 한다")
    out: list[float | None] = [None] * len(values)
    if len(values) < period:
        return out
    window_sum = sum(values[:period])
    out[period - 1] = window_sum / period
    for i in range(period, len(values)):
        window_sum += values[i] - values[i - period]
        out[i] = window_sum / period
    return out


def ema(values: list[float], period: int) -> list[float | None]:
    """지수이동평균. 시드는 첫 ``period`` 개의 SMA."""
    if period <= 0:
        raise ValueError("period 는 1 이상이어야 한다")
    out: list[float | None] = [None] * len(values)
    if len(values) < period:
        return out
    k = 2 / (period + 1)
    prev = sum(values[:period]) / period
    out[period - 1] = prev
    for i in range(period, len(values)):
        prev = values[i] * k + prev * (1 - k)
        out[i] = prev
    return out


def _stddev(window: list[float], mean: float) -> float:
    var = sum((x - mean) ** 2 for x in window) / len(window)
    return math.sqrt(var)


def bollinger(
    values: list[float], period: int = 20, mult: float = 2.0
) -> tuple[list[float | None], list[float | None], list[float | None]]:
    """볼린저 밴드 (upper, middle, lower). middle 은 SMA(period)."""
    middle = sma(values, period)
    upper: list[float | None] = [None] * len(values)
    lower: list[float | None] = [None] * len(values)
    for i in range(period - 1, len(values)):
        window = values[i - period + 1 : i + 1]
        m = middle[i]
        assert m is not None  # period 충족 구간이므로 보장됨
        sd = _stddev(window, m)
        upper[i] = m + mult * sd
        lower[i] = m - mult * sd
    return upper, middle, lower


def rsi(values: list[float], period: int = 14) -> list[float | None]:
    """RSI (Wilder smoothing)."""
    out: list[float | None] = [None] * len(values)
    if len(values) <= period:
        return out
    gains = 0.0
    losses = 0.0
    for i in range(1, period + 1):
        delta = values[i] - values[i - 1]
        if delta >= 0:
            gains += delta
        else:
            losses -= delta
    avg_gain = gains / period
    avg_loss = losses / period
    out[period] = _rsi_from(avg_gain, avg_loss)
    for i in range(period + 1, len(values)):
        delta = values[i] - values[i - 1]
        gain = delta if delta > 0 else 0.0
        loss = -delta if delta < 0 else 0.0
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        out[i] = _rsi_from(avg_gain, avg_loss)
    return out


def _rsi_from(avg_gain: float, avg_loss: float) -> float:
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def macd(
    values: list[float],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[list[float | None], list[float | None], list[float | None]]:
    """MACD (macd_line, signal_line, histogram)."""
    fast_ema = ema(values, fast)
    slow_ema = ema(values, slow)
    macd_line: list[float | None] = [
        (f - s) if (f is not None and s is not None) else None
        for f, s in zip(fast_ema, slow_ema, strict=True)
    ]
    # signal = EMA(macd_line) — None 구간을 제외하고 계산 후 원위치로 매핑
    defined = [(i, v) for i, v in enumerate(macd_line) if v is not None]
    signal_line: list[float | None] = [None] * len(values)
    hist: list[float | None] = [None] * len(values)
    if len(defined) >= signal:
        seq = [v for _, v in defined]
        sig_seq = ema(seq, signal)
        for (orig_i, _), sig_v in zip(defined, sig_seq, strict=True):
            signal_line[orig_i] = sig_v
            if sig_v is not None:
                m = macd_line[orig_i]
                assert m is not None
                hist[orig_i] = m - sig_v
    return macd_line, signal_line, hist


def compute_indicators(
    closes: list[float],
    *,
    ma_periods: tuple[int, ...] = (20, 50, 200),
) -> IndicatorSeries:
    """차트용 표준 지표 묶음을 한 번에 계산."""
    ma_map = {str(p): sma(closes, p) for p in ma_periods}
    bb_u, bb_m, bb_l = bollinger(closes)
    macd_line, sig_line, hist = macd(closes)
    return IndicatorSeries(
        ma=ma_map,
        bb_upper=bb_u,
        bb_middle=bb_m,
        bb_lower=bb_l,
        rsi=rsi(closes),
        macd=macd_line,
        macd_signal=sig_line,
        macd_hist=hist,
    )
