"""뉴스 + AI 라우터."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from ..deps import get_news_service
from ..models import (
    AskResult,
    CamelModel,
    DataEnvelope,
    NewsItem,
    NewsSummaryResult,
)
from ..services.news import NewsAIService

router = APIRouter(prefix="/api", tags=["news", "ai"])


@router.get("/news")
async def get_news(
    service: Annotated[NewsAIService, Depends(get_news_service)],
    symbol: Annotated[str, Query()],
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> DataEnvelope[list[NewsItem]]:
    return await service.get_news(symbol, limit)


class SummarizeRequest(CamelModel):
    symbol: str
    limit: int = 12


@router.post("/news/summarize")
async def summarize_news(
    body: SummarizeRequest,
    service: Annotated[NewsAIService, Depends(get_news_service)],
) -> NewsSummaryResult:
    return await service.summarize(body.symbol, body.limit)


@router.get("/news/digest")
async def news_digest(
    service: Annotated[NewsAIService, Depends(get_news_service)],
    symbols: Annotated[str, Query()],
    top: Annotated[int, Query(ge=1, le=12)] = 6,
) -> NewsSummaryResult:
    """홈 다이제스트: 관심종목 뉴스 중 중요한 것만 AI 요약."""
    return await service.digest(symbols.split(","), top)


class AskRequest(CamelModel):
    context: str = ""
    question: str
    think: bool = False  # 사고(thinking) 모드 — 느리지만 더 깊은 추론


@router.post("/ai/ask")
async def ai_ask(
    body: AskRequest,
    service: Annotated[NewsAIService, Depends(get_news_service)],
) -> AskResult:
    return await service.ask(body.context, body.question, think=body.think)


@router.post("/ai/ask/stream")
async def ai_ask_stream(
    body: AskRequest,
    service: Annotated[NewsAIService, Depends(get_news_service)],
) -> StreamingResponse:
    """토큰을 생성되는 대로 흘려보낸다(체감 속도 개선)."""
    backend, stream = await service.ask_stream(
        body.context, body.question, think=body.think
    )
    return StreamingResponse(
        stream,
        media_type="text/plain; charset=utf-8",
        headers={"X-AI-Backend": backend, "X-Accel-Buffering": "no"},
    )
