"""규칙기반 AI 백엔드 테스트 (결정적, 네트워크 없음)."""

from __future__ import annotations

import pytest

from app.ai.rule_based import (
    RuleBasedBackend,
    analyze_item,
    extract_cashtags,
    rule_importance,
    rule_sentiment,
)
from app.models import Importance, NewsItem, Sentiment


def test_sentiment_positive() -> None:
    assert rule_sentiment("Stock surges to record high on strong profit") == (
        Sentiment.POSITIVE
    )


def test_sentiment_negative() -> None:
    assert rule_sentiment("Shares plunge after earnings miss and downgrade") == (
        Sentiment.NEGATIVE
    )


def test_sentiment_neutral_when_balanced_or_empty() -> None:
    assert rule_sentiment("Company holds annual meeting") == Sentiment.NEUTRAL
    # 긍정/부정 1:1 → 중립
    assert rule_sentiment("gain then loss") == Sentiment.NEUTRAL


def test_importance_high_on_keyword() -> None:
    assert rule_importance("Fed signals rate decision next week") == Importance.HIGH
    assert rule_importance("Company announces merger") == Importance.HIGH


def test_importance_low_without_signal() -> None:
    assert rule_importance("A quiet day for the company") == Importance.LOW


def test_extract_cashtags() -> None:
    assert extract_cashtags("Buying $AAPL and $NVDA today") == ["AAPL", "NVDA"]
    assert extract_cashtags("no tags here") == []


def test_analyze_item_preserves_original_title_and_tags() -> None:
    item = NewsItem(
        id="1",
        title="Nvidia shares surge on record AI demand",
        summary="Strong guidance beats estimates",
        tickers=["NVDA"],
    )
    analysis = analyze_item(item)
    assert analysis.sentiment == Sentiment.POSITIVE
    assert "NVDA" in analysis.tickers
    # 원문 제목을 보존(거짓 번역 금지)
    assert item.title in analysis.korean_summary
    assert "규칙기반" in analysis.korean_summary


@pytest.mark.asyncio
async def test_summarize_news_returns_per_item() -> None:
    items = [
        NewsItem(id="1", title="Stock jumps on strong earnings", tickers=["AAPL"]),
        NewsItem(id="2", title="Shares fall after probe", tickers=["XYZ"]),
    ]
    out = await RuleBasedBackend().summarize_news(items)
    assert len(out) == 2
    assert out[0].analysis.sentiment == Sentiment.POSITIVE
    assert out[1].analysis.sentiment == Sentiment.NEGATIVE


@pytest.mark.asyncio
async def test_ask_returns_korean_fallback_message() -> None:
    answer = await RuleBasedBackend().ask("맥락", "지금 사도 돼?")
    assert "규칙기반" in answer
    assert isinstance(answer, str) and answer
