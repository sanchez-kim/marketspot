"""yfinance 뉴스 파서 테스트 — 신구 구조 모두(네트워크 없음)."""

from __future__ import annotations

from app.providers.news_provider import parse_news_item


def test_parses_new_structure() -> None:
    raw = {
        "id": "abc",
        "content": {
            "title": "Broadcom's sell-off enters history",
            "summary": "Erasing $320 billion in value.",
            "pubDate": "2026-06-04T16:39:42Z",
            "provider": {"displayName": "Yahoo Finance"},
            "clickThroughUrl": {"url": "https://finance.yahoo.com/article"},
        },
    }
    item = parse_news_item(raw, fallback_ticker="avgo")
    assert item is not None
    assert item.title.startswith("Broadcom")
    assert item.publisher == "Yahoo Finance"
    assert item.link == "https://finance.yahoo.com/article"
    assert item.published is not None
    assert item.published.year == 2026
    assert item.tickers == ["AVGO"]  # 소스에 티커 없으면 요청 심볼로 보강


def test_parses_old_flat_structure() -> None:
    raw = {
        "uuid": "x1",
        "title": "Old format news",
        "publisher": "Reuters",
        "link": "https://example.com/n",
        "providerPublishTime": 1_700_000_000,
        "relatedTickers": ["AAPL", "MSFT"],
    }
    item = parse_news_item(raw, fallback_ticker="aapl")
    assert item is not None
    assert item.publisher == "Reuters"
    assert item.link == "https://example.com/n"
    assert item.published is not None
    assert item.tickers == ["AAPL", "MSFT"]


def test_missing_title_returns_none() -> None:
    assert parse_news_item({"content": {"summary": "no title"}}, "x") is None
