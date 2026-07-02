"""의존성 구성(컴포지션 루트).

provider 체인과 서비스 싱글톤을 만든다. 키가 필요한 제공자(KIS/Alpaca)는
키가 있을 때만 체인에 추가한다 — 그렇지 않으면 yfinance(키 불필요)만으로
동작한다.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from functools import lru_cache

from .config import load_settings
from .providers.base import QuoteProvider
from .providers.calendar_provider import YFinanceCalendarProvider
from .providers.filings_provider import (
    DartProvider,
    FilingsProvider,
    SecEdgarProvider,
)
from .providers.fundamentals_provider import YFinanceFundamentalsProvider
from .providers.last_good import LastGoodStore
from .providers.macro_provider import FredMacroProvider
from .providers.registry import ProviderRegistry
from .providers.search_provider import SearchProvider, YahooSearchProvider
from .providers.toss_client import TossClient
from .providers.toss_provider import TossQuoteProvider
from .providers.yfinance_provider import YFinanceProvider
from .services.chart import ChartService
from .services.conditions import MacroConditionsService
from .services.filings import FilingsService
from .services.fx import FxService
from .services.home import HomeService
from .services.macro import MacroService
from .services.news import NewsAIService
from .services.portfolio import PortfolioService
from .services.quotes import QuoteService
from .services.reassurance import ReassuranceService
from .services.risk import RiskService
from .services.spark import SparkService
from .services.toss_sync import TossSyncService
from .services.valuation import ValuationService


def build_registry() -> ProviderRegistry:
    yf = YFinanceProvider()
    # MVP: 미국은 yfinance 기본. KIS/Alpaca 는 키 연동 시 앞단에 추가.
    us_chain: list[QuoteProvider] = [yf]
    # 토스는 항상 KR 체인 맨 앞에 둔다(키 유무와 무관) — 키가 없으면
    # TossQuoteProvider 가 네트워크 호출 없이 즉시 NEEDS_KEY 를 반환해
    # yfinance 로 곧바로 폴백한다. 이 설계 덕분에 get_registry() 는 키를
    # 캡처하지 않는 안정적 싱글턴으로 남는다 — registry() 를 소비하는
    # 8개 lru_cache 서비스(quote/chart/macro/risk/spark/reassurance/
    # conditions/valuation)를 전부 reset_service_caches() 에서 캐스케이드
    # 클리어해야 하는 위험을 피한다. 여기에 get_registry.cache_clear() 를
    # "고치듯" 추가하지 말 것 — 위 이유로 불필요하고, 추가하면 오히려
    # 절반만 갱신되는 버그를 만든다(하위 8개 서비스는 여전히 캐시됨).
    kr_chain: list[QuoteProvider] = [
        TossQuoteProvider(get_toss_client_factory),
        yf,
    ]
    # last-good 폴백: 일시 실패 시 마지막 정상값을 STALE 로 제공(메모리 상한).
    return ProviderRegistry(
        {"US": us_chain, "KR": kr_chain}, store=LastGoodStore(max_entries=256)
    )


@lru_cache(maxsize=1)
def get_registry() -> ProviderRegistry:
    return build_registry()


@lru_cache(maxsize=1)
def get_quote_service() -> QuoteService:
    return QuoteService(get_registry())


@lru_cache(maxsize=1)
def get_chart_service() -> ChartService:
    return ChartService(get_registry())


@lru_cache(maxsize=1)
def get_macro_service() -> MacroService:
    return MacroService(get_registry())


@lru_cache(maxsize=1)
def get_news_service() -> NewsAIService:
    return NewsAIService()


@lru_cache(maxsize=1)
def get_portfolio_service() -> PortfolioService:
    return PortfolioService(get_quote_service(), FxService(get_quote_service()))


@lru_cache(maxsize=1)
def get_risk_service() -> RiskService:
    return RiskService(get_registry(), get_portfolio_service())


@lru_cache(maxsize=1)
def get_search_provider() -> SearchProvider:
    return YahooSearchProvider()


@lru_cache(maxsize=1)
def get_fundamentals_provider() -> YFinanceFundamentalsProvider:
    return YFinanceFundamentalsProvider()


@lru_cache(maxsize=1)
def get_calendar_provider() -> YFinanceCalendarProvider:
    return YFinanceCalendarProvider()


@lru_cache(maxsize=1)
def get_spark_service() -> SparkService:
    return SparkService(get_registry())


@lru_cache(maxsize=1)
def get_reassurance_service() -> ReassuranceService:
    return ReassuranceService(get_registry(), get_search_provider())


@lru_cache(maxsize=1)
def get_home_service() -> HomeService:
    return HomeService(
        get_portfolio_service(),
        get_reassurance_service(),
        plan_loader=lambda: load_settings().plan,
    )


@lru_cache(maxsize=1)
def get_filings_service() -> FilingsService:
    # DART 키는 로컬 설정에서 읽는다(없으면 NEEDS_KEY 로 정직하게 표기).
    dart_key = load_settings().api_keys.dart
    providers: dict[str, FilingsProvider] = {
        "US": SecEdgarProvider(),
        "KR": DartProvider(api_key=dart_key),
    }
    return FilingsService(providers)


def _fred_key() -> str:
    # settings.json 우선, 없으면 .env 의 FRED_API_KEY 사용(정직: 둘 다 없으면 빈 문자열)
    return load_settings().api_keys.fred or os.environ.get("FRED_API_KEY", "")


@lru_cache(maxsize=1)
def get_conditions_service() -> MacroConditionsService:
    fred = FredMacroProvider(_fred_key())
    return MacroConditionsService(fred, get_registry())


@lru_cache(maxsize=1)
def get_valuation_service() -> ValuationService:
    return ValuationService(get_fundamentals_provider(), get_registry())


@lru_cache(maxsize=1)
def get_toss_client_factory() -> Callable[[], TossClient]:
    """토스 app key/secret 를 캡처한 클라이언트 팩토리.

    키를 생성 시점에 한 번 읽어(캡처) 팩토리에 담는다 — 그래서 키가 바뀌면
    ``reset_service_caches()`` 로 이 캐시를 비워야 새 키가 반영된다(★ 아래 계약).
    팩토리는 호출마다 **새 클라이언트**를 만든다: 토큰 단일 관리자를 동기화
    작업(메서드) 단위로 격리해 1토큰 제약을 안전하게 지킨다.
    """
    keys = load_settings().api_keys
    app_key = keys.toss_app_key
    app_secret = keys.toss_app_secret

    def factory() -> TossClient:
        return TossClient(app_key, app_secret)

    return factory


@lru_cache(maxsize=1)
def get_toss_sync_service() -> TossSyncService:
    return TossSyncService(get_toss_client_factory())


def reset_service_caches() -> None:
    """설정(특히 API 키) 변경 후 키를 캡처해 둔 서비스 캐시를 비운다.

    이 서비스들은 생성 시 FRED/DART 키를 한 번 읽어 보관하므로, 키가 바뀌면
    캐시를 비워 다음 요청에서 새 키로 다시 만들어지게 한다(재시작 불필요).

    주의: 앞으로 키를 생성 시점에 캡처하는 @lru_cache 팩토리를 추가하면
    반드시 여기에도 cache_clear()를 추가해야 "재시작 없이 적용" 보장이 유지된다.
    """
    get_conditions_service.cache_clear()
    get_filings_service.cache_clear()
    # 토스 팩토리는 app key/secret 를 캡처한다 → 키 변경 시 재생성 필요.
    # sync 서비스는 팩토리를 들고 있으므로 함께 비운다.
    get_toss_client_factory.cache_clear()
    get_toss_sync_service.cache_clear()
