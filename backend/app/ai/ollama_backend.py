"""Ollama 로컬 AI 백엔드.

키 불필요. 로컬에서 구동 중인 Ollama 에 HTTP 로 요청한다. 연결 실패/파싱
실패 시 예외를 던져 상위(서비스)가 규칙기반으로 폴백하게 한다.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
from collections.abc import AsyncIterator

import httpx

from ..models import (
    AnalyzedNews,
    Importance,
    NewsAnalysis,
    NewsItem,
    Sentiment,
)
from .rule_based import analyze_item

_SENTIMENT_MAP = {
    "positive": Sentiment.POSITIVE,
    "강세": Sentiment.POSITIVE,
    "negative": Sentiment.NEGATIVE,
    "약세": Sentiment.NEGATIVE,
    "neutral": Sentiment.NEUTRAL,
    "중립": Sentiment.NEUTRAL,
}
_IMPORTANCE_MAP = {
    "high": Importance.HIGH,
    "중요": Importance.HIGH,
    "medium": Importance.MEDIUM,
    "보통": Importance.MEDIUM,
    "low": Importance.LOW,
    "낮음": Importance.LOW,
}


def _host() -> str:
    return os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")


class OllamaBackend:
    name = "ollama"

    def __init__(
        self, model: str = "qwen3.5:9b-mlx", *, beginner_mode: bool = True
    ) -> None:
        self.model = model
        self.beginner_mode = beginner_mode

    @staticmethod
    async def is_available(timeout_seconds: float = 1.5) -> bool:
        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                resp = await client.get(f"{_host()}/api/tags")
                return resp.status_code == 200
        except (httpx.HTTPError, OSError):
            return False

    async def _generate(
        self, prompt: str, *, num_predict: int = 512, think: bool = False
    ) -> str:
        # ★ think 기본 off(사고 토큰 0 → 빠름). 요약은 항상 off(JSON 안정),
        #   질의응답은 사용자가 켤 수 있다. format:"json" 은 빈 출력 유발이라 미사용.
        payload: dict[str, object] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "think": think,
            # 모델을 30분간 메모리에 유지 → 다음 요청의 콜드 재로딩(~수초) 제거
            "keep_alive": "30m",
            "options": {"num_predict": num_predict},
        }
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(f"{_host()}/api/generate", json=payload)
            resp.raise_for_status()
            data = resp.json()
        response = data.get("response")
        if not isinstance(response, str) or not response.strip():
            raise ValueError("Ollama 응답이 비었습니다")
        return response

    async def _summarize_one(self, item: NewsItem) -> AnalyzedNews:
        prompt = _summary_prompt(item, beginner=self.beginner_mode)
        raw = await self._generate(prompt, num_predict=400)
        return AnalyzedNews(item=item, analysis=_parse_analysis(raw, item))

    async def _try_one(self, item: NewsItem) -> AnalyzedNews | None:
        """성공하면 분석, 실패하면 None(상위에서 규칙기반으로 폴백)."""
        try:
            return await self._summarize_one(item)
        except Exception:  # noqa: BLE001 - 항목 실패는 None 으로 폴백(가짜값 ❌)
            return None

    async def summarize_news(self, items: list[NewsItem]) -> list[AnalyzedNews]:
        if not items:
            return []
        # ★ 첫 항목으로 모델을 '워밍업'한 뒤 나머지를 병렬 처리한다. 콜드 로드
        #   중에 동시 요청이 한꺼번에 몰리면(thundering herd) 일부가 깨지는
        #   경쟁이 생기는데, 먼저 1건으로 모델을 올려두면 이를 피한다.
        outcomes: list[AnalyzedNews | None] = [await self._try_one(items[0])]
        if len(items) > 1:
            outcomes += await asyncio.gather(*(self._try_one(i) for i in items[1:]))
        results: list[AnalyzedNews] = []
        failures = 0
        for item, outcome in zip(items, outcomes, strict=True):
            if outcome is not None:
                results.append(outcome)
            else:
                failures += 1
                results.append(AnalyzedNews(item=item, analysis=analyze_item(item)))
        # 전부 실패 = Ollama 가 사실상 죽음 → 상위가 일괄 폴백(배지=rule)하도록 예외.
        if failures == len(items):
            raise RuntimeError("Ollama 요약이 모든 항목에서 실패했습니다")
        return results

    async def ask(self, context: str, question: str, *, think: bool = False) -> str:
        prompt = _coach_prompt(context, question, beginner=self.beginner_mode)
        return await self._generate(prompt, num_predict=_ask_budget(think), think=think)

    async def ask_stream(
        self, context: str, question: str, *, think: bool = False
    ) -> AsyncIterator[str]:
        """토큰을 생성되는 대로 흘려보낸다(체감 속도 개선)."""
        prompt = _coach_prompt(context, question, beginner=self.beginner_mode)
        payload: dict[str, object] = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
            "think": think,
            "keep_alive": "30m",  # 모델 메모리 유지(콜드 재로딩 제거)
            # ★ 사고 모드는 thinking 이 토큰을 먼저 소비하므로 예산을 크게 줘야
            #   답변까지 남는다(작으면 응답이 비어버림).
            "options": {"num_predict": _ask_budget(think)},
        }
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream(
                "POST", f"{_host()}/api/generate", json=payload
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    chunk = json.loads(line).get("response")
                    if isinstance(chunk, str) and chunk:
                        yield chunk


def _ask_budget(think: bool) -> int:
    # 사고 모드는 thinking 이 토큰을 먼저 쓰므로 넉넉히, 일반 모드는 짧게.
    return 3072 if think else 800


def _coach_prompt(context: str, question: str, *, beginner: bool) -> str:
    # 차분한 코치 — 예측·매수매도 조언 금지(가짜 확신 ❌), 맥락·원리로 안심.
    tone = "초보도 이해하게 전문용어를 풀어서, " if beginner else ""
    return (
        "당신은 초보 장기투자자를 돕는 차분한 한국어 투자 코치입니다.\n"
        "규칙: 가격 예측이나 매수/매도 시점 조언은 하지 않습니다"
        "('오른다'/'사라/팔아라' 금지). 대신 일반 원리·역사적 경향·맥락으로 "
        f"설명합니다. {tone}간결하게 한국어로, 불안을 키우지 않게 "
        "장기·적립 관점을 존중하며 답하세요.\n\n"
        f"[맥락]\n{context}\n\n[질문]\n{question}"
    )


def _summary_prompt(item: NewsItem, *, beginner: bool) -> str:
    tone = "초보 투자자도 이해하게 쉬운 말로, " if beginner else ""
    return (
        "다음 영어 금융 뉴스를 분석해 JSON 으로만 답하세요. "
        f"{tone}koreanSummary 는 한국어 한두 문장.\n"
        'JSON 스키마: {"koreanSummary": string, '
        '"sentiment": "POSITIVE|NEUTRAL|NEGATIVE", '
        '"importance": "HIGH|MEDIUM|LOW", "tickers": string[]}\n\n'
        f"제목: {item.title}\n요약: {item.summary}\n"
    )


_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)


def extract_json_object(text: str) -> dict[str, object]:
    """모델 출력에서 JSON 객체를 견고하게 추출한다.

    thinking 블록(<think>…</think>)이나 마크다운 코드펜스가 섞여 있어도
    첫 '{' 부터 마지막 '}' 까지를 파싱한다.
    """
    cleaned = _THINK_RE.sub("", text)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("JSON 객체를 찾을 수 없습니다")
    parsed = json.loads(cleaned[start : end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("JSON 객체가 아닙니다")
    return parsed


def _parse_analysis(raw: str, item: NewsItem) -> NewsAnalysis:
    data = extract_json_object(raw)
    sentiment = _SENTIMENT_MAP.get(
        str(data.get("sentiment", "")).lower().strip(), Sentiment.NEUTRAL
    )
    importance = _IMPORTANCE_MAP.get(
        str(data.get("importance", "")).lower().strip(), Importance.MEDIUM
    )
    korean = data.get("koreanSummary")
    if not isinstance(korean, str) or not korean.strip():
        raise ValueError("koreanSummary 누락")
    tickers_raw = data.get("tickers")
    tickers = (
        [str(t) for t in tickers_raw if isinstance(t, str)]
        if isinstance(tickers_raw, list)
        else []
    )
    if not tickers:
        tickers = item.tickers
    return NewsAnalysis(
        sentiment=sentiment,
        importance=importance,
        tickers=tickers,
        korean_summary=korean.strip(),
    )
