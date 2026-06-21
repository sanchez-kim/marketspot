"""뉴스 + AI 서비스.

뉴스 목록 조회는 빠르게(AI 없이) 반환하고, 요약/질의는 온디맨드로 AI 를
호출한다. AI 백엔드 선택·폴백을 여기서 관장한다:
Ollama(가동 중일 때) → 규칙기반(항상 동작).
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator, Callable

from ..ai.base import AIBackend
from ..ai.ollama_backend import OllamaBackend
from ..ai.rule_based import RuleBasedBackend, rule_importance
from ..cache import TTLCache
from ..config import Settings, load_settings
from ..models import (
    AnalyzedNews,
    AskResult,
    DataEnvelope,
    DataStatus,
    Importance,
    NewsItem,
    NewsSummaryResult,
)
from ..providers.news_provider import NewsProvider, YFinanceNewsProvider

# 뉴스 목록은 빠르게 변하지 않으니 짧게, AI 요약은 비싼 호출이라 길게 캐시.
_NEWS_TTL = 300.0  # 5분
_SUMMARY_TTL = 1800.0  # 30분 (심볼/다이제스트 묶음 결과 — 정확 재호출 빠른길)
_ITEM_TTL = 86400.0  # 24시간 (기사별 분석 — 같은 기사는 재요약 안 함)
# 다이제스트 선별 시 중요도 정렬 가중치(낮을수록 우선)
_IMPORTANCE_RANK = {Importance.HIGH: 0, Importance.MEDIUM: 1, Importance.LOW: 2}
# 실제 데이터가 담긴 상태들(이때만 캐시 — 에러/키필요는 재시도 여지를 남김).
_HAS_DATA = {DataStatus.LIVE, DataStatus.DELAYED, DataStatus.STALE}


class NewsAIService:
    def __init__(
        self,
        provider: NewsProvider | None = None,
        settings_loader: Callable[[], Settings] | None = None,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._provider: NewsProvider = provider or YFinanceNewsProvider()
        # 테스트에서 설정/백엔드를 주입할 수 있도록 loader 를 분리
        self._load_settings: Callable[[], Settings] = settings_loader or load_settings
        # 서버측 캐시(로컬 단일 사용자) — 탭을 다시 눌러도 즉시 표시되게.
        self._news_cache: TTLCache[DataEnvelope[list[NewsItem]]] = TTLCache(clock=clock)
        self._summary_cache: TTLCache[NewsSummaryResult] = TTLCache(clock=clock)
        self._digest_cache: TTLCache[NewsSummaryResult] = TTLCache(clock=clock)
        # 기사별 분석 캐시 — 변동 없으면 재요약하지 않고, 새 기사만 AI 호출.
        self._item_cache: TTLCache[AnalyzedNews] = TTLCache(clock=clock)

    async def get_news(
        self, symbol: str, limit: int = 20
    ) -> DataEnvelope[list[NewsItem]]:
        key = f"{symbol.upper()}|{limit}"
        cached = self._news_cache.get(key)
        if cached is not None:
            return cached
        env = await self._provider.get_news(symbol, limit)
        # 실제 데이터가 있을 때만 캐시(에러/키필요는 캐시하지 않아 다음 호출이 재시도).
        if env.data and env.status in _HAS_DATA:
            self._news_cache.set(key, env, _NEWS_TTL)
        return env

    async def summarize(self, symbol: str, limit: int = 12) -> NewsSummaryResult:
        key = f"{symbol.upper()}|{limit}"
        cached = self._summary_cache.get(key)
        if cached is not None:
            return cached

        env = await self.get_news(symbol, limit)  # 캐시된 뉴스 재사용
        items = env.data or []
        if not items:
            return NewsSummaryResult(backend="none", items=[])

        result = await self._summarize_items(items)
        # ★ AI 성공 결과만 캐시(rule 폴백 캐시는 일시 장애를 고정시켜 오염).
        if result.backend in ("ollama", "gemini"):
            self._summary_cache.set(key, result, _SUMMARY_TTL)
        return result

    async def _summarize_items(self, items: list[NewsItem]) -> NewsSummaryResult:
        """기사별 캐시를 활용 — 이미 요약된 기사는 재사용하고 **새 기사만** AI 호출.

        뉴스가 그대로면(같은 item id) AI 를 다시 부르지 않아 빠르다. 부분적으로
        새 기사가 생기면 그것만 요약한다.
        """
        if not items:
            return NewsSummaryResult(backend="none", items=[])

        done: dict[str, AnalyzedNews] = {}
        todo: list[NewsItem] = []
        for it in items:
            hit = self._item_cache.get(it.id)
            if hit is not None:
                done[it.id] = hit
            else:
                todo.append(it)

        backend_name = "ollama"  # 전부 캐시면(캐시는 AI 성공만 저장) ollama 로 간주
        if todo:
            backend = await self._choose_backend()
            try:
                analyzed = await backend.summarize_news(todo)
                backend_name = backend.name
            except Exception:  # noqa: BLE001 - 어떤 AI 실패든 규칙기반으로 폴백
                analyzed = await RuleBasedBackend().summarize_news(todo)
                backend_name = "rule"
            for a in analyzed:
                done[a.item.id] = a
                if backend_name in ("ollama", "gemini"):  # AI 성공만 항목 캐시
                    self._item_cache.set(a.item.id, a, _ITEM_TTL)

        ordered = [done[it.id] for it in items if it.id in done]
        return NewsSummaryResult(backend=backend_name, items=ordered)

    async def digest(self, symbols: list[str], top: int = 6) -> NewsSummaryResult:
        """홈 다이제스트: 여러 종목 뉴스 중 **중요한 것만** 골라 AI 요약.

        규칙기반 중요도로 먼저 싸게 거르고(전부 AI 요약은 느리고 노이즈도 많음),
        상위 N건만 AI 로 한국어 요약한다.
        """
        uniq = list(dict.fromkeys(s.strip().upper() for s in symbols if s.strip()))
        if not uniq:
            return NewsSummaryResult(backend="none", items=[])
        key = "|".join(uniq) + f"#{top}"
        cached = self._digest_cache.get(key)
        if cached is not None:
            return cached

        seen: set[str] = set()
        pool: list[tuple[int, float, NewsItem]] = []
        for sym in uniq:
            env = await self.get_news(sym, 8)
            for item in env.data or []:
                if item.id in seen:
                    continue
                seen.add(item.id)
                imp = rule_importance(f"{item.title} {item.summary}")
                ts = item.published.timestamp() if item.published else 0.0
                pool.append((_IMPORTANCE_RANK[imp], -ts, item))

        if not pool:
            return NewsSummaryResult(backend="none", items=[])
        pool.sort(key=lambda p: (p[0], p[1]))  # 중요도↑, 최신순
        selected = [item for _, _, item in pool[:top]]

        result = await self._summarize_items(selected)
        if result.backend in ("ollama", "gemini"):
            self._digest_cache.set(key, result, _SUMMARY_TTL)
        return result

    async def ask(
        self, context: str, question: str, *, think: bool = False
    ) -> AskResult:
        backend = await self._choose_backend()
        try:
            if isinstance(backend, OllamaBackend):
                answer = await backend.ask(context, question, think=think)
            else:
                answer = await backend.ask(context, question)
            return AskResult(backend=backend.name, answer=answer)
        except Exception:  # noqa: BLE001
            rule = RuleBasedBackend()
            answer = await rule.ask(context, question)
            return AskResult(backend=rule.name, answer=answer)

    async def ask_stream(
        self, context: str, question: str, *, think: bool = False
    ) -> tuple[str, AsyncIterator[str]]:
        """(백엔드명, 토큰 스트림). Ollama 면 실시간 스트리밍, 아니면 규칙기반 한 번."""
        backend = await self._choose_backend()
        if isinstance(backend, OllamaBackend):
            return "ollama", _stream_with_fallback(backend, context, question, think)

        async def _one() -> AsyncIterator[str]:
            yield await RuleBasedBackend().ask(context, question)

        return "rule", _one()

    async def _choose_backend(self) -> AIBackend:
        settings: Settings = self._load_settings()
        pref = settings.ai.backend
        if pref == "ollama" and await OllamaBackend.is_available():
            return OllamaBackend(
                model=settings.ai.model, beginner_mode=settings.ai.beginner_mode
            )
        # gemini 는 향후 구현. 키/모델 없거나 미가동이면 규칙기반.
        return RuleBasedBackend()


async def _stream_with_fallback(
    backend: OllamaBackend, context: str, question: str, think: bool
) -> AsyncIterator[str]:
    """Ollama 스트림. 첫 토큰 전에 실패하면 규칙기반으로 폴백한다."""
    yielded = False
    try:
        async for chunk in backend.ask_stream(context, question, think=think):
            yielded = True
            yield chunk
    except Exception:  # noqa: BLE001
        if not yielded:
            yield await RuleBasedBackend().ask(context, question)
