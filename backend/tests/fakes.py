"""테스트용 가짜 Provider.

★ 검증 대상(폴백 로직/캐시 키)을 mock 으로 치워버리지 않는다(CLAUDE.md §1.2).
이 fake 는 *외부 네트워크* 만 대체하며, 레지스트리/서비스의 실제 로직은
그대로 실행된다.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.models import (
    AnalyzedNews,
    Bar,
    DataEnvelope,
    DataStatus,
    Filing,
    FilingList,
    NewsItem,
    Quote,
)


class FakeProvider:
    """호출 횟수를 세고, 미리 정한 응답을 돌려주는 제공자."""

    def __init__(
        self,
        name: str,
        *,
        quote_status: DataStatus = DataStatus.LIVE,
        bars_status: DataStatus = DataStatus.LIVE,
        raise_on_quote: bool = False,
    ) -> None:
        self.name = name
        self._quote_status = quote_status
        self._bars_status = bars_status
        self._raise_on_quote = raise_on_quote
        self.quote_calls = 0
        self.bars_calls = 0

    async def get_quote(self, symbol: str) -> DataEnvelope[Quote]:
        self.quote_calls += 1
        if self._raise_on_quote:
            raise RuntimeError("boom")
        if self._quote_status in (DataStatus.LIVE, DataStatus.DELAYED):
            return DataEnvelope.ok(
                Quote(symbol=symbol, price=100.0, change=1.0, change_pct=1.0),
                source=self.name,
                status=self._quote_status,
            )
        return DataEnvelope[Quote].empty(
            source=self.name, status=self._quote_status, message="no data"
        )

    async def get_bars(
        self, symbol: str, period: str, interval: str
    ) -> DataEnvelope[list[Bar]]:
        self.bars_calls += 1
        if self._bars_status in (DataStatus.LIVE, DataStatus.DELAYED, DataStatus.STALE):
            bars = _make_bars(40)
            return DataEnvelope.ok(
                bars,
                source=self.name,
                status=self._bars_status,
                as_of=bars[-1].time,
            )
        return DataEnvelope[list[Bar]].empty(
            source=self.name, status=self._bars_status, message="no data"
        )


class FakeNewsProvider:
    """미리 정한 뉴스 항목을 돌려주는 제공자(네트워크 없음)."""

    name = "fake-news"

    def __init__(self, items: list[NewsItem]) -> None:
        self._items = items
        self.calls = 0  # 캐시 동작 검증용 호출 카운터

    async def get_news(
        self, symbol: str, limit: int = 20
    ) -> DataEnvelope[list[NewsItem]]:
        self.calls += 1
        if not self._items:
            return DataEnvelope[list[NewsItem]].empty(
                source=self.name, status=DataStatus.NO_DATA
            )
        return DataEnvelope.ok(
            self._items[:limit], source=self.name, status=DataStatus.DELAYED
        )


class FakeFilingsProvider:
    """미리 정한 공시를 돌려주는 제공자(네트워크 없음)."""

    name = "fake-filings"

    def __init__(
        self,
        filings: list[Filing] | None = None,
        *,
        status: DataStatus = DataStatus.DELAYED,
        entity: str = "Fake Corp",
    ) -> None:
        self._filings = filings or []
        self._status = status
        self._entity = entity

    async def get_filings(
        self, symbol: str, limit: int = 20
    ) -> DataEnvelope[FilingList]:
        if self._status in (DataStatus.LIVE, DataStatus.DELAYED, DataStatus.STALE):
            data = FilingList(
                entity=self._entity,
                cik="0000000001",
                market="US",
                filings=self._filings[:limit],
            )
            return DataEnvelope.ok(data, source=self.name, status=self._status)
        return DataEnvelope[FilingList].empty(
            source=self.name, status=self._status, message="no data"
        )


class RaisingBackend:
    """항상 실패하는 AI 백엔드 — 폴백 경로 검증용."""

    name = "boom"

    async def summarize_news(self, items: list[NewsItem]) -> list[AnalyzedNews]:
        raise RuntimeError("ai down")

    async def ask(self, context: str, question: str) -> str:
        raise RuntimeError("ai down")


def _make_bars(n: int) -> list[Bar]:
    bars: list[Bar] = []
    for i in range(n):
        c = 100.0 + i
        bars.append(
            Bar(
                time=datetime(2026, 1, 1, tzinfo=UTC),
                open=c - 1,
                high=c + 1,
                low=c - 2,
                close=c,
                volume=1000.0,
            )
        )
    return bars
