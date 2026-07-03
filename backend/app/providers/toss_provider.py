"""토스 시세 보조 프로바이더 (Phase A Wave 3, 스펙 §3.5).

KR 체인 앞단에 항상 붙는다(키 유무와 무관하게). 키가 없으면 네트워크 호출
없이 즉시 ``NEEDS_KEY`` 를 반환해 registry 가 yfinance 로 곧바로 폴백하게
한다 — 그래서 ``deps.get_registry()`` 는 키 의존적일 필요가 없다(캐시
캐스케이드 무효화 불필요, 아래 ``deps.py`` 주석 참고).

캔들은 1m/1d 만 제공돼(§비목표) ``get_bars`` 는 항상 NO_DATA — bars 는
yfinance 가 계속 담당한다.

공식 문서(developers.tossinvest.com, 2026-07 확인) 기준 토스는 한국 종목을
접미사 없는 6자리 코드(``005930``)로 다룬다 — registry 가 넘기는 yfinance
표기(``005930.KS``)와 형식이 다르므로 ``_toss_symbol()`` 로 변환해 호출한다
(``Quote`` 응답의 ``symbol`` 은 호출자 계약대로 원래 앱 표기를 유지).
"""

from __future__ import annotations

import time
from collections.abc import Callable

from ..cache import TTLCache
from ..config import load_settings
from ..models import Bar, DataEnvelope, DataStatus, Quote
from .toss_client import TossClient

# ★ 실키 검증 전까지 LIVE 로 단정한다(스펙 §3.5/§4 — 검증 후 DELAYED 로
#   조정될 수 있음, 그 전까지는 상수로 명시해 추적 가능하게 한다).
_TOSS_QUOTE_STATUS = DataStatus.LIVE
_QUOTE_TTL_S = 10.0


def _has_toss_keys() -> bool:
    keys = load_settings().api_keys
    return bool(keys.toss_app_key and keys.toss_app_secret)


def _toss_symbol(symbol: str) -> str:
    """앱 표기(예: ``005930.KS``)를 토스가 기대하는 접미사 없는 코드로.

    문서 확인(developers.tossinvest.com, 2026-07): 한국 종목은 접미사 없는
    6자리 코드. 접미사가 없는 입력(예: 미국 종목)은 그대로 돌려준다 —
    이 프로바이더는 KR 체인에만 붙지만 방어적으로 처리한다.
    """
    upper = symbol.upper()
    if upper.endswith((".KS", ".KQ")):
        return upper[:-3]
    return symbol


class TossQuoteProvider:
    """토스 시세 — 항상 KR 체인 앞단에 있지만, 키 없으면 즉시 NEEDS_KEY."""

    name = "toss"

    def __init__(
        self,
        client_factory_provider: Callable[[], Callable[[], TossClient]],
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        # client_factory_provider 는 값이 아니라 deps.get_toss_client_factory
        # "함수 자체"를 받는다 — 매 호출마다 그 함수를 다시 불러야 설정 변경
        # (reset_service_caches) 이후에도 최신 키를 반영한다. 생성 시점에
        # factory() 결과를 한 번만 캡처해 저장하면 키 변경이 반영되지 않는다.
        self._client_factory_provider = client_factory_provider
        self._cache: TTLCache[Quote] = TTLCache(clock=clock)

    async def get_quote(self, symbol: str) -> DataEnvelope[Quote]:
        cached = self._cache.get(symbol)
        if cached is not None:
            return DataEnvelope.ok(cached, source=self.name, status=_TOSS_QUOTE_STATUS)

        if not _has_toss_keys():
            return DataEnvelope[Quote].empty(
                source=self.name,
                status=DataStatus.NEEDS_KEY,
                message="토스증권 app key/secret 를 설정에서 입력하세요.",
            )

        toss_symbol = _toss_symbol(symbol)
        factory = self._client_factory_provider()
        client = factory()
        try:
            prices = await client.get_prices([toss_symbol])
            candles = await client.get_candles(toss_symbol, "1d", 2)
        finally:
            await client.aclose()

        if not prices:
            return DataEnvelope[Quote].empty(
                source=self.name,
                status=DataStatus.NO_DATA,
                message=f"'{symbol}' 토스 시세를 찾을 수 없습니다",
            )
        price_item = prices[0]

        change: float | None = None
        change_pct: float | None = None
        sorted_candles = sorted(candles, key=lambda c: c.time)
        if len(sorted_candles) >= 2:
            prev_close = sorted_candles[-2].close
            if prev_close:
                change = price_item.last_price - prev_close
                change_pct = change / prev_close * 100
        # 캔들이 2개 미만이면 change/change_pct 는 None 으로 둔다 — 지어내지
        # 않는다(§0). 프론트는 null 을 정직하게 '—' 로 표시한다(기존 계약).

        quote = Quote(
            symbol=symbol,
            price=price_item.last_price,
            change=change,
            change_pct=change_pct,
            currency=price_item.currency,
        )
        self._cache.set(symbol, quote, _QUOTE_TTL_S)
        return DataEnvelope.ok(quote, source=self.name, status=_TOSS_QUOTE_STATUS)

    async def get_bars(
        self, symbol: str, period: str, interval: str
    ) -> DataEnvelope[list[Bar]]:
        return DataEnvelope[list[Bar]].empty(
            source=self.name,
            status=DataStatus.NO_DATA,
            message="토스 캔들은 미지원 — yfinance 사용",
        )
