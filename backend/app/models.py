"""핵심 데이터 모델.

설계 원칙(CLAUDE.md §0, DESIGN.md §3): 모든 외부 데이터는 ``DataEnvelope`` 로
정규화되어 *값 + 상태 + 출처 + 신선도* 를 항상 함께 운반한다. 데이터가 없으면
가짜 값으로 채우지 않고 ``DataStatus`` 로 정직하게 표기한다.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Generic, Literal, TypeVar

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


class Transaction(CamelModel):
    """사용자 거래(체결) 기록 — 매수/매도 1건.

    ``source``/``external_id``/``fee``/``tax`` 는 토스증권 연동(Phase A)에서
    추가됐다. 기존 저장 데이터에는 없으므로 **기본값으로 하위호환**한다:
    수동 입력분은 ``source="manual"``, 브로커 동기화분은 ``source="toss"``
    (부트스트랩 스냅샷은 ``"toss-baseline"``). ``external_id`` 는 멱등 동기화
    키(주문 orderId / baseline 키)로 중복 import 를 막는다.
    """

    id: str
    date: str | None  # ISO YYYY-MM-DD. 마이그레이션분은 None("기초 보유")
    type: Literal["buy", "sell"]
    symbol: str
    quantity: float
    price: float  # 1주당 체결가(해당 종목 통화 기준)
    currency: str  # "USD" | "KRW"
    source: str = "manual"  # manual | toss | toss-baseline
    external_id: str | None = None  # 동기화 멱등 키(orderId / baseline 키)
    fee: float | None = None  # 수수료(체결 통화 기준)
    tax: float | None = None  # 세금(체결 통화 기준)


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
    realized_pnl: float = 0.0  # 실현손익(매도로 확정된 손익, 원통화)
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
    total_realized: float = 0.0  # 실현손익 합(원통화 단순합 — 단일통화 호환)
    value_krw: float | None = None
    value_usd: float | None = None
    unrealized_krw: float | None = None
    unrealized_usd: float | None = None
    realized_krw: float | None = None
    realized_usd: float | None = None
    fx_rate: float | None = None  # 1 USD 당 KRW
    fx_status: DataStatus = DataStatus.NO_DATA


# ---- 포트폴리오 리스크(근거 ④) ----------------------------------------------


class HoldingWeight(CamelModel):
    """보유 비중 한 건(평가액 기준 %)."""

    symbol: str
    weight: float


class CorrelationPair(CamelModel):
    """두 종목의 상관계수(-1~1). 같이 움직일수록 분산 효과가 적다."""

    a: str
    b: str
    corr: float


class PortfolioRisk(CamelModel):
    """포트폴리오 집중도·상관(분산) 요약. 근거 ④ '포트폴리오 영향'.

    예측이 아니라 현재 보유의 *구조적 사실*만 담는다. 시세/이력이 없는 종목은
    excluded 로 빼고 그 사실을 표기한다(가짜 ❌).
    """

    status: DataStatus
    as_of: datetime | None = None
    concentration_hhi: float | None = None  # 0~1 (1=완전 집중)
    top_symbol: str | None = None
    top_weight: float | None = None  # %
    weights: list[HoldingWeight] = []
    correlations: list[CorrelationPair] = []
    avg_correlation: float | None = None  # 평균 쌍별 상관(낮을수록 분산↑)
    lookback_days: int | None = None
    excluded: list[str] = []  # 시세/이력 없어 상관 계산 제외
    message: str | None = None


# ---- 거시 환경(근거 ③) ------------------------------------------------------


class MacroMetric(CamelModel):
    """거시 지표 한 건(금리/CPI 등). 예측 없이 발표값·방향만."""

    label: str
    value: float | None = None
    unit: str | None = None  # "%" 등
    as_of: date | None = None  # 발표/기준일
    change: float | None = None  # 직전 대비(방향)
    status: DataStatus
    source: str
    note: str | None = None


class IndexTrend(CamelModel):
    """지수의 이동평균선 대비 위치(과열/침체 단서). 예측 ❌."""

    label: str
    symbol: str
    price: float | None = None
    vs_ma50_pct: float | None = None  # (price/MA50 - 1) * 100
    vs_ma200_pct: float | None = None  # (price/MA200 - 1) * 100
    status: DataStatus


class MacroConditions(CamelModel):
    """근거 ③ '거시 환경': 기준금리 + CPI + 핵심 지수 추세."""

    rate: MacroMetric
    cpi: MacroMetric
    indices: list[IndexTrend] = []
    as_of: datetime | None = None


# ---- 밸류 컨텍스트(근거 ①) --------------------------------------------------


class ValuationContext(CamelModel):
    """근거 ① '밸류·과열도'. 사실만 — 싸다/비싸다 판단은 사용자.

    5년 평균 PER 은 yfinance 한계로 신뢰 제공이 어려워 null 로 두고 note 로
    그 사실을 알린다(가짜 ❌).
    """

    symbol: str
    status: DataStatus
    as_of: datetime | None = None
    pe_ratio: float | None = None
    pe_5y_avg: float | None = None  # 미제공(yfinance 한계) → null
    pe_vs_5y_avg_pct: float | None = None
    dividend_yield: float | None = None  # %
    week52_high: float | None = None
    week52_low: float | None = None
    week52_position_pct: float | None = None  # 0=저점,100=고점
    price: float | None = None
    vs_ma200_pct: float | None = None  # 200일선 대비(과열도 단서)
    note: str | None = None
    message: str | None = None


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


# ---- 토스증권 연동 (Phase A) -------------------------------------------------


class TossAccountInfo(CamelModel):
    """상태 응답에 실을 계좌 표시 정보(원시 TossAccount 를 프론트용으로 조합).

    토스 스펙에 표시용 ``name`` 이 없어(§0 지어내지 않음) accountType·accountNo
    로 ``label`` 을 조합한다. ``account_seq`` 는 문자열로 노출(settings 형식과 일치).
    """

    account_seq: str
    account_no: str
    account_type: str | None = None
    label: str


class TossStatus(CamelModel):
    """``GET /api/toss/status`` 의 데이터 본문(연동돼 있을 때)."""

    connected: bool
    accounts: list[TossAccountInfo] = []
    selected_account_seq: str | None = None
    last_sync: str | None = None


class DriftWarning(CamelModel):
    """파생 포지션 수량 vs 토스 실잔고 불일치(정직성 — 숨기지 않고 표기).

    ``app_qty`` 는 거래내역 fold 로 도출한 수량, ``toss_qty`` 는 토스 holdings
    실수량. 동기화 밖 거래(다른 도구·소급 한도 밖)를 드러낸다.
    """

    symbol: str
    app_qty: float
    toss_qty: float


class TossSyncResult(CamelModel):
    """``POST /api/toss/sync`` 결과 요약.

    ``mode`` 는 최초 연동(bootstrap) / 증분(incremental). ``added`` 는 새로
    삽입된 거래 수. ``skipped_unpriced`` 는 체결됐으나 체결가가 없어 (가짜값을
    만들지 않고) 건너뛴 주문 수(§0). ``drift`` 는 잔고 대조 경고.
    """

    mode: Literal["bootstrap", "incremental"]
    added: int
    skipped_unpriced: int = 0
    drift: list[DriftWarning] = []
