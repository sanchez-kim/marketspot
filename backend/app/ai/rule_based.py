"""규칙기반 AI 폴백.

키/모델 없이도 동작해야 한다(REQUIREMENTS FR-2,4). 영어→한국어 번역은
하지 않는다(거짓 번역 금지). 대신 감성/중요도/티커를 **정직하게 태깅**하고,
원문 제목을 그대로 보존한다. UI 는 backend="rule" 뱃지로 이를 표시한다.
"""

from __future__ import annotations

import re

from ..models import (
    AnalyzedNews,
    Importance,
    NewsAnalysis,
    NewsItem,
    Sentiment,
)

# 감성 사전 (소문자 매칭)
_POSITIVE = {
    "surge",
    "soar",
    "jump",
    "rally",
    "gain",
    "rise",
    "beat",
    "beats",
    "upgrade",
    "record",
    "strong",
    "boost",
    "profit",
    "growth",
    "bullish",
    "outperform",
    "high",
    "wins",
    "win",
    "raises",
    "soars",
    "rallies",
}
_NEGATIVE = {
    "fall",
    "drop",
    "plunge",
    "slump",
    "miss",
    "misses",
    "cut",
    "cuts",
    "downgrade",
    "weak",
    "loss",
    "losses",
    "decline",
    "warn",
    "warns",
    "lawsuit",
    "probe",
    "layoff",
    "layoffs",
    "bearish",
    "underperform",
    "sinks",
    "tumble",
    "tumbles",
    "selloff",
    "sell-off",
    "crash",
}
# 고중요도 키워드
_HIGH_IMPACT = {
    "earnings",
    "fed",
    "rate",
    "rates",
    "merger",
    "acquisition",
    "acquire",
    "guidance",
    "lawsuit",
    "sec",
    "recall",
    "bankruptcy",
    "ceo",
    "ipo",
    "dividend",
    "buyback",
    "antitrust",
}

_KR_SENTIMENT = {
    Sentiment.POSITIVE: "강세",
    Sentiment.NEUTRAL: "중립",
    Sentiment.NEGATIVE: "약세",
}
_KR_IMPORTANCE = {
    Importance.HIGH: "중요",
    Importance.MEDIUM: "보통",
    Importance.LOW: "낮음",
}

_WORD_RE = re.compile(r"[a-z][a-z\-]+")
_CASHTAG_RE = re.compile(r"\$([A-Z]{1,5})")


def _words(text: str) -> list[str]:
    return _WORD_RE.findall(text.lower())


def rule_sentiment(text: str) -> Sentiment:
    words = set(_words(text))
    pos = len(words & _POSITIVE)
    neg = len(words & _NEGATIVE)
    if pos > neg:
        return Sentiment.POSITIVE
    if neg > pos:
        return Sentiment.NEGATIVE
    return Sentiment.NEUTRAL


def rule_importance(text: str) -> Importance:
    words = set(_words(text))
    if words & _HIGH_IMPACT:
        return Importance.HIGH
    signal = len(words & _POSITIVE) + len(words & _NEGATIVE)
    return Importance.MEDIUM if signal >= 2 else Importance.LOW


def extract_cashtags(text: str) -> list[str]:
    return list(dict.fromkeys(_CASHTAG_RE.findall(text)))


def analyze_item(item: NewsItem) -> NewsAnalysis:
    text = f"{item.title} {item.summary}"
    sentiment = rule_sentiment(text)
    importance = rule_importance(text)
    tickers = list(dict.fromkeys([*item.tickers, *extract_cashtags(text)]))
    korean = (
        f"[{_KR_SENTIMENT[sentiment]}·{_KR_IMPORTANCE[importance]}] "
        f"규칙기반 태그 (원문): {item.title}"
    )
    return NewsAnalysis(
        sentiment=sentiment,
        importance=importance,
        tickers=tickers,
        korean_summary=korean,
    )


class RuleBasedBackend:
    name = "rule"

    async def summarize_news(self, items: list[NewsItem]) -> list[AnalyzedNews]:
        return [AnalyzedNews(item=i, analysis=analyze_item(i)) for i in items]

    async def ask(self, context: str, question: str) -> str:
        return (
            "로컬 AI(Ollama)가 연결되지 않아 규칙기반으로 답합니다.\n"
            f"질문: {question}\n\n"
            "현재 화면 맥락에서 핵심 수치만 정리해 드릴 수 있어요. "
            "더 깊은 한국어 분석을 원하시면 설정에서 Ollama 를 켜고 "
            "qwen3.5:9b-mlx 모델을 준비해 주세요."
        )
