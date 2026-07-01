# MarketSpot

> **시장의 흐름을 포착하다** — 초보 장기 ETF 투자자를 위한 **차분한 한국어 투자 동반자**.
> 데이터를 쏟아붓는 "터미널"이 아니라, *무서운 날 열었을 때 안심하고 계획을 지키게* 돕는 도구.

개인 로컬 전용 · 무료 데이터 · 로그인 없음 · 가짜 숫자/예측 없음.

관련 문서: [REQUIREMENTS.md](./REQUIREMENTS.md) · [DESIGN.md](./DESIGN.md) · [CLAUDE.md](./CLAUDE.md)(개발 규율) · [STATUS.md](./STATUS.md)(진행 상태)

---

## 무엇을 하나

투자에서 수익을 가장 크게 좌우하는 건 종목 선택이 아니라 **내 행동**(패닉 매도, 추격 매수)이다. MarketSpot은 그 행동을 다스리도록 설계됐다.

- **안심 홈 대시보드** — "나 괜찮나? 뭔가 해야 하나?"에 한 줄로 답하는 **평결**, 그 근거가 되는 **하락 맥락**(예: "VOO는 10년간 5%+ 조정을 14번 겪고 전부 회복, 보통 49일"), 내 **투자원칙**·**포트폴리오 요약**·**관심종목**·**오늘 눈여겨볼 뉴스**·**다가오는 일정**·**오늘의 배움**. 카드는 드래그로 재배치/숨김 가능.
- **종목 상세** — 기본정보(섹터·시총·PER·배당·ETF 보유종목·용어풀이), 차트(차분 모드 / 탐구 모드=RSI·MACD), 그 종목 뉴스·공시.
- **수동 포트폴리오** — 보유종목·수량·평단 입력 → 실시간 평가액·손익·비중. 시세 없는 종목은 정직하게 제외.
- **AI 코치** — 우측 토글 사이드바, 스트리밍 응답. 상황을 먼저 읽고 말 걸고, **예측·매수매도 조언은 하지 않음**. Ollama 미가동 시 규칙기반 폴백.

### 핵심 원칙 — 정직성 (가짜 금지)
모든 외부 데이터는 `DataEnvelope`(값 + `DataStatus` + 출처 + 신선도)로 정규화되어 **상태 표기가 강제**된다. 데이터가 없으면 임의 값으로 채우지 않고 `NO_DATA`/`NEEDS_KEY`/`ERROR`로 표시한다. AI도 **가짜 인사이트·가짜 확신·가격 예측을 하지 않으며**, 진행 중인 하락은 회복 통계에서 제외한다.

---

## 실행

### 권장: Docker Compose 한 방 (개발용, 핫리로드)
```bash
docker compose up
#   브라우저 → http://localhost:4000   (백엔드 :8000)
#   코드 편집 즉시 반영(백엔드 --reload, 프론트 Vite HMR)
#   AI는 호스트의 Ollama(:11434)를 재사용한다(컨테이너에 모델 재다운로드 X)
docker compose up --build   # Dockerfile/의존성 바뀐 경우
docker compose down         # 중지
```

**전제:** [Ollama](https://ollama.com)가 호스트에서 돌고 있고 AI 모델이 준비돼 있어야 AI 기능이 동작한다(없으면 규칙기반 폴백):
```bash
ollama pull qwen3.5:9b-mlx   # 기본 모델(애플 실리콘 MLX, Ollama 0.30+)
```

### 대안: 로컬 직접 실행
```bash
# 백엔드 (Python 3.11+; SEC 공시 호출 시 연락처 포함 User-Agent 권장)
cd backend
SEC_USER_AGENT="MarketSpot/0.1 (local; you@example.com)" \
  .venv/bin/uvicorn app.main:app --port 8000

# 프론트 (새 터미널)
cd frontend && npm run dev    # http://localhost:4000 (/api → :8000 프록시)
```

---

## 아키텍처

```
backend/  FastAPI (Python 3.14) · Pydantic v2 · httpx
  app/
    models.py            DataEnvelope/DataStatus + 도메인 모델
    providers/           외부 데이터 어댑터(yfinance·SEC·Yahoo검색…) → DataEnvelope 정규화
    analytics/drawdown.py 하락 기저율(순수 함수)
    services/            quotes·chart·news·portfolio·reassurance·home·spark…
    routers/             HTTP 엔드포인트
    config.py            settings.json(관심종목·UI·투자원칙·대시보드 레이아웃)
frontend/ React 18 + TypeScript + Vite
  src/
    components/          홈 위젯·종목 상세·AI 사이드바·차트(lightweight-charts)
    api/                 client.ts(엔드포인트) · types.ts(camelCase 계약)
    store/uiStore.ts     Zustand(UI 상태) · TanStack Query(서버 상태)
docker-compose.yml       backend + frontend (개발용)
```

**데이터 소스(무료):** 시세·차트·뉴스·기본정보·일정 = yfinance(키 불필요, 미국 ~15분 지연) · 공시 = SEC EDGAR(키 불필요) / DART(키 필요) · 심볼검색 = Yahoo · AI = 로컬 Ollama.

### 주요 API
```
GET  /api/home                       안심 홈 평결
GET  /api/context/{symbol}|?symbols=  하락 맥락(기저율)
GET  /api/quotes?symbols=             시세        GET /api/chart/{symbol}
GET  /api/fundamentals/{symbol}       종목 기본정보
GET  /api/news?symbol=  ·  /api/news/digest?symbols=   뉴스·다이제스트
POST /api/ai/ask  ·  /api/ai/ask/stream               AI 코치(스트리밍)
GET  /api/filings?symbol=             공시(SEC)
GET  /api/portfolio  ·  PUT           수동 포트폴리오
GET  /api/calendar?symbols=  ·  /api/spark?symbols=    일정·스파크라인
GET  /api/search?q=                   심볼 검색
GET  /api/settings   ·  PUT           로컬 설정(관심종목·UI·원칙·대시보드)
```

---

## 설정 · 보안

- 설정은 로컬 파일에 저장된다: `backend/data/settings.json`(관심종목·UI·투자원칙·대시보드 레이아웃), `backend/data/portfolio.json`(보유 포지션).
- **API 키는 코드/커밋에 넣지 않는다.** `.env`·`settings.json`은 `.gitignore` 대상이며 응답에서 키는 마스킹된다. 커밋되는 건 `.env.example`뿐.
- 단일 로컬 사용자라 로그인·DB가 없다(파일 영속으로 충분). **따라서 인증이 전혀 없다.**
- `docker-compose.yml`은 기본적으로 호스트 포트를 `127.0.0.1`(로컬 전용)에만 게시한다. 다른 기기(LAN)에서 접속하려면 포트 바인딩을 직접 바꿔야 하며, 그 순간부터 인증 없이 누구나 접근 가능해진다는 것을 알고 진행할 것.
- 주요 환경변수: `OLLAMA_HOST`(기본 `http://localhost:11434`) · `SEC_USER_AGENT` · `STOCK_TERMINAL_DATA_DIR`.
- 이 폴더를 zip이나 백업으로 남에게 공유하기 전에는 `.env`에 넣어둔 API 키를 지우거나 회전할 것(`.env`는 커밋되지 않지만 디스크에는 평문으로 남는다).

---

## 알려진 한계 (정직하게)

- **미국 시세는 ~15분 지연**(무료 정책상 의도된 것 — 적립식 장기 투자엔 무방).
- **DART(한국 공시)**는 키 없으면 `NEEDS_KEY`, 키가 있어도 corp_code 매핑 미연동.
- **포트폴리오 합계는 단일 통화(USD) 가정** — 통화 혼합 시 환산 없음. 미실현 손익만(거래내역·실현손익·배당 미반영).
- **AI 사고(think) 모드**는 느리다(기본 off=빠른 스트리밍). MLX 모델은 드물게 한국어 글자깨짐 가능.
- yfinance는 비공식 → 깨질 수 있고, 그 경우 `ERROR` 상태로 표기된다(가짜값 ❌).

---

## 개발

```bash
# 백엔드 (검증 게이트)
cd backend && .venv/bin/ruff check . && .venv/bin/mypy . && .venv/bin/python -m pytest -q
# 프론트
cd frontend && npm run typecheck && npm run lint && npm test && npm run build
```

개발 규율(테스트 속임수 금지·정직성 우선 등)은 [CLAUDE.md](./CLAUDE.md), 진행 상태는 [STATUS.md](./STATUS.md) 참조.
