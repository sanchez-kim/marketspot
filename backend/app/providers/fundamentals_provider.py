"""종목 기본정보 제공자 (yfinance ``.info`` + ETF 보유종목).

'내가 산 게 뭔지'를 초보에게 보여주기 위한 정보. yfinance 는 비공식이라
필드가 빠질 수 있다 — 없으면 채우지 않고 null/NO_DATA 로 정직하게 둔다.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable, Mapping, Sequence

from ..cache import TTLCache
from ..models import DataStatus, Fundamentals, Holding

JsonDict = Mapping[str, object]
_TTL = 3600.0  # 1시간 (기본정보는 천천히 변함)


def _s(info: JsonDict, key: str) -> str | None:
    v = info.get(key)
    return v if isinstance(v, str) and v else None


def _f(info: JsonDict, key: str) -> float | None:
    v = info.get(key)
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def parse_fundamentals(
    symbol: str, info: JsonDict, holdings: Sequence[JsonDict]
) -> Fundamentals:
    """yfinance info(+보유종목) → Fundamentals (순수 함수)."""
    summary = _s(info, "longBusinessSummary")
    if summary and len(summary) > 600:
        summary = summary[:600].rstrip() + "…"

    parsed_holdings: list[Holding] = []
    for h in holdings:
        name = h.get("name")
        if not isinstance(name, str) or not name:
            continue
        w = h.get("weight")
        weight = float(w) * 100 if isinstance(w, (int, float)) else 0.0
        sym = h.get("symbol")
        parsed_holdings.append(
            Holding(
                symbol=sym if isinstance(sym, str) else None,
                name=name,
                weight=round(weight, 2),
            )
        )

    return Fundamentals(
        symbol=symbol.upper(),
        status=DataStatus.DELAYED,
        name=_s(info, "longName") or _s(info, "shortName"),
        type=_s(info, "quoteType"),
        summary=summary,
        sector=_s(info, "sector"),
        industry=_s(info, "industry"),
        category=_s(info, "category"),
        currency=_s(info, "currency"),
        market_cap=_f(info, "marketCap"),
        total_assets=_f(info, "totalAssets"),
        pe_ratio=_f(info, "trailingPE"),
        dividend_yield=_f(info, "dividendYield"),
        week52_high=_f(info, "fiftyTwoWeekHigh"),
        week52_low=_f(info, "fiftyTwoWeekLow"),
        beta=_f(info, "beta"),
        top_holdings=parsed_holdings,
    )


class YFinanceFundamentalsProvider:
    name = "yfinance-fundamentals"

    def __init__(self, *, clock: Callable[[], float] = time.monotonic) -> None:
        self._cache: TTLCache[Fundamentals] = TTLCache(clock=clock)

    async def get(self, symbol: str) -> Fundamentals:
        key = symbol.upper()
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        try:
            import yfinance as yf
        except ImportError:
            return Fundamentals(
                symbol=key, status=DataStatus.ERROR, message="yfinance 미설치"
            )

        try:
            # 동기 yfinance(info + 보유종목) → 스레드로 오프로드
            info, holdings = await asyncio.to_thread(_fetch_info, yf, symbol)
        except Exception as exc:  # noqa: BLE001 - 어떤 조회 오류도 상태로 변환
            return Fundamentals(
                symbol=key, status=DataStatus.ERROR, message=f"조회 실패: {exc}"
            )

        if not info.get("longName") and not info.get("shortName"):
            return Fundamentals(
                symbol=key, status=DataStatus.NO_DATA, message="기본정보가 없습니다"
            )

        fund = parse_fundamentals(symbol, info, holdings)
        self._cache.set(key, fund, _TTL)
        return fund


def _fetch_info(
    yf: object, symbol: str
) -> tuple[dict[str, object], list[dict[str, object]]]:
    """동기 yfinance 기본정보 + ETF 보유종목(스레드에서 실행)."""
    ticker = yf.Ticker(symbol)  # type: ignore[attr-defined]
    info = ticker.info or {}
    holdings = _etf_holdings(ticker) if info.get("quoteType") == "ETF" else []
    return info, holdings


def _etf_holdings(ticker: object) -> list[dict[str, object]]:
    """ETF 보유 상위 — funds_data 가 없거나 형식이 다르면 빈 목록."""
    out: list[dict[str, object]] = []
    try:
        th = ticker.funds_data.top_holdings  # type: ignore[attr-defined]
        for idx, row in th.iterrows():
            out.append(
                {
                    "symbol": str(idx),
                    "name": str(row.get("Name", "")),
                    "weight": float(row.get("Holding Percent", 0)),
                }
            )
    except Exception:  # noqa: BLE001 - 보유종목 없으면 그냥 비움
        return []
    return out
