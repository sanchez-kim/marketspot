"""FastAPI 앱 진입점."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import __version__
from .portfolio_store import load_positions
from .routers import (
    calendar,
    chart,
    context,
    filings,
    fundamentals,
    health,
    home,
    macro,
    news,
    portfolio,
    quotes,
    search,
    settings,
    spark,
    toss,
    valuation,
)
from .transaction_store import bootstrap_transactions


def _migrate_transactions_on_startup() -> None:
    """기존 portfolio.json → transactions.json 한 번만 마이그레이션.

    transactions.json 이 없으면 portfolio.json 에서 buy 거래내역을 생성해
    저장한다. 이미 transactions.json 이 있으면 아무것도 하지 않는다(멱등).
    """
    bootstrap_transactions(None, load_positions)


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
    _migrate_transactions_on_startup()
    yield


app = FastAPI(
    title="MarketSpot API",
    version=__version__,
    description="MarketSpot — ETF 투자자를 위한 로컬 금융 리서치 터미널 백엔드",
    lifespan=_lifespan,
)

# 로컬 개발: Vite dev 서버(4000)에서의 호출 허용
_dev_origins = os.environ.get(
    "CORS_ORIGINS", "http://localhost:4000,http://127.0.0.1:4000"
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _dev_origins if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(quotes.router)
app.include_router(chart.router)
app.include_router(macro.router)
app.include_router(news.router)
app.include_router(filings.router)
app.include_router(portfolio.router)
app.include_router(context.router)
app.include_router(home.router)
app.include_router(fundamentals.router)
app.include_router(calendar.router)
app.include_router(spark.router)
app.include_router(search.router)
app.include_router(settings.router)
app.include_router(toss.router)
app.include_router(valuation.router)
app.include_router(health.router)


@app.get("/api")
async def api_root() -> dict[str, str]:
    return {"name": "MarketSpot", "version": __version__}


# 프로덕션: 빌드된 프론트 정적 파일 서빙(있을 때만)
_static_dir = Path(os.environ.get("FRONTEND_DIST", "./static"))
if _static_dir.is_dir():
    app.mount("/", StaticFiles(directory=str(_static_dir), html=True), name="static")
