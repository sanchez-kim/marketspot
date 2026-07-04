# MarketSpot

[한국어](./README.md) | **English**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](./backend/pyproject.toml)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](./backend/pyproject.toml)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=white)](./frontend/package.json)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.6-3178C6?logo=typescript&logoColor=white)](./frontend/package.json)

> Catch the market's pulse — a quiet, honest investing companion for beginner long-term ETF investors.

![MarketSpot home dashboard](./assets/screenshots/home.png)

> **Note:** the app's UI itself is Korean-only for now (see [Known limitations](#known-limitations)). This README is the English version of the project docs.

## TL;DR

One dashboard for your verdict, drawdown context, portfolio, Toss Securities sync, and an AI coach. No predictions, no buy/sell calls — if there's no data, it just says so.

```bash
docker compose up
# → http://localhost:4000
```

That's really all you need to try it. Details below in [Getting started](#getting-started).

---

## Why I built this

What actually wrecks investing returns usually isn't picking the wrong stock — it's **what you do**. Panic-selling in a crash. Chasing a rally after it's already run. There's no shortage of flashy "terminals" packed with indicators. MarketSpot tries to do the opposite: on a scary day, it just tells you, calmly, "this is fine, this happens sometimes."

There's one rule behind all of it. If it doesn't know something, it says so. Missing data shows up as missing data — never papered over with a plausible-looking number. The AI follows the same rule: it doesn't predict prices, and it doesn't tell you to buy or sell. Honestly, that one rule is most of what this project is.

It's built for a single local user, runs on free data, and has no login.

---

## What it does

**Reassurance home dashboard**
A one-line verdict answers "am I okay right now?", backed by the drawdown context behind it. Something like — *"VOO has had 14 corrections of 5%+ over the past 10 years, and recovered from every single one, usually within 49 days."* Your investing principles, portfolio summary, watchlist, today's news, and upcoming events all live on one screen. Cards can be dragged around or hidden however you like.

**Stock detail**
Sector, market cap, P/E, dividends, and — for ETFs — what's actually inside the fund. Charts come in two modes: a calm price-only view, and an "explore" mode with RSI/MACD. Related news and filings are attached too.

**Portfolio**
Enter your holdings, quantities, and average cost, and it calculates live valuation, P&L, and weight for you. If a quote can't be fetched for something, it's honestly left out rather than faked.

**Toss Securities sync**
Drop in your app key and secret, and it syncs your account, holdings, and transaction history — read-only, no order placement at all. If what the app has computed drifts from your actual Toss balance, it won't quietly paper over the gap; it shows the drift as-is. Also used to backstop Korean-market quotes.

**AI coach**
A toggleable sidebar on the right, streaming responses. It reads the situation and opens the conversation, but it never predicts or tells you to buy or sell. If Ollama isn't running, it quietly falls back to rule-based responses.

All of this data flows through a shared `DataEnvelope` wrapper that always carries a value, a status, a source, and a freshness timestamp together. So whenever something fails or data is missing, it shows up as `NO_DATA`, `NEEDS_KEY`, or `ERROR` — never a blank gap or a made-up number on screen.

---

## Getting started

### Requirements

| Method | You'll need |
|---|---|
| Docker Compose (recommended) | Docker, Docker Compose |
| Running it directly | Python 3.11+, Node 18+ |
| AI features (optional) | [Ollama](https://ollama.com) |

### Docker Compose, all at once (recommended, dev mode)

```bash
docker compose up
#   Open http://localhost:4000 in your browser (backend is on :8000)
#   Edits are reflected immediately (backend --reload, frontend Vite HMR)
#   AI reuses the Ollama instance already running on your host (:11434) — no re-downloading models into the container

docker compose up --build   # after changing the Dockerfile or dependencies
docker compose down         # stop everything
```

You'll need [Ollama](https://ollama.com) running on your host for AI features. It's not required — everything falls back to rule-based responses without it.

```bash
ollama pull qwen3.5:9b-mlx   # default model (Apple Silicon MLX, Ollama 0.30+)
```

### Production mode, for leaving it running

Serves the built frontend and backend from a single container (:8000) — no `--reload` or HMR, just light and fast.

```bash
docker compose -f docker-compose.prod.yml up --build -d
# → http://127.0.0.1:8000 (frontend and API together)
```

Code changes aren't picked up automatically here — rebuild with `--build` after editing. For actual development, the `docker compose up` (hot-reload) setup above is much more convenient.

### Running it directly, without Docker

```bash
# backend (Python 3.11+; include a contact address in the User-Agent when calling SEC filings)
cd backend
SEC_USER_AGENT="MarketSpot/0.1 (local; you@example.com)" \
  .venv/bin/uvicorn app.main:app --port 8000

# frontend (in a new terminal)
cd frontend && npm run dev    # http://localhost:4000 (/api requests proxy to :8000)
```

---

## How it's built

### Tech stack

| Layer | Tech |
|---|---|
| Backend | Python 3.11+ · FastAPI · Pydantic v2 · httpx |
| Frontend | React 18 · TypeScript · Vite |
| State | Zustand (UI state) · TanStack Query (server state) |
| Charts | lightweight-charts |
| AI | Ollama (local) |
| Deployment | Docker Compose |

### Directory layout

```
backend/  FastAPI (Python 3.14) · Pydantic v2 · httpx
  app/
    models.py            DataEnvelope/DataStatus + domain models
    providers/            External data adapters (yfinance, SEC, Toss, Yahoo search…) → normalized into DataEnvelope
    analytics/drawdown.py Drawdown base-rate calculations (pure functions)
    services/             quotes, chart, news, portfolio, reassurance, home, spark…
    routers/               HTTP endpoints
    config.py              settings.json (watchlist, UI, investing principles, dashboard layout)
frontend/ React 18 + TypeScript + Vite
  src/
    components/           Home widgets, stock detail, AI sidebar, charts (lightweight-charts)
    api/                   client.ts (endpoints) · types.ts (camelCase contract)
    store/uiStore.ts       Zustand (UI state) · TanStack Query (server state)
docker-compose.yml        backend + frontend (dev)
```

### Data sources

Everything is free.

| Feature | Provider | Key needed | Notes |
|---|---|:---:|---|
| Quotes, charts, news, fundamentals, calendar | yfinance | ✕ | US quotes run ~15 min delayed |
| Filings (US) | SEC EDGAR | ✕ | |
| Filings (Korea) | DART | ✓ | corp_code mapping not wired up yet |
| Symbol search | Yahoo | ✕ | |
| Account sync, Korean quote backstop | Toss Securities Open API | ✓ | read-only |
| AI coach | Ollama | ✕ | runs locally, model installed separately |

### Main API

| Method | Path | Description |
|---|---|---|
| GET | `/api/home` | Reassurance home verdict |
| GET | `/api/context/{symbol}` \| `?symbols=` | Drawdown context (base rates) |
| GET | `/api/quotes?symbols=` | Quotes |
| GET | `/api/chart/{symbol}` | Chart |
| GET | `/api/fundamentals/{symbol}` | Stock fundamentals |
| GET | `/api/news?symbol=` | Stock news |
| GET | `/api/news/digest?symbols=` | News digest |
| POST | `/api/ai/ask` | AI coach |
| POST | `/api/ai/ask/stream` | AI coach (streaming) |
| GET | `/api/filings?symbol=` | Filings (SEC) |
| GET / PUT | `/api/portfolio` | Portfolio |
| GET | `/api/calendar?symbols=` | Upcoming events |
| GET | `/api/spark?symbols=` | Sparklines |
| GET | `/api/search?q=` | Symbol search |
| GET / PUT | `/api/settings` | Local settings (watchlist, UI, principles, dashboard) |
| GET | `/api/toss/status` | Toss Securities connection status |
| PUT | `/api/toss/account` | Select Toss account |
| POST | `/api/toss/sync` | Sync with Toss Securities |

---

## Configuration and security — please read this

All settings live in local files. `backend/data/settings.json` holds your watchlist, UI, investing principles, and dashboard layout; `backend/data/portfolio.json` holds your holdings.

API keys never go into code or commits. `.env` and `settings.json` are both gitignored, and keys are always masked in API responses. The only thing actually committed to the repo is `.env.example`, with empty placeholder values.

Your Toss Securities app key and secret deserve extra care — they grant access to a real brokerage account. That said, the app only uses them for account lookups and quotes; there's no order-placement functionality at all.

Since this is a single-user local app, there's no login and no database — which also means **there's no authentication whatsoever**. `docker-compose.yml` binds host ports to `127.0.0.1` only by default (accessible only from your own machine). If you rebind the ports to reach it from another device, know that from that moment on, anyone can get in with zero authentication.

Environment variables you'll actually use:

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_HOST` | `http://localhost:11434` | Address of the Ollama instance the AI connects to |
| `SEC_USER_AGENT` | — | User-Agent (with a contact address) for SEC EDGAR calls |
| `STOCK_TERMINAL_DATA_DIR` | — | Where settings and portfolio files are stored |

Before zipping this folder up or handing a backup to someone else, clear or rotate any keys you've put in `.env`. It's never committed, but it does sit on disk in plain text.

---

## Known limitations

Being upfront about these.

- US quotes run about 15 minutes delayed — an unavoidable consequence of using free data, and shouldn't matter much for dollar-cost-averaging long-term investors.
- DART (Korean filings) shows nothing without a key, and even with one, symbol-to-corp_code mapping isn't wired up yet.
- Portfolio totals assume a single currency (USD) — no conversion if you hold mixed currencies. Only unrealized P&L is shown; realized P&L, transaction history, and dividends aren't factored in yet.
- The AI's "thinking" mode is slow, so fast streaming is the default and thinking is off. MLX models occasionally garble Korean text.
- yfinance isn't an official API, so it can change or break without notice. When it does, it shows up honestly as `ERROR` — never papered over with fake numbers.
- For Korean stocks newly discovered through Toss Securities sync, it's not yet clear whether they're KOSPI or KOSDAQ. The Toss API returns bare symbol codes with no exchange suffix, and we haven't been able to verify from real holdings whether the response contains anything that distinguishes the exchange. Rather than guess, we're leaving this unresolved until it's confirmed.
- The app UI is Korean-only for now. Multi-language support (English included) doesn't exist yet — it's on the roadmap. **TODO.**

---

## Contributing

Issues and PRs are always welcome. Please run these gates before submitting a change:

```bash
# Backend (verification gate)
cd backend && .venv/bin/ruff check . && .venv/bin/mypy . && .venv/bin/python -m pytest -q

# Frontend
cd frontend && npm run typecheck && npm run lint && npm test && npm run build
```

The "never fabricate numbers" principle applies just as much to code and tests. When data isn't available, please write code that shows that honestly rather than filling the gap. Please also avoid weakening assertions or quietly skipping failing cases just to get a test to pass.

---

## License

Released under the [MIT](./LICENSE) license. Use it, modify it, redistribute it — just keep the attribution.
