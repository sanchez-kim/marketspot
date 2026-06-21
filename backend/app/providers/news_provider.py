"""뉴스 제공자 (yfinance `.news`, 키 불필요).

yfinance 뉴스 구조는 버전에 따라 다르다. 신구 구조를 모두 방어적으로
파싱한다. 실패 시 가짜 데이터 대신 빈/에러 상태를 반환한다.
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Protocol, runtime_checkable

from ..models import DataEnvelope, DataStatus, NewsItem

JsonDict = Mapping[str, object]


@runtime_checkable
class NewsProvider(Protocol):
    name: str

    async def get_news(
        self, symbol: str, limit: int = 20
    ) -> DataEnvelope[list[NewsItem]]: ...


class YFinanceNewsProvider:
    name = "yfinance-news"

    async def get_news(
        self, symbol: str, limit: int = 20
    ) -> DataEnvelope[list[NewsItem]]:
        try:
            import yfinance as yf
        except ImportError:
            return DataEnvelope[list[NewsItem]].empty(
                source=self.name,
                status=DataStatus.ERROR,
                message="yfinance 미설치",
            )

        try:
            # 동기 yfinance → 스레드로 오프로드(이벤트 루프 비차단)
            raw = await asyncio.to_thread(lambda: yf.Ticker(symbol).news or [])
        except Exception as exc:  # noqa: BLE001
            return DataEnvelope[list[NewsItem]].empty(
                source=self.name,
                status=DataStatus.ERROR,
                message=f"뉴스 조회 실패: {exc}",
            )

        parsed = [parse_news_item(r, symbol) for r in raw[:limit]]
        items = [i for i in parsed if i is not None]
        if not items:
            return DataEnvelope[list[NewsItem]].empty(
                source=self.name,
                status=DataStatus.NO_DATA,
                message=f"'{symbol}' 관련 뉴스가 없습니다",
            )
        # 뉴스는 본질적으로 지연 데이터
        return DataEnvelope.ok(items, source=self.name, status=DataStatus.DELAYED)


def parse_news_item(raw: JsonDict, fallback_ticker: str) -> NewsItem | None:
    """yfinance 뉴스 dict → NewsItem. 신구 구조 모두 처리."""
    content_obj = raw.get("content")
    content: JsonDict = content_obj if isinstance(content_obj, dict) else raw

    title = content.get("title")
    if not isinstance(title, str) or not title:
        return None

    raw_id = raw.get("id") or content.get("id") or title
    summary = content.get("summary") or content.get("description") or ""

    return NewsItem(
        id=str(raw_id),
        title=title,
        summary=summary if isinstance(summary, str) else "",
        publisher=_publisher(content),
        link=_link(content),
        published=_published(content),
        tickers=_tickers(content, fallback_ticker),
    )


def _publisher(content: JsonDict) -> str | None:
    prov = content.get("provider")
    if isinstance(prov, dict):
        name = prov.get("displayName")
        if isinstance(name, str):
            return name
    pub = content.get("publisher")  # 구 구조
    return pub if isinstance(pub, str) else None


def _link(content: JsonDict) -> str | None:
    for key in ("clickThroughUrl", "canonicalUrl"):
        v = content.get(key)
        if isinstance(v, dict):
            url = v.get("url")
            if isinstance(url, str):
                return url
    link = content.get("link")  # 구 구조
    return link if isinstance(link, str) else None


def _published(content: JsonDict) -> datetime | None:
    # 신 구조: ISO 문자열 pubDate
    for key in ("pubDate", "displayTime"):
        v = content.get(key)
        if isinstance(v, str):
            try:
                return datetime.fromisoformat(v.replace("Z", "+00:00"))
            except ValueError:
                continue
    # 구 구조: providerPublishTime (epoch 초)
    epoch = content.get("providerPublishTime")
    if isinstance(epoch, (int, float)):
        return datetime.fromtimestamp(epoch, tz=UTC)
    return None


def _tickers(content: JsonDict, fallback_ticker: str) -> list[str]:
    raw_tickers = content.get("relatedTickers")
    if isinstance(raw_tickers, list):
        found = [str(t) for t in raw_tickers if isinstance(t, str)]
        if found:
            return found
    return [fallback_ticker.upper()]
