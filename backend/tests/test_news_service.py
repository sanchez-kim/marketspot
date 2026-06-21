"""뉴스/AI 서비스 폴백 테스트 (네트워크 없음).

★ 핵심: AI 가 실패하거나 미가동이어도 규칙기반으로 폴백해 항상 동작한다
(REQUIREMENTS FR-2,4).
"""

from __future__ import annotations

import pytest

from app.ai.base import AIBackend
from app.config import AISettings, Settings
from app.models import (
    AnalyzedNews,
    Importance,
    NewsAnalysis,
    NewsItem,
    Sentiment,
)
from app.services.news import NewsAIService

from .fakes import FakeNewsProvider, RaisingBackend


class _CountingOllama:
    """ollama 로 위장한 가짜 백엔드 — 호출 횟수를 센다(캐시 검증용)."""

    name = "ollama"

    def __init__(self) -> None:
        self.calls = 0

    async def summarize_news(self, items: list[NewsItem]) -> list[AnalyzedNews]:
        self.calls += 1
        return [
            AnalyzedNews(
                item=i,
                analysis=NewsAnalysis(
                    sentiment=Sentiment.NEUTRAL,
                    importance=Importance.LOW,
                    tickers=i.tickers,
                    korean_summary="요약",
                ),
            )
            for i in items
        ]

    async def ask(self, context: str, question: str) -> str:
        return "답변"


_ITEMS = [
    NewsItem(id="1", title="Stock surges on strong earnings", tickers=["AAPL"]),
    NewsItem(id="2", title="Shares plunge after downgrade", tickers=["XYZ"]),
]


def _rule_settings() -> Settings:
    return Settings(ai=AISettings(backend="rule"))


@pytest.mark.asyncio
async def test_summarize_uses_rule_backend_when_configured() -> None:
    svc = NewsAIService(
        provider=FakeNewsProvider(_ITEMS), settings_loader=_rule_settings
    )
    result = await svc.summarize("AAPL")
    assert result.backend == "rule"
    assert len(result.items) == 2
    assert result.items[0].analysis.korean_summary  # 분석이 채워짐


@pytest.mark.asyncio
async def test_summarize_empty_when_no_news() -> None:
    svc = NewsAIService(provider=FakeNewsProvider([]), settings_loader=_rule_settings)
    result = await svc.summarize("AAPL")
    assert result.backend == "none"
    assert result.items == []


@pytest.mark.asyncio
async def test_summarize_falls_back_when_ai_raises() -> None:
    """선택된 백엔드가 예외를 던지면 규칙기반으로 폴백한다."""

    class FallbackService(NewsAIService):
        async def _choose_backend(self) -> AIBackend:
            return RaisingBackend()

    svc = FallbackService(
        provider=FakeNewsProvider(_ITEMS), settings_loader=_rule_settings
    )
    result = await svc.summarize("AAPL")
    assert result.backend == "rule"  # boom 이 아니라 rule
    assert len(result.items) == 2


@pytest.mark.asyncio
async def test_ask_falls_back_when_ai_raises() -> None:
    class FallbackService(NewsAIService):
        async def _choose_backend(self) -> AIBackend:
            return RaisingBackend()

    svc = FallbackService(
        provider=FakeNewsProvider(_ITEMS), settings_loader=_rule_settings
    )
    result = await svc.ask("맥락", "질문")
    assert result.backend == "rule"
    assert result.answer


# ── 캐싱 (탭 재진입 시 재조회 방지) ─────────────────────────────────
class _Clock:
    """주입 가능한 단조 시계 — sleep 없이 만료를 테스트한다(CLAUDE.md §1.3)."""

    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


@pytest.mark.asyncio
async def test_get_news_is_cached_within_ttl() -> None:
    provider = FakeNewsProvider(_ITEMS)
    svc = NewsAIService(
        provider=provider, settings_loader=_rule_settings, clock=_Clock()
    )
    await svc.get_news("AAPL")
    await svc.get_news("AAPL")
    assert provider.calls == 1  # 두 번째는 캐시에서


@pytest.mark.asyncio
async def test_get_news_refetches_after_ttl_expires() -> None:
    provider = FakeNewsProvider(_ITEMS)
    clock = _Clock()
    svc = NewsAIService(provider=provider, settings_loader=_rule_settings, clock=clock)
    await svc.get_news("AAPL")
    clock.now += 301.0  # _NEWS_TTL(300) 초과
    await svc.get_news("AAPL")
    assert provider.calls == 2


@pytest.mark.asyncio
async def test_error_status_is_not_cached() -> None:
    """데이터 없음/에러는 캐시하지 않아 다음 호출이 재시도한다."""
    provider = FakeNewsProvider([])  # NO_DATA
    svc = NewsAIService(
        provider=provider, settings_loader=_rule_settings, clock=_Clock()
    )
    await svc.get_news("AAPL")
    await svc.get_news("AAPL")
    assert provider.calls == 2


@pytest.mark.asyncio
async def test_summarize_caches_ai_result() -> None:
    provider = FakeNewsProvider(_ITEMS)
    backend = _CountingOllama()

    class Svc(NewsAIService):
        async def _choose_backend(self) -> AIBackend:
            return backend

    svc = Svc(provider=provider, settings_loader=_rule_settings, clock=_Clock())
    first = await svc.summarize("AAPL")
    second = await svc.summarize("AAPL")
    assert first == second
    assert backend.calls == 1  # 두 번째는 캐시 → AI 재호출 안 함
    assert provider.calls == 1


@pytest.mark.asyncio
async def test_digest_summarizes_important_news_and_caches() -> None:
    provider = FakeNewsProvider(_ITEMS)
    backend = _CountingOllama()

    class Svc(NewsAIService):
        async def _choose_backend(self) -> AIBackend:
            return backend

    svc = Svc(provider=provider, settings_loader=_rule_settings, clock=_Clock())
    first = await svc.digest(["AAPL", "QQQM"], top=6)
    assert first.backend == "ollama"
    assert len(first.items) >= 1  # 중요 뉴스가 요약됨
    await svc.digest(["AAPL", "QQQM"], top=6)
    assert backend.calls == 1  # 두 번째는 캐시


@pytest.mark.asyncio
async def test_item_analyses_reused_across_calls() -> None:
    """같은 기사는 재요약하지 않는다 — summarize 후 digest 가 항목 캐시를 재사용."""
    provider = FakeNewsProvider(_ITEMS)
    backend = _CountingOllama()

    class Svc(NewsAIService):
        async def _choose_backend(self) -> AIBackend:
            return backend

    svc = Svc(provider=provider, settings_loader=_rule_settings, clock=_Clock())
    await svc.summarize("AAPL")  # 기사 1,2 요약 → backend 1회
    # 다이제스트(다른 심볼이지만 FakeNewsProvider 가 같은 기사 반환) → 항목 캐시 재사용
    await svc.digest(["QQQM"])
    assert backend.calls == 1  # 새 AI 호출 없음


@pytest.mark.asyncio
async def test_only_new_items_summarized() -> None:
    """기사 일부만 새로 생기면 그 기사만 AI 호출한다."""
    item1 = NewsItem(id="1", title="Old earnings beat", tickers=["AAPL"])
    item2 = NewsItem(id="2", title="New merger news", tickers=["AAPL"])
    backend = _CountingOllama()

    class Svc(NewsAIService):
        async def _choose_backend(self) -> AIBackend:
            return backend

    svc = Svc(
        provider=FakeNewsProvider([item1]),
        settings_loader=_rule_settings,
        clock=_Clock(),
    )
    await svc._summarize_items([item1])  # 1건 요약
    res = await svc._summarize_items([item1, item2])  # 1은 캐시, 2만 신규
    assert backend.calls == 2  # 두 번째 호출에서 새 기사 1건만
    assert len(res.items) == 2


@pytest.mark.asyncio
async def test_digest_empty_for_no_symbols() -> None:
    svc = NewsAIService(
        provider=FakeNewsProvider(_ITEMS), settings_loader=_rule_settings
    )
    result = await svc.digest([])
    assert result.backend == "none"
    assert result.items == []


@pytest.mark.asyncio
async def test_rule_fallback_is_not_cached_and_retries_ai() -> None:
    """일시적 Ollama 장애로 rule 폴백해도 캐시 오염 없이 다음에 AI 재시도한다."""
    provider = FakeNewsProvider(_ITEMS)
    backend = _CountingOllama()
    state = {"fail": True}

    class Svc(NewsAIService):
        async def _choose_backend(self) -> AIBackend:
            return RaisingBackend() if state["fail"] else backend

    svc = Svc(provider=provider, settings_loader=_rule_settings, clock=_Clock())
    first = await svc.summarize("AAPL")
    assert first.backend == "rule"  # 폴백(캐시 안 됨)

    state["fail"] = False
    second = await svc.summarize("AAPL")
    assert second.backend == "ollama"  # 오염되지 않아 AI 로 재시도됨
