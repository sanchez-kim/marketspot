"""토스증권 Open API 클라이언트 코어 (Phase A).

Base URL ``https://openapi.tossinvest.com``. OAuth2 client_credentials 로 토큰을
발급받아 계좌·잔고·주문·시세·캔들을 읽는다. 이 클라이언트는 **에러를 삼키지
않는다**(CLAUDE.md §0) — HTTP/파싱 실패는 예외로 전파하고, DataStatus 변환은
상위 계층(프로바이더/라우터)의 책임이다.

토큰 단일 관리자 (핵심 제약)
----------------------------
토스는 **client 당 유효 토큰 1개**만 허용한다 — 재발급하면 기존 토큰이 즉시
무효화된다. 따라서 동시 코루틴이 각자 재발급하면 서로를 무효화하는 경쟁이
발생한다. 이를 막기 위해:

- ``asyncio.Lock`` 으로 재발급을 직렬화한다.
- 락 획득 후 **다시 확인(double-check)** 한다 — 다른 코루틴이 이미 재발급했으면
  그 토큰을 그대로 쓴다(중복 재발급으로 서로를 무효화하지 않도록).
- 만료 판정은 ``발급시각 + expires_in - 60초`` 여유. 클럭을 주입해 테스트가
  결정적이다(실시간 대기 없음).

401(외부 도구가 토큰을 무효화) → 락 잡고 강제 재발급 후 원요청 1회 재시도.
429(레이트리밋) → ``Retry-After`` 초만큼 주입된 sleep 으로 대기 후 1회 재시도.

필드명 출처: OpenAPI 스펙(v1.x)
    https://openapi.tossinvest.com/openapi-docs/latest/openapi.json (2026-07-03 확인)
성공 응답은 ``{"result": ...}`` 로 감싸이며, 토큰 응답만 표준 OAuth 평문이다.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable, Sequence
from datetime import datetime
from typing import Any, Literal

import httpx
from pydantic import Field

from ..models import CamelModel

_BASE_URL = "https://openapi.tossinvest.com"
_TIMEOUT = 10.0
_EXPIRY_MARGIN = 60.0  # 만료 60초 전에 선제 재발급
_DEFAULT_RETRY_AFTER = 1.0  # 429 인데 Retry-After 헤더가 없을 때의 기본 대기(초)

SleepFn = Callable[[float], Awaitable[Any]]
ClockFn = Callable[[], float]


# ── 응답 모델 (OpenAPI 스펙 기준 alias 매핑) ──────────────────────────────────
# CamelModel 이 snake_case → camelCase alias 를 자동 생성하므로, camelCase 와
# 그대로 맞는 필드는 별도 alias 가 필요 없다. 캔들처럼 이름이 다른 필드만 명시.


class TossAccount(CamelModel):
    """``GET /api/v1/accounts`` 의 ``result[]`` 원소.

    스펙 필드: ``accountNo``, ``accountSeq``(int), ``accountType``.
    ★ 스펙에 표시용 ``name`` 필드는 없다 — 지어내지 않고 accountType 만 노출한다
      (§0 정직성). 표시명은 상위 계층에서 accountType/accountNo 로 조합.
    """

    account_seq: int
    account_no: str
    account_type: str | None = None


class TossHolding(CamelModel):
    """``GET /api/v1/holdings`` 의 ``result.items[]`` 원소.

    스펙 필드: ``symbol``, ``name``, ``quantity``, ``averagePurchasePrice``,
    ``currency``, ``lastPrice``. (수치는 문자열로 올 수 있어 pydantic lax 강제
    변환에 맡긴다 — 예: prices 의 ``"72000"``.)
    """

    symbol: str
    name: str | None = None
    quantity: float
    average_purchase_price: float
    currency: str | None = None
    last_price: float | None = None


class TossExecution(CamelModel):
    """주문 체결 집계(주문 단위 — 개별 fill 은 스펙상 제공 안 됨).

    스펙 필드(order.execution): ``filledQuantity``, ``averageFilledPrice``,
    ``commission``, ``tax``, ``filledAt``.
    """

    filled_quantity: float | None = None
    average_filled_price: float | None = None
    commission: float | None = None
    tax: float | None = None
    filled_at: datetime | None = None


class TossOrder(CamelModel):
    """``GET /api/v1/orders`` 의 ``result.orders[]`` 원소.

    스펙 필드: ``orderId``, ``symbol``, ``side``, ``status``, ``currency``,
    ``orderedAt``, 중첩 ``execution``. (계약에 없는 필드는 무시된다.)
    """

    order_id: str
    symbol: str
    side: Literal["BUY", "SELL"]
    status: str | None = None
    currency: str | None = None
    ordered_at: datetime | None = None
    execution: TossExecution | None = None


class TossOrderPage(CamelModel):
    """``GET /api/v1/orders`` 응답 ``result`` (PaginatedOrderResponse).

    스펙 필드: ``orders[]``, ``nextCursor``, ``hasNext``. 페이지네이션은
    ``nextCursor`` 로 순회한다(없으면 마지막 페이지).
    """

    orders: list[TossOrder] = Field(default_factory=list)
    next_cursor: str | None = None


class TossOrderDetail(CamelModel):
    """``GET /api/v1/orders/{orderId}`` 단건 상세.

    ★ 이 경로는 OpenAPI 문서 본문에 스키마가 없으나 문서 설명상 "개별 orderId
      로 주문 상세 조회 지원"이라 명시됨 → 목록 원소와 동일 형태로 방어적 파싱.
    스펙 필드: ``orderId``, ``symbol``, ``side``, ``currency``, ``execution``.
    """

    order_id: str
    symbol: str
    side: Literal["BUY", "SELL"]
    currency: str | None = None
    execution: TossExecution | None = None


class TossPrice(CamelModel):
    """``GET /api/v1/prices`` 의 ``result[]`` 원소.

    스펙 필드: ``symbol``, ``timestamp``, ``lastPrice``(문자열), ``currency``.
    등락률/전일종가는 제공되지 않는다(캔들로 계산 — Wave 3).
    """

    symbol: str
    last_price: float
    currency: str | None = None
    timestamp: datetime | None = None


class TossCandle(CamelModel):
    """``GET /api/v1/candles`` 의 ``result.candles[]`` 원소.

    스펙 필드: ``timestamp``, ``openPrice``, ``highPrice``, ``lowPrice``,
    ``closePrice``, ``volume``, ``currency``. camelCase 자동 alias 와 다른
    이름이라 명시적으로 매핑한다.
    """

    time: datetime = Field(alias="timestamp")
    open: float = Field(alias="openPrice")
    high: float = Field(alias="highPrice")
    low: float = Field(alias="lowPrice")
    close: float = Field(alias="closePrice")
    volume: float | None = None


# ── 클라이언트 ────────────────────────────────────────────────────────────────


class TossClient:
    """토스증권 Open API 단일 진입점(토큰 단일 관리자 포함).

    Parameters
    ----------
    app_key, app_secret:
        OAuth2 client_credentials 자격(설정에 저장된 키).
    transport:
        httpx 트랜스포트 주입(테스트에서 ``httpx.MockTransport`` 사용). None 이면
        실 네트워크.
    clock:
        단조 시계 주입(만료 판정용). 테스트에서 결정적으로 만료를 흉내.
    sleep:
        비동기 대기 함수 주입(429 백오프). 테스트에서 실제 대기 없이 기록만.
    """

    def __init__(
        self,
        app_key: str,
        app_secret: str,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        clock: ClockFn = time.monotonic,
        sleep: SleepFn = asyncio.sleep,
    ) -> None:
        self._app_key = app_key
        self._app_secret = app_secret
        self._clock = clock
        self._sleep = sleep
        self._client = httpx.AsyncClient(
            base_url=_BASE_URL,
            timeout=_TIMEOUT,
            transport=transport,
        )
        self._token: str | None = None
        self._expires_at: float | None = None
        self._lock = asyncio.Lock()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> TossClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.aclose()

    # ── 토큰 관리 ────────────────────────────────────────────────────────────

    async def _ensure_token(self) -> str:
        """유효 토큰을 반환(만료 임박/없음이면 재발급)."""
        token = self._token
        if (
            token is not None
            and self._expires_at is not None
            and self._clock() < self._expires_at
        ):
            return token
        return await self._refresh(token)

    async def _refresh(self, previous: str | None) -> str:
        """토큰 재발급(직렬화 + double-check).

        ``previous`` 는 재발급을 촉발한(만료됐거나 401 을 받은) 토큰이다. 락을
        잡은 뒤, 다른 코루틴이 이미 ``previous`` 와 다른 유효 토큰으로 바꿔놨다면
        재발급하지 않고 그 토큰을 쓴다 — 그래야 중복 재발급으로 서로를
        무효화하지 않는다(1토큰 제약).
        """
        async with self._lock:
            current = self._token
            if (
                current is not None
                and current != previous
                and self._expires_at is not None
                and self._clock() < self._expires_at
            ):
                return current
            access_token, expires_in = await self._request_token()
            self._token = access_token
            self._expires_at = self._clock() + float(expires_in) - _EXPIRY_MARGIN
            return access_token

    async def _request_token(self) -> tuple[str, int]:
        """``POST /oauth2/token`` (form). 응답은 표준 OAuth 평문."""
        resp = await self._client.post(
            "/oauth2/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self._app_key,
                "client_secret": self._app_secret,
            },
        )
        resp.raise_for_status()
        payload = resp.json()
        return str(payload["access_token"]), int(payload["expires_in"])

    # ── 요청 실행 (401 재발급·429 백오프) ────────────────────────────────────

    async def _call(
        self,
        method: str,
        path: str,
        *,
        token: str,
        account_seq: int | str | None,
        params: dict[str, str] | None,
    ) -> httpx.Response:
        headers = {"Authorization": f"Bearer {token}"}
        if account_seq is not None:
            # 계좌 계열 엔드포인트는 accountSeq 헤더 필요.
            headers["X-Tossinvest-Account"] = str(account_seq)
        return await self._client.request(method, path, headers=headers, params=params)

    async def _request(
        self,
        method: str,
        path: str,
        *,
        account_seq: int | str | None = None,
        params: dict[str, str] | None = None,
    ) -> Any:
        """인증 요청 실행 → ``result`` payload(JSON) 반환.

        401 은 강제 재발급 후 1회, 429 는 Retry-After 대기 후 1회 재시도한다.
        그래도 실패하면 ``raise_for_status`` 로 예외 전파(§0 — 삼키지 않음).
        """
        token = await self._ensure_token()
        did_refresh = False
        did_backoff = False
        while True:
            resp = await self._call(
                method, path, token=token, account_seq=account_seq, params=params
            )
            if resp.status_code == 401 and not did_refresh:
                did_refresh = True
                token = await self._refresh(token)
                continue
            if resp.status_code == 429 and not did_backoff:
                did_backoff = True
                await self._sleep(_retry_after_seconds(resp))
                continue
            resp.raise_for_status()
            return resp.json()

    # ── 공개 메서드 ──────────────────────────────────────────────────────────

    async def get_accounts(self) -> list[TossAccount]:
        payload = await self._request("GET", "/api/v1/accounts")
        return [TossAccount.model_validate(item) for item in _as_list(payload)]

    async def get_holdings(self, account_seq: int | str) -> list[TossHolding]:
        payload = await self._request(
            "GET", "/api/v1/holdings", account_seq=account_seq
        )
        result = _as_dict(payload)
        return [TossHolding.model_validate(item) for item in _seq(result.get("items"))]

    async def get_closed_orders(
        self,
        account_seq: int | str,
        from_: str | None = None,
        to: str | None = None,
        cursor: str | None = None,
    ) -> TossOrderPage:
        params: dict[str, str] = {"status": "CLOSED"}
        if from_ is not None:
            params["from"] = from_
        if to is not None:
            params["to"] = to
        if cursor is not None:
            params["cursor"] = cursor
        payload = await self._request(
            "GET", "/api/v1/orders", account_seq=account_seq, params=params
        )
        return TossOrderPage.model_validate(_as_dict(payload))

    async def get_order(self, account_seq: int | str, order_id: str) -> TossOrderDetail:
        # ★ 미확인(공식 문서 대조 2026-07): 개요 문서 산문엔 "orderId로 상세
        # 조회 가능"이라 적혀 있으나, 실제 OpenAPI 스펙(paths)에는 이 경로가
        # 안 보인다(문서 자체의 내부 불일치로 보임 — 진짜 404 인지 실키로
        # 확인 필요). toss_sync.py 는 이 메서드를 쓰지 않는다(주문 목록
        # 응답의 중첩 execution 필드만으로 처리) — 실사용 영향 없음.
        payload = await self._request(
            "GET", f"/api/v1/orders/{order_id}", account_seq=account_seq
        )
        return TossOrderDetail.model_validate(_as_dict(payload))

    async def get_prices(self, symbols: Sequence[str]) -> list[TossPrice]:
        params = {"symbols": ",".join(symbols)}
        payload = await self._request("GET", "/api/v1/prices", params=params)
        return [TossPrice.model_validate(item) for item in _as_list(payload)]

    async def get_candles(
        self, symbol: str, interval: Literal["1d", "1m"], count: int
    ) -> list[TossCandle]:
        params = {"symbol": symbol, "interval": interval, "count": str(count)}
        payload = await self._request("GET", "/api/v1/candles", params=params)
        result = _as_dict(payload)
        return [TossCandle.model_validate(item) for item in _seq(result.get("candles"))]


# ── 헬퍼 ──────────────────────────────────────────────────────────────────────


def _retry_after_seconds(resp: httpx.Response) -> float:
    """``Retry-After`` 헤더(초)를 float 로. 없거나 HTTP-date 면 기본값."""
    raw = resp.headers.get("Retry-After")
    if raw is None:
        return _DEFAULT_RETRY_AFTER
    try:
        return float(raw)
    except ValueError:
        # HTTP-date 형식은 이 클라이언트에서 지원하지 않음 → 보수적 기본 대기.
        return _DEFAULT_RETRY_AFTER


def _as_list(payload: Any) -> list[Any]:
    """``{"result": [...]}`` → 리스트(방어적)."""
    result = payload.get("result") if isinstance(payload, dict) else None
    return result if isinstance(result, list) else []


def _as_dict(payload: Any) -> dict[str, Any]:
    """``{"result": {...}}`` → dict(방어적)."""
    result = payload.get("result") if isinstance(payload, dict) else None
    return result if isinstance(result, dict) else {}


def _seq(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []
