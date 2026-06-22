"""yfinance 기반 제공자 (기본, 키 불필요).

야후 파이낸스 비공식 데이터로 미국/한국 종목·지수·환율·원자재를 폭넓게
커버한다. 비공식이라 가끔 깨질 수 있으며, 그럴 때는 가짜 값 대신
``DataStatus.ERROR`` 로 정직하게 표기한다(REQUIREMENTS.md §3).

미국 시세는 지연 데이터이므로 ``DELAYED`` 로 표기한다. ETF 적립식 투자
관점에서 지연은 의사결정에 영향이 없다.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from ..models import Bar, DataEnvelope, DataStatus, Quote
from .base import market_of

# API 파라미터 → yfinance 파라미터 매핑
_PERIOD_MAP = {
    "1M": "1mo",
    "3M": "3mo",
    "6M": "6mo",
    "1Y": "1y",
    "2Y": "2y",
    "5Y": "5y",
    "10Y": "10y",
}
_INTERVAL_MAP = {
    "1D": "1d",
    "1W": "1wk",
    "1M": "1mo",
}

# 미국 정규장 무료 데이터의 통상 지연(분)
_US_DELAY_MINUTES = 15


class YFinanceProvider:
    name = "yfinance"

    async def get_quote(self, symbol: str) -> DataEnvelope[Quote]:
        try:
            import yfinance as yf
        except ImportError:
            return DataEnvelope[Quote].empty(
                source=self.name,
                status=DataStatus.ERROR,
                message="yfinance 미설치 (pip install yfinance)",
            )

        try:
            # ★ yfinance 는 동기(blocking) — 스레드로 오프로드해 이벤트 루프를
            #   막지 않게 한다(동시 요청이 진짜 병렬로 처리됨).
            quote = await asyncio.to_thread(_fetch_quote, yf, symbol)
        except KeyError as exc:
            # yfinance FastInfo 는 데이터 없는 심볼에서 KeyError
            # (예: 'exchangeTimezoneName')를 던진다 — 시스템 오류가 아니라
            # "그 종목이 없다"는 뜻이므로 ERROR 가 아니라 NO_DATA 로 정직히 표기.
            return DataEnvelope[Quote].empty(
                source=self.name,
                status=DataStatus.NO_DATA,
                message=f"'{symbol}' 시세를 찾을 수 없습니다 ({exc})",
            )
        except Exception as exc:  # noqa: BLE001
            return DataEnvelope[Quote].empty(
                source=self.name,
                status=DataStatus.ERROR,
                message=f"시세 조회 실패: {exc}",
            )

        if quote is None:
            return DataEnvelope[Quote].empty(
                source=self.name,
                status=DataStatus.NO_DATA,
                message=f"'{symbol}' 시세를 찾을 수 없습니다",
            )

        return self._envelope_with_freshness(symbol, quote)

    async def get_bars(
        self, symbol: str, period: str, interval: str
    ) -> DataEnvelope[list[Bar]]:
        yf_period = _PERIOD_MAP.get(period.upper())
        yf_interval = _INTERVAL_MAP.get(interval.upper())
        if yf_period is None or yf_interval is None:
            return DataEnvelope[list[Bar]].empty(
                source=self.name,
                status=DataStatus.ERROR,
                message=f"지원하지 않는 기간/인터벌: {period}/{interval}",
            )

        try:
            import yfinance as yf
        except ImportError:
            return DataEnvelope[list[Bar]].empty(
                source=self.name,
                status=DataStatus.ERROR,
                message="yfinance 미설치 (pip install yfinance)",
            )

        try:
            bars = await asyncio.to_thread(
                _fetch_bars, yf, symbol, yf_period, yf_interval
            )
        except Exception as exc:  # noqa: BLE001
            return DataEnvelope[list[Bar]].empty(
                source=self.name,
                status=DataStatus.ERROR,
                message=f"차트 조회 실패: {exc}",
            )

        if not bars:
            return DataEnvelope[list[Bar]].empty(
                source=self.name,
                status=DataStatus.NO_DATA,
                message=f"'{symbol}' 차트 데이터가 없습니다",
            )

        status = DataStatus.DELAYED if market_of(symbol) == "US" else DataStatus.STALE
        delay = _US_DELAY_MINUTES if status is DataStatus.DELAYED else None
        return DataEnvelope.ok(
            bars,
            source=self.name,
            status=status,
            as_of=bars[-1].time,
            delay_minutes=delay,
        )

    def _envelope_with_freshness(
        self, symbol: str, quote: Quote
    ) -> DataEnvelope[Quote]:
        # 미국 무료 시세는 ~15분 지연(DELAYED). 한국 등 그 외 시장은 yfinance
        # 가 전일 종가(end-of-day)를 주므로 STALE 로 정직히 표기한다 — bars 경로
        # (get_bars)와 동일 기준. US 의 15분 지연 의미를 KR 에 붙이지 않는다.
        if market_of(symbol) == "US":
            status = DataStatus.DELAYED
            delay: int | None = _US_DELAY_MINUTES
        else:
            status = DataStatus.STALE
            delay = None
        return DataEnvelope.ok(
            quote,
            source=self.name,
            status=status,
            as_of=datetime.now(UTC),
            delay_minutes=delay,
        )


def _fetch_quote(yf: object, symbol: str) -> Quote | None:
    """동기 yfinance 시세 조회(스레드에서 실행)."""
    ticker = yf.Ticker(symbol)  # type: ignore[attr-defined]
    return quote_from_fast_info(symbol, ticker.fast_info)


def _fetch_bars(yf: object, symbol: str, period: str, interval: str) -> list[Bar]:
    """동기 yfinance 봉 조회 + 변환(스레드에서 실행)."""
    ticker = yf.Ticker(symbol)  # type: ignore[attr-defined]
    return _frame_to_bars(ticker.history(period=period, interval=interval))


def quote_from_fast_info(symbol: str, info: object) -> Quote | None:
    """yfinance ``FastInfo`` 에서 Quote 를 만든다.

    ★ FastInfo 의 dict 키는 camelCase('lastPrice')지만 **속성 접근은
    snake_case**('last_price')다. 안정적인 속성 접근을 사용한다.
    (이 구분을 놓치면 시세가 NO_DATA 로 잘못 나온다 — regression 테스트 존재)
    """
    price = _safe_float(getattr(info, "last_price", None))
    if price is None:
        return None
    prev = _safe_float(getattr(info, "previous_close", None))
    currency = getattr(info, "currency", None)

    change = None
    change_pct = None
    if prev is not None and prev != 0:
        change = price - prev
        change_pct = change / prev * 100

    return Quote(
        symbol=symbol,
        price=price,
        change=change,
        change_pct=change_pct,
        currency=currency if isinstance(currency, str) else None,
    )


def _safe_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        f = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if f != f:  # NaN 체크
        return None
    return f


def _frame_to_bars(hist: object) -> list[Bar]:
    """yfinance history DataFrame → Bar 리스트. pandas 의존을 격리."""
    bars: list[Bar] = []
    # pandas DataFrame 은 .empty / .iterrows() 를 제공
    if getattr(hist, "empty", True):
        return bars
    for ts, row in hist.iterrows():  # type: ignore[attr-defined]
        close = _safe_float(row.get("Close"))
        open_ = _safe_float(row.get("Open"))
        high = _safe_float(row.get("High"))
        low = _safe_float(row.get("Low"))
        if None in (open_, high, low, close):
            continue
        bars.append(
            Bar(
                time=_to_datetime(ts),
                open=open_,
                high=high,
                low=low,
                close=close,
                volume=_safe_float(row.get("Volume")),
            )
        )
    return bars


def _to_datetime(ts: object) -> datetime:
    to_py = getattr(ts, "to_pydatetime", None)
    if callable(to_py):
        return to_py()  # type: ignore[no-any-return]
    if isinstance(ts, datetime):
        return ts
    return datetime.now(UTC)
