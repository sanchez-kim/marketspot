"""핵심 데이터 모델.

설계 원칙(CLAUDE.md §0, DESIGN.md §3): 모든 외부 데이터는 ``DataEnvelope`` 로
정규화되어 *값 + 상태 + 출처 + 신선도* 를 항상 함께 운반한다. 데이터가 없으면
가짜 값으로 채우지 않고 ``DataStatus`` 로 정직하게 표기한다.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

T = TypeVar("T")


class DataStatus(StrEnum):
    """데이터 셀/패널의 신선도·가용성 상태.

    프론트는 이 값에 따라 뱃지를 표시한다. 절대로 임의 숫자로 빈 값을
    대체하지 않는다.
    """

    LIVE = "LIVE"  # 실시간
    DELAYED = "DELAYED"  # 지연 (delay_minutes 동반)
    STALE = "STALE"  # 마지막 갱신 후 오래됨
    NO_DATA = "NO_DATA"  # 데이터 없음
    NEEDS_KEY = "NEEDS_KEY"  # API 키 필요
    RATE_LIMITED = "RATE_LIMITED"  # 호출 제한 도달
    ERROR = "ERROR"  # 조회 실패


class CamelModel(BaseModel):
    """JSON 직렬화 시 camelCase 를 사용하는 공통 베이스."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class DataEnvelope(CamelModel, Generic[T]):
    """모든 외부 데이터의 표준 래퍼."""

    data: T | None = None
    status: DataStatus
    source: str
    as_of: datetime | None = None
    delay_minutes: int | None = None
    message: str | None = None

    @classmethod
    def ok(
        cls,
        data: T,
        *,
        source: str,
        status: DataStatus = DataStatus.LIVE,
        as_of: datetime | None = None,
        delay_minutes: int | None = None,
    ) -> DataEnvelope[T]:
        return cls(
            data=data,
            status=status,
            source=source,
            as_of=as_of,
            delay_minutes=delay_minutes,
        )

    @classmethod
    def empty(
        cls,
        *,
        source: str,
        status: DataStatus,
        message: str | None = None,
    ) -> DataEnvelope[T]:
        """데이터 없음 / 키 필요 / 에러 등 빈 상태 생성기."""
        if status in (DataStatus.LIVE, DataStatus.DELAYED):
            raise ValueError("empty() 는 데이터가 없는 상태에만 사용한다")
        return cls(data=None, status=status, source=source, message=message)


# ---- 도메인 모델 -------------------------------------------------------------


class Quote(CamelModel):
    """단일 종목/지수 시세 스냅샷."""

    symbol: str
    price: float
    change: float | None = None
    change_pct: float | None = None
    currency: str | None = None
    name: str | None = None


class Bar(CamelModel):
    """OHLCV 캔들 하나."""

    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float | None = None


class IndicatorSeries(CamelModel):
    """차트에 함께 그릴 보조지표 (입력 봉과 동일 길이, warmup 은 None)."""

    ma: dict[str, list[float | None]] = {}  # {"20": [...], "50": [...]}
    bb_upper: list[float | None] = []
    bb_middle: list[float | None] = []
    bb_lower: list[float | None] = []
    rsi: list[float | None] = []
    macd: list[float | None] = []
    macd_signal: list[float | None] = []
    macd_hist: list[float | None] = []


class ChartData(CamelModel):
    """차트 응답 본문: 봉 + 지표."""

    symbol: str
    period: str
    interval: str
    bars: list[Bar]
    indicators: IndicatorSeries


# ---- 뉴스 / AI ---------------------------------------------------------------


class Sentiment(StrEnum):
    POSITIVE = "POSITIVE"  # 강세
    NEUTRAL = "NEUTRAL"  # 중립
    NEGATIVE = "NEGATIVE"  # 약세


class Importance(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class NewsItem(CamelModel):
    """뉴스 원문 항목(요약/번역 전)."""

    id: str
    title: str
    summary: str = ""  # 원문 요약(영어)
    publisher: str | None = None
    link: str | None = None
    published: datetime | None = None
    tickers: list[str] = []


class NewsAnalysis(CamelModel):
    """한 뉴스에 대한 AI/규칙 분석 결과."""

    sentiment: Sentiment
    importance: Importance
    tickers: list[str] = []
    korean_summary: str


class AnalyzedNews(CamelModel):
    item: NewsItem
    analysis: NewsAnalysis


class NewsSummaryResult(CamelModel):
    """요약 응답. backend 는 실제로 사용된 AI 백엔드(ollama/gemini/rule)."""

    backend: str
    items: list[AnalyzedNews]


class AskResult(CamelModel):
    backend: str
    answer: str


# ---- 공시 (Filings) ----------------------------------------------------------


class Filing(CamelModel):
    """단일 공시 항목."""

    form: str  # 서식 코드 (예: "10-K", "8-K", "NPORT-P")
    title: str  # 사람이 읽는 설명 (없으면 form 으로 대체)
    filed: datetime  # 접수일
    report_date: datetime | None = None  # 보고 기준일 (있을 때)
    url: str  # 원문 링크
    accession: str  # 접수번호


class FilingList(CamelModel):
    """한 종목의 공시 묶음. 펀드/ETF 는 신탁(entity) 단위로 보고된다."""

    entity: str  # 제출 주체명 (회사/신탁)
    cik: str | None = None  # SEC CIK (미국)
    market: str  # US | KR
    filings: list[Filing]


# ---- 포트폴리오 (수동 입력) --------------------------------------------------


class Position(CamelModel):
    """사용자가 직접 입력한 보유 포지션(원금 정보)."""

    symbol: str
    quantity: float  # 보유 수량
    avg_cost: float  # 평균 매입 단가


class PositionValuation(CamelModel):
    """현재 시세로 평가한 포지션. 시세가 없으면 가격/평가액은 null 로 둔다."""

    symbol: str
    quantity: float
    avg_cost: float
    cost_basis: float  # 원금 = quantity * avg_cost (항상 계산 가능)
    name: str | None = None
    currency: str | None = None
    price: float | None = None  # 현재가 (없으면 null)
    market_value: float | None = None  # 평가액 = quantity * price
    unrealized_pnl: float | None = None  # 평가손익 = market_value - cost_basis
    unrealized_pnl_pct: float | None = None  # 수익률(%)
    weight: float | None = None  # 비중(%) = market_value / total_value
    status: DataStatus  # 이 포지션 시세의 상태


class PortfolioSummary(CamelModel):
    """포트폴리오 전체 평가 결과.

    합계는 **시세가 있는 포지션만** 반영한다(가짜 평가 금지). 시세가 없는
    포지션 수는 ``unvalued_count`` 로 정직하게 알린다.
    """

    positions: list[PositionValuation]
    total_value: float  # 평가액 합(시세 있는 것만)
    total_cost: float  # 원금 합(시세 있는 것만 — 손익률 분모와 일치)
    total_pnl: float  # 평가손익 합
    total_pnl_pct: float | None  # 총 수익률(%)
    valued_count: int  # 시세로 평가된 포지션 수
    unvalued_count: int  # 시세 없어 제외된 포지션 수
    as_of: datetime | None = None


# ---- 심볼 검색 (자동완성) ----------------------------------------------------


class SymbolMatch(CamelModel):
    """심볼 검색 결과 한 건."""

    symbol: str
    name: str  # 회사/펀드명
    type: str  # EQUITY | ETF | INDEX | MUTUALFUND
    exchange: str | None = None  # 거래소 표시명


# ---- 종목 기본정보 (Fundamentals) -------------------------------------------


class Holding(CamelModel):
    """ETF 구성 종목 하나."""

    symbol: str | None = None
    name: str
    weight: float  # 비중(%)


class CalendarEvent(CamelModel):
    """다가오는 일정 한 건 (실적 발표 / 배당락)."""

    symbol: str
    type: str  # earnings | exDividend
    date: date


class Fundamentals(CamelModel):
    """'내가 산 게 뭔지' — 초보용 기본정보. 없는 값은 채우지 않고 null."""

    symbol: str
    status: DataStatus
    name: str | None = None
    type: str | None = None  # EQUITY | ETF
    summary: str | None = None  # 무엇을 하는/담는 곳인지(원문)
    sector: str | None = None  # 주식
    industry: str | None = None  # 주식
    category: str | None = None  # ETF 분류
    currency: str | None = None
    market_cap: float | None = None  # 주식 시가총액
    total_assets: float | None = None  # ETF 순자산(AUM)
    pe_ratio: float | None = None
    dividend_yield: float | None = None  # %
    week52_high: float | None = None
    week52_low: float | None = None
    beta: float | None = None
    top_holdings: list[Holding] = []  # ETF 보유 상위
    message: str | None = None


# ---- 안심 레이어: 하락 맥락화 ------------------------------------------------


class DrawdownContext(CamelModel):
    """한 종목의 고점 대비 낙폭과 과거 조정의 정직한 기저율.

    예측이 아니라 *역사적 사실*만 담는다. 데이터가 부족하면 ``limited_history``
    로 표기하고 기저율을 비운다(가짜 안심 ❌).
    """

    symbol: str
    status: DataStatus
    as_of: datetime | None = None
    asset_type: str | None = None  # ETF | EQUITY | INDEX (회복 보장 여부 단서)
    current_price: float | None = None
    peak_price: float | None = None
    peak_date: datetime | None = None
    current_drawdown_pct: float | None = None  # 예: -2.9
    history_years: float | None = None  # 실제 보유 데이터 길이(정직)
    threshold_pct: float | None = None  # 기저율 기준 낙폭(예: 5.0)
    comparable_count: int = 0  # 기준 이상 깊었던 과거 조정 수
    recovered_count: int = 0  # 그중 회복 완료
    median_recovery_days: int | None = None
    max_recovery_days: int | None = None
    worst_drawdown_pct: float | None = None  # 예: -34.0
    limited_history: bool = False  # 데이터 짧아 기저율 비신뢰
    note: str | None = None  # "개별 종목은 회복 미보장" 등 정직 단서
    message: str | None = None  # 에러/데이터 없음 사유


class HomeVerdict(CamelModel):
    """안심 홈의 한 줄 평결: "계획대로 가고 있나? 뭔가 해야 하나?".

    톤은 포트폴리오 손익으로, 근거는 최대 비중 종목의 하락 맥락으로 만든다.
    예측·매수매도 권유는 하지 않는다.
    """

    tone: str  # ON_TRACK | NORMAL_DIP | UNUSUAL | NO_HOLDINGS
    headline: str  # 한 줄 평결
    subline: str  # 근거 한 줄(기저율 등)
    todo: str  # 보통 "지금 할 일: 없음 — 계획대로 계속"
    total_value: float = 0.0
    total_pnl_pct: float | None = None
    context: DrawdownContext | None = None  # 근거가 된 종목의 하락 맥락
    as_of: datetime | None = None
