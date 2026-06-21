"""보조지표 테스트.

수학적 *성질* 을 검증한다(특정 숫자를 지어내지 않음, CLAUDE.md §1.3):
- 상수 수열의 SMA/EMA 는 그 상수
- 단조증가 수열의 RSI 는 100, 단조감소는 0
- 볼린저 중앙선 == SMA, 상수 수열의 밴드폭 == 0
- 상수 수열의 MACD 는 0
- 출력 길이는 입력과 동일하고 warmup 은 None
"""

from __future__ import annotations

from app.indicators import bollinger, compute_indicators, ema, macd, rsi, sma


def test_sma_length_and_warmup() -> None:
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    out = sma(values, 3)
    assert len(out) == len(values)
    assert out[0] is None and out[1] is None  # warmup
    assert out[2] == 2.0  # (1+2+3)/3
    assert out[3] == 3.0
    assert out[4] == 4.0


def test_sma_of_constant_is_constant() -> None:
    values = [7.0] * 10
    out = sma(values, 4)
    for v in out[3:]:
        assert v == 7.0


def test_sma_shorter_than_period_all_none() -> None:
    assert sma([1.0, 2.0], 5) == [None, None]


def test_ema_of_constant_is_constant() -> None:
    values = [3.0] * 20
    out = ema(values, 5)
    for v in out[4:]:
        assert v is not None
        assert abs(v - 3.0) < 1e-9


def test_bollinger_middle_equals_sma_and_zero_width_on_constant() -> None:
    values = [10.0] * 30
    upper, middle, lower = bollinger(values, period=20)
    assert middle == sma(values, 20)
    # 상수 수열은 표준편차 0 → 밴드폭 0
    assert upper[-1] == 10.0
    assert lower[-1] == 10.0


def test_rsi_monotonic_increasing_is_100() -> None:
    values = [float(i) for i in range(1, 30)]
    out = rsi(values, 14)
    last = out[-1]
    assert last is not None
    assert abs(last - 100.0) < 1e-9


def test_rsi_monotonic_decreasing_is_0() -> None:
    values = [float(i) for i in range(30, 1, -1)]
    out = rsi(values, 14)
    last = out[-1]
    assert last is not None
    assert abs(last - 0.0) < 1e-9


def test_rsi_warmup_is_none() -> None:
    values = [float(i) for i in range(1, 30)]
    out = rsi(values, 14)
    assert all(v is None for v in out[:14])
    assert out[14] is not None


def test_macd_of_constant_is_zero() -> None:
    values = [5.0] * 60
    macd_line, _signal, hist = macd(values)
    # 정의된 구간에서 모두 0
    defined = [v for v in macd_line if v is not None]
    assert defined  # 비어있지 않음
    assert all(abs(v) < 1e-9 for v in defined)
    defined_hist = [v for v in hist if v is not None]
    assert all(abs(v) < 1e-9 for v in defined_hist)


def test_compute_indicators_lengths_match() -> None:
    closes = [float(i % 7) + 1 for i in range(300)]
    ind = compute_indicators(closes)
    n = len(closes)
    assert len(ind.rsi) == n
    assert len(ind.bb_upper) == n
    assert len(ind.macd) == n
    for series in ind.ma.values():
        assert len(series) == n
    assert set(ind.ma.keys()) == {"20", "50", "200"}
