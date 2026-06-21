"""Ollama 출력 파싱 테스트(네트워크 없음).

qwen3 thinking 블록/코드펜스가 섞여도 JSON 을 견고하게 추출하는지,
그리고 _parse_analysis 가 한/영 라벨을 enum 으로 매핑하는지 검증한다.
"""

from __future__ import annotations

import pytest

from app.ai.ollama_backend import OllamaBackend, _parse_analysis, extract_json_object
from app.models import Importance, NewsItem, Sentiment


def test_extract_plain_json() -> None:
    raw = '{"koreanSummary": "요약", "sentiment": "POSITIVE"}'
    assert extract_json_object(raw)["sentiment"] == "POSITIVE"


def test_extract_strips_think_block() -> None:
    raw = '<think>이건 사고과정...</think>\n{"koreanSummary": "ok"}'
    assert extract_json_object(raw)["koreanSummary"] == "ok"


def test_extract_handles_code_fence_and_prose() -> None:
    raw = '설명입니다:\n```json\n{"koreanSummary": "안녕"}\n```\n끝.'
    assert extract_json_object(raw)["koreanSummary"] == "안녕"


def test_extract_raises_when_no_json() -> None:
    with pytest.raises(ValueError):
        extract_json_object("JSON 없음")


def test_parse_analysis_maps_labels() -> None:
    item = NewsItem(id="1", title="t", tickers=["AAPL"])
    raw = (
        '{"koreanSummary":"애플 실적 호조","sentiment":"POSITIVE",'
        '"importance":"HIGH","tickers":["AAPL"]}'
    )
    analysis = _parse_analysis(raw, item)
    assert analysis.sentiment == Sentiment.POSITIVE
    assert analysis.importance == Importance.HIGH
    assert analysis.korean_summary == "애플 실적 호조"


def test_parse_analysis_accepts_korean_labels() -> None:
    item = NewsItem(id="1", title="t", tickers=["X"])
    raw = '{"koreanSummary":"약세 뉴스","sentiment":"약세","importance":"중요"}'
    analysis = _parse_analysis(raw, item)
    assert analysis.sentiment == Sentiment.NEGATIVE
    assert analysis.importance == Importance.HIGH
    assert analysis.tickers == ["X"]  # 누락 시 원본 티커 보존


def test_parse_analysis_raises_without_summary() -> None:
    item = NewsItem(id="1", title="t")
    with pytest.raises(ValueError):
        _parse_analysis('{"sentiment":"POSITIVE"}', item)


# ── 항목별 폴백 (한 항목 실패해도 나머지는 유지) ──────────────────────
_GOOD = '{"koreanSummary":"좋은 요약","sentiment":"POSITIVE","importance":"LOW"}'


class _PartialOllama(OllamaBackend):
    """특정 제목에서만 생성 실패를 흉내내는 백엔드(네트워크 없음)."""

    async def _generate(
        self, prompt: str, *, num_predict: int = 512, think: bool = False
    ) -> str:
        if "BOOM" in prompt:
            raise ValueError("생성 실패")
        return _GOOD


@pytest.mark.asyncio
async def test_summarize_news_per_item_fallback() -> None:
    items = [
        NewsItem(id="1", title="정상 기사", tickers=["AAPL"]),
        NewsItem(id="2", title="BOOM 실패 기사", tickers=["XYZ"]),
    ]
    out = await _PartialOllama().summarize_news(items)
    assert len(out) == 2
    # 1번은 Ollama 요약, 2번은 규칙기반 폴백(원문 제목 보존)
    assert out[0].analysis.korean_summary == "좋은 요약"
    assert "BOOM 실패 기사" in out[1].analysis.korean_summary


@pytest.mark.asyncio
async def test_summarize_news_raises_when_all_fail() -> None:
    """전부 실패하면 상위가 일괄 규칙기반 폴백하도록 예외를 던진다."""
    items = [NewsItem(id="1", title="BOOM a"), NewsItem(id="2", title="BOOM b")]
    with pytest.raises(RuntimeError):
        await _PartialOllama().summarize_news(items)
