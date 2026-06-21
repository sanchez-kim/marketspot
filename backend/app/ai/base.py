"""AI 백엔드 인터페이스."""

from __future__ import annotations

from typing import Protocol

from ..models import AnalyzedNews, NewsItem


class AIBackend(Protocol):
    name: str

    async def summarize_news(self, items: list[NewsItem]) -> list[AnalyzedNews]:
        """뉴스 목록을 한국어 요약/감성/티커로 분석."""
        ...

    async def ask(self, context: str, question: str) -> str:
        """맥락 기반 한국어 질의응답."""
        ...
