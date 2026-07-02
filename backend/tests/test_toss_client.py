"""TossClient 코어 테스트 (결정적 — 실네트워크·실sleep 금지).

httpx.MockTransport 로 응답을 흉내내고, 클럭·sleep 을 주입해 토큰 수명·Lock
직렬화·401 복구·429 백오프를 검증한다(CLAUDE.md §1.3). 필드 매핑은 OpenAPI
스펙 기준 alias 로 파싱되는지 확인한다.
"""

from __future__ import annotations

import asyncio

import httpx
import pytest

from app.providers.toss_client import (
    TossClient,
    _retry_after_seconds,
)


class FakeClock:
    """주입용 단조 시계 — 테스트가 시간을 직접 전진시킨다."""

    def __init__(self, start: float = 1000.0) -> None:
        self.t = start

    def __call__(self) -> float:
        return self.t

    def advance(self, dt: float) -> None:
        self.t += dt


class SleepSpy:
    """주입용 sleep — 실제로 대기하지 않고 호출 인자만 기록."""

    def __init__(self) -> None:
        self.calls: list[float] = []

    async def __call__(self, seconds: float) -> None:
        self.calls.append(seconds)


def _token_response(counter: list[int], expires_in: int) -> httpx.Response:
    counter[0] += 1
    return httpx.Response(
        200,
        json={
            "access_token": f"tok-{counter[0]}",
            "token_type": "Bearer",
            "expires_in": expires_in,
        },
    )


def _make_client(
    handler: httpx.MockTransport,
    *,
    clock: FakeClock | None = None,
    sleep: SleepSpy | None = None,
) -> TossClient:
    return TossClient(
        "app-key",
        "app-secret",
        transport=handler,
        clock=clock or FakeClock(),
        sleep=sleep or SleepSpy(),
    )


# ── 토큰 캐시 / 만료 재발급 ───────────────────────────────────────────────────


async def test_token_cached_then_reissued_on_expiry() -> None:
    clock = FakeClock()
    token_count = [0]

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/oauth2/token":
            return _token_response(token_count, expires_in=100)
        assert request.url.path == "/api/v1/accounts"
        return httpx.Response(200, json={"result": []})

    client = _make_client(httpx.MockTransport(handler), clock=clock)
    try:
        await client.get_accounts()
        assert token_count[0] == 1  # 최초 발급
        await client.get_accounts()
        assert token_count[0] == 1  # 만료 전 → 캐시 재사용

        # expires_in=100, 여유 60초 → 40초 후 만료. 41초 전진.
        clock.advance(41)
        await client.get_accounts()
        assert token_count[0] == 2  # 만료 → 재발급
    finally:
        await client.aclose()


# ── 동시 요청 시 토큰 발급 1회 (Lock 직렬화) ─────────────────────────────────


async def test_concurrent_requests_issue_token_once() -> None:
    """5개 동시 요청이 토큰을 1회만 발급받는지 — 진짜 동시 진입을 강제한다.

    ``httpx.MockTransport`` 의 **동기** 핸들러는 이벤트 루프에 양보하지 않는다
    — 그래서 예전 버전처럼 동기 핸들러를 쓰면 gather 의 첫 태스크가 완전히
    끝날 때까지(토큰이 캐시될 때까지) 나머지 태스크가 아예 시작되지 않아,
    전부 fast path 만 타고 ``_refresh`` 의 락/double-check 경로가 한 번도
    실행되지 않는 "가짜 동시성" 테스트가 된다(락을 no-op 으로 바꿔도 통과).

    이를 막기 위해 토큰 핸들러를 **async** 로 만들고 ``asyncio.Event`` 로 첫
    응답을 게이트한다. 태스크를 만든 직후 게이트를 닫아둔 채 ``sleep(0)`` 으로
    여러 스케줄링 틱만큼 양보시키면(실sleep 아님 — 결정적):
    - 락이 올바르면: 태스크1 만 핸들러 안에서 게이트를 기다리고, 나머지 4개는
      ``asyncio.Lock`` 앞에서 **진짜로** 블록된다(핸들러 근처에도 못 감).
    - 락이 no-op 이면: 5개 전부 락에 걸리지 않고 핸들러까지 도달해 동시에
      게이트를 기다린다.

    따라서 핸들러 안 동시 체류 하이워터마크(``highwater``)가 오버랩의 직접
    증거다: 올바른 락이면 항상 1, no-op 이면 5로 관측된다 — 락을 no-op 으로
    바꾸면 이 테스트는 반드시 실패한다.
    """
    token_count = [0]
    gate = asyncio.Event()
    concurrent_in_handler = [0]
    highwater = [0]

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/oauth2/token":
            concurrent_in_handler[0] += 1
            highwater[0] = max(highwater[0], concurrent_in_handler[0])
            await gate.wait()  # 첫 응답을 게이트가 열릴 때까지 지연.
            concurrent_in_handler[0] -= 1
            return _token_response(token_count, expires_in=86400)
        return httpx.Response(200, json={"result": []})

    client = _make_client(httpx.MockTransport(handler))
    try:
        tasks = [asyncio.create_task(client.get_accounts()) for _ in range(5)]
        # 게이트가 닫힌 채로 여러 스케줄링 틱을 진행시켜, 락이 정상이면
        # 나머지 4개가 _refresh 의 락 앞에서 실제로 블록되도록 한다.
        for _ in range(20):
            await asyncio.sleep(0)
        # 오버랩 부재의 증거: 게이트가 열리기 전, 핸들러 안에 동시에 있던
        # 태스크는 최대 1개뿐이었다(나머지는 asyncio.Lock 대기 중).
        assert highwater[0] == 1
        gate.set()
        await asyncio.gather(*tasks)
        # 1토큰 제약: 5개가 동시에 재발급하지 않고 정확히 1번만 발급.
        assert token_count[0] == 1
    finally:
        await client.aclose()


# ── 401 → 강제 재발급 후 1회 재시도 복구 ─────────────────────────────────────


async def test_401_forces_reissue_and_retries_once() -> None:
    token_count = [0]
    accounts_calls = [0]

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/oauth2/token":
            return _token_response(token_count, expires_in=86400)
        accounts_calls[0] += 1
        auth = request.headers.get("Authorization")
        # 첫 토큰(tok-1)은 외부에서 무효화된 것처럼 401. 재발급된 tok-2 는 200.
        if auth == "Bearer tok-1":
            return httpx.Response(401, json={"message": "invalid token"})
        return httpx.Response(
            200,
            json={
                "result": [
                    {"accountNo": "1", "accountSeq": 7, "accountType": "BROKERAGE"}
                ]
            },
        )

    client = _make_client(httpx.MockTransport(handler))
    try:
        accounts = await client.get_accounts()
        assert token_count[0] == 2  # 강제 재발급 1회
        assert accounts_calls[0] == 2  # 401 후 재시도 1회
        assert accounts[0].account_seq == 7
    finally:
        await client.aclose()


async def test_persistent_401_raises() -> None:
    """계속 401 이면(그래도 실패) 예외 전파 — 삼키지 않음(§0)."""
    token_count = [0]

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/oauth2/token":
            return _token_response(token_count, expires_in=86400)
        return httpx.Response(401, json={"message": "nope"})

    client = _make_client(httpx.MockTransport(handler))
    try:
        with pytest.raises(httpx.HTTPStatusError):
            await client.get_accounts()
    finally:
        await client.aclose()


# ── 429 → Retry-After 대기 후 1회 재시도 ─────────────────────────────────────


async def test_429_waits_retry_after_then_succeeds() -> None:
    token_count = [0]
    sleep = SleepSpy()
    state = {"served_429": False}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/oauth2/token":
            return _token_response(token_count, expires_in=86400)
        if not state["served_429"]:
            state["served_429"] = True
            return httpx.Response(429, headers={"Retry-After": "3"}, json={})
        return httpx.Response(200, json={"result": []})

    client = _make_client(httpx.MockTransport(handler), sleep=sleep)
    try:
        result = await client.get_accounts()
        assert result == []
        # 주입된 sleep 이 Retry-After(3초)만큼 정확히 1회 호출됐는지.
        assert sleep.calls == [3.0]
    finally:
        await client.aclose()


def test_retry_after_parsing() -> None:
    def resp(headers: dict[str, str]) -> httpx.Response:
        return httpx.Response(429, headers=headers)

    assert _retry_after_seconds(resp({"Retry-After": "5"})) == 5.0
    # 헤더 없음 → 보수적 기본값(1초).
    assert _retry_after_seconds(resp({})) == 1.0
    # HTTP-date 형식(미지원) → 기본값.
    assert (
        _retry_after_seconds(resp({"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"}))
        == 1.0
    )


# ── 계좌 헤더(X-Tossinvest-Account) 포함 확인 ────────────────────────────────


async def test_account_scoped_endpoint_sends_account_header() -> None:
    token_count = [0]
    seen: dict[str, str | None] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/oauth2/token":
            return _token_response(token_count, expires_in=86400)
        seen["account"] = request.headers.get("X-Tossinvest-Account")
        return httpx.Response(200, json={"result": {"items": []}})

    client = _make_client(httpx.MockTransport(handler))
    try:
        await client.get_holdings(42)
        assert seen["account"] == "42"
    finally:
        await client.aclose()


async def test_non_account_endpoint_omits_account_header() -> None:
    token_count = [0]
    seen: dict[str, bool] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/oauth2/token":
            return _token_response(token_count, expires_in=86400)
        seen["has_header"] = "X-Tossinvest-Account" in request.headers
        return httpx.Response(200, json={"result": []})

    client = _make_client(httpx.MockTransport(handler))
    try:
        await client.get_prices(["005930"])
        assert seen["has_header"] is False
    finally:
        await client.aclose()


# ── 필드 매핑 파싱 (OpenAPI 스펙 alias) ──────────────────────────────────────


def _static_client(payload: dict[str, object]) -> TossClient:
    token_count = [0]

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/oauth2/token":
            return _token_response(token_count, expires_in=86400)
        return httpx.Response(200, json=payload)

    return _make_client(httpx.MockTransport(handler))


async def test_holdings_parses_items_and_coerces_numeric_strings() -> None:
    client = _static_client(
        {
            "result": {
                "items": [
                    {
                        "symbol": "005930",
                        "name": "삼성전자",
                        "quantity": "10",
                        "averagePurchasePrice": "70000",
                        "currency": "KRW",
                        "lastPrice": "72000",
                    }
                ]
            }
        }
    )
    try:
        holdings = await client.get_holdings(1)
        assert len(holdings) == 1
        h = holdings[0]
        assert h.symbol == "005930"
        assert h.name == "삼성전자"
        assert h.quantity == 10.0
        assert h.average_purchase_price == 70000.0
        assert h.last_price == 72000.0
    finally:
        await client.aclose()


async def test_prices_parses_string_last_price_and_timestamp() -> None:
    client = _static_client(
        {
            "result": [
                {
                    "symbol": "005930",
                    "timestamp": "2026-03-25T09:30:00.123+09:00",
                    "lastPrice": "72000",
                    "currency": "KRW",
                }
            ]
        }
    )
    try:
        prices = await client.get_prices(["005930"])
        assert len(prices) == 1
        assert prices[0].last_price == 72000.0
        assert prices[0].timestamp is not None
        assert prices[0].timestamp.year == 2026
    finally:
        await client.aclose()


async def test_candles_maps_ohlc_aliases() -> None:
    client = _static_client(
        {
            "result": {
                "candles": [
                    {
                        "timestamp": "2026-03-25T00:00:00+09:00",
                        "openPrice": "100",
                        "highPrice": "110",
                        "lowPrice": "95",
                        "closePrice": "105",
                        "volume": "1234",
                        "currency": "KRW",
                    }
                ],
                "nextBefore": None,
            }
        }
    )
    try:
        candles = await client.get_candles("005930", "1d", 2)
        assert len(candles) == 1
        c = candles[0]
        assert c.open == 100.0
        assert c.high == 110.0
        assert c.low == 95.0
        assert c.close == 105.0
        assert c.volume == 1234.0
        assert c.time.year == 2026
    finally:
        await client.aclose()


async def test_closed_orders_parses_page_and_execution() -> None:
    client = _static_client(
        {
            "result": {
                "orders": [
                    {
                        "orderId": "ord-1",
                        "symbol": "005930",
                        "side": "BUY",
                        "status": "CLOSED",
                        "currency": "KRW",
                        "orderedAt": "2026-03-25T09:30:00+09:00",
                        "execution": {
                            "filledQuantity": "5",
                            "averageFilledPrice": "71000",
                            "commission": "100",
                            "tax": "0",
                            "filledAt": "2026-03-25T09:31:00+09:00",
                        },
                    }
                ],
                "nextCursor": "cursor-2",
                "hasNext": True,
            }
        }
    )
    try:
        page = await client.get_closed_orders(1, from_="2026-01-01")
        assert page.next_cursor == "cursor-2"
        assert len(page.orders) == 1
        order = page.orders[0]
        assert order.order_id == "ord-1"
        assert order.side == "BUY"
        assert order.execution is not None
        assert order.execution.filled_quantity == 5.0
        assert order.execution.average_filled_price == 71000.0
        assert order.execution.commission == 100.0
    finally:
        await client.aclose()


async def test_closed_orders_forwards_query_params() -> None:
    token_count = [0]
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/oauth2/token":
            return _token_response(token_count, expires_in=86400)
        seen.update(dict(request.url.params))
        return httpx.Response(200, json={"result": {"orders": [], "nextCursor": None}})

    client = _make_client(httpx.MockTransport(handler))
    try:
        await client.get_closed_orders(
            1, from_="2026-01-01", to="2026-02-01", cursor="c1"
        )
        assert seen["status"] == "CLOSED"
        assert seen["from"] == "2026-01-01"
        assert seen["to"] == "2026-02-01"
        assert seen["cursor"] == "c1"
    finally:
        await client.aclose()


async def test_get_order_detail() -> None:
    client = _static_client(
        {
            "result": {
                "orderId": "ord-9",
                "symbol": "AAPL",
                "side": "SELL",
                "currency": "USD",
                "execution": {
                    "filledQuantity": "2",
                    "averageFilledPrice": "190.5",
                    "commission": "0.1",
                    "tax": "0.05",
                    "filledAt": "2026-03-25T10:00:00+09:00",
                },
            }
        }
    )
    try:
        detail = await client.get_order(1, "ord-9")
        assert detail.order_id == "ord-9"
        assert detail.side == "SELL"
        assert detail.execution is not None
        assert detail.execution.average_filled_price == 190.5
        assert detail.execution.tax == 0.05
    finally:
        await client.aclose()


async def test_accounts_parses_without_name_field() -> None:
    """스펙에 name 이 없어도 정상 파싱 — 지어내지 않음(§0)."""
    client = _static_client(
        {
            "result": [
                {
                    "accountNo": "12345678901",
                    "accountSeq": 1,
                    "accountType": "BROKERAGE",
                }
            ]
        }
    )
    try:
        accounts = await client.get_accounts()
        assert len(accounts) == 1
        assert accounts[0].account_seq == 1
        assert accounts[0].account_no == "12345678901"
        assert accounts[0].account_type == "BROKERAGE"
    finally:
        await client.aclose()
