# MarketSpot

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE)

> 시장의 흐름을 포착하다 — 초보 장기 ETF 투자자를 위한, 조용하고 정직한 투자 동반자.

![MarketSpot 홈 대시보드](./assets/screenshots/home.png)

## 이걸 왜 만들었냐면

주식 투자에서 수익을 가장 크게 갉아먹는 건 사실 종목 선택이 아니라 **내 행동**이에요. 폭락장에 겁먹고 팔아버리거나, 오르는 걸 보고 뒤늦게 따라 사거나. MarketSpot은 화려한 지표를 잔뜩 늘어놓는 "터미널"이 아니라, 무서운 날 열었을 때 "괜찮아, 원래 이런 날도 있어"라고 담담하게 알려주는 도구를 목표로 만들었습니다.

그래서 원칙이 하나 있어요: **모르는 건 모른다고 한다.** 데이터가 없으면 그냥 없다고 표시하지, 그럴싸한 숫자로 채워 넣지 않습니다. AI도 마찬가지로 주가를 예측하거나 사라·팔라고 말하지 않아요. 이 원칙이 이 프로젝트의 거의 전부입니다.

개인 로컬 환경에서만 돌아가고, 무료 데이터를 쓰고, 로그인 같은 것도 없습니다.

---

## 뭘 할 수 있나요

- **안심 홈 대시보드** — "나 지금 괜찮은 건가?"에 한 줄로 답해주는 평결과, 그 근거가 되는 하락 맥락(예: *"VOO는 지난 10년간 5% 이상 조정을 14번 겪었고 전부 회복했어요, 보통 49일 걸렸습니다"*)을 보여줍니다. 내 투자 원칙, 포트폴리오 요약, 관심종목, 오늘 눈여겨볼 뉴스, 다가오는 일정도 한 화면에서. 카드는 원하는 대로 드래그해서 재배치하거나 숨길 수 있어요.
- **종목 상세** — 섹터·시총·PER·배당 같은 기본 정보부터 ETF가 실제로 뭘 담고 있는지, 차트(차분한 기본 모드와 RSI·MACD를 보는 탐구 모드), 관련 뉴스·공시까지.
- **포트폴리오** — 보유종목·수량·평단을 입력하면 실시간 평가액과 손익, 비중을 계산해줍니다. 시세를 못 가져온 종목은 억지로 채우지 않고 정직하게 빠집니다.
- **토스증권 연동** — 앱키/시크릿만 넣으면 계좌와 보유종목, 거래내역을 읽기 전용으로 동기화합니다(주문·매매 기능은 없어요). 앱이 계산한 보유수량과 토스 실제 잔고가 다르면 조용히 넘어가지 않고 드리프트로 그대로 보여줍니다. 한국 종목 시세를 보조하는 데도 씁니다.
- **AI 코치** — 오른쪽에서 토글로 열고 닫는 사이드바, 스트리밍으로 답합니다. 지금 상황을 먼저 읽고 말을 걸어주지만, 예측이나 매수·매도 조언은 하지 않습니다. Ollama가 안 켜져 있으면 규칙 기반으로 조용히 대체됩니다.

이 모든 데이터는 내부적으로 `DataEnvelope`라는 공통 틀(값 + 상태 + 출처 + 신선도)을 거쳐서 나갑니다. 그래서 뭔가 실패하거나 데이터가 없으면 반드시 `NO_DATA`, `NEEDS_KEY`, `ERROR` 같은 상태로 드러나요 — 화면에 어중간한 빈 칸이나 지어낸 숫자가 뜨는 일은 없습니다.

---

## 시작하기

### Docker Compose로 한 번에 (추천, 개발용)

```bash
docker compose up
#   브라우저에서 http://localhost:4000 열면 됩니다 (백엔드는 :8000)
#   코드를 고치면 바로 반영돼요 (백엔드 --reload, 프론트 Vite HMR)
#   AI는 호스트에 떠 있는 Ollama(:11434)를 그대로 씁니다 — 컨테이너에 모델을 다시 받지 않아요

docker compose up --build   # Dockerfile이나 의존성이 바뀌었을 때
docker compose down         # 끄기
```

AI 기능을 쓰려면 호스트에 [Ollama](https://ollama.com)가 떠 있어야 해요(없어도 규칙 기반으로 대체되긴 합니다):

```bash
ollama pull qwen3.5:9b-mlx   # 기본 모델(애플 실리콘 MLX, Ollama 0.30 이상)
```

### 상시 실행용 프로덕션 모드

빌드한 프론트+백엔드를 컨테이너 하나(:8000)로 서빙합니다. `--reload`나 HMR 없이 가볍고 빠르게 켜두고 쓰기 좋아요.

```bash
docker compose -f docker-compose.prod.yml up --build -d
# → http://127.0.0.1:8000 (프론트와 API가 한곳에서)
```

코드를 고쳐도 자동으로 반영되진 않으니, 수정했다면 `--build`로 다시 빌드해주세요. 개발할 땐 위의 `docker compose up`(핫리로드)이 훨씬 편합니다.

### Docker 없이 직접 실행

```bash
# 백엔드 (Python 3.11+; SEC 공시를 호출할 땐 연락처가 담긴 User-Agent를 넣어주는 게 좋습니다)
cd backend
SEC_USER_AGENT="MarketSpot/0.1 (local; you@example.com)" \
  .venv/bin/uvicorn app.main:app --port 8000

# 프론트 (새 터미널에서)
cd frontend && npm run dev    # http://localhost:4000 (/api 요청은 :8000으로 프록시됩니다)
```

---

## 어떻게 만들어져 있나요

```
backend/  FastAPI (Python 3.14) · Pydantic v2 · httpx
  app/
    models.py            DataEnvelope/DataStatus + 도메인 모델
    providers/            외부 데이터 어댑터(yfinance·SEC·토스·Yahoo검색…) → DataEnvelope로 정규화
    analytics/drawdown.py 하락 기저율 계산(순수 함수)
    services/             quotes·chart·news·portfolio·reassurance·home·spark…
    routers/               HTTP 엔드포인트
    config.py              settings.json(관심종목·UI·투자원칙·대시보드 레이아웃)
frontend/ React 18 + TypeScript + Vite
  src/
    components/           홈 위젯·종목 상세·AI 사이드바·차트(lightweight-charts)
    api/                   client.ts(엔드포인트) · types.ts(camelCase 계약)
    store/uiStore.ts       Zustand(UI 상태) · TanStack Query(서버 상태)
docker-compose.yml        backend + frontend (개발용)
```

**데이터 출처(전부 무료):** 시세·차트·뉴스·기본정보·일정은 yfinance(키 필요 없음, 미국 종목은 약 15분 지연) · 공시는 SEC EDGAR(키 필요 없음) 또는 DART(키 필요) · 심볼 검색은 Yahoo · 계좌 연동과 한국 시세 보조는 토스증권 Open API(키 필요) · AI는 로컬 Ollama를 씁니다.

### 주요 API

```
GET  /api/home                       안심 홈 평결
GET  /api/context/{symbol}|?symbols=  하락 맥락(기저율)
GET  /api/quotes?symbols=             시세        GET /api/chart/{symbol}
GET  /api/fundamentals/{symbol}       종목 기본정보
GET  /api/news?symbol=  ·  /api/news/digest?symbols=   뉴스·다이제스트
POST /api/ai/ask  ·  /api/ai/ask/stream               AI 코치(스트리밍)
GET  /api/filings?symbol=             공시(SEC)
GET  /api/portfolio  ·  PUT           포트폴리오
GET  /api/calendar?symbols=  ·  /api/spark?symbols=    일정·스파크라인
GET  /api/search?q=                   심볼 검색
GET  /api/settings   ·  PUT           로컬 설정(관심종목·UI·원칙·대시보드)
GET  /api/toss/status  ·  PUT /api/toss/account  ·  POST /api/toss/sync   토스증권 연동(읽기 전용)
```

---

## 설정과 보안, 꼭 읽어주세요

- 설정은 전부 로컬 파일에 저장됩니다: `backend/data/settings.json`(관심종목·UI·투자원칙·대시보드 레이아웃), `backend/data/portfolio.json`(보유 포지션).
- **API 키는 코드나 커밋에 절대 넣지 않습니다.** `.env`와 `settings.json`은 `.gitignore`로 빠져 있고, API 응답에서도 키는 항상 마스킹돼서 나갑니다. 저장소에 실제로 커밋되는 건 값이 비어 있는 `.env.example`뿐이에요.
- **토스증권 앱키·시크릿은 실제 증권 계좌에 접근할 수 있는 권한**이에요. 다른 무료 API 키들보다 훨씬 조심스럽게 다뤄주세요. 다만 이 앱이 쓰는 건 계좌 조회와 시세뿐이고, 주문을 넣는 기능은 아예 없습니다.
- 혼자 쓰는 로컬 앱이라 로그인도, DB도 없습니다. 즉 **인증이 전혀 없다**는 뜻이에요.
- `docker-compose.yml`은 기본적으로 호스트 포트를 `127.0.0.1`(내 컴퓨터에서만 접속 가능)에만 열어둡니다. 다른 기기(같은 LAN 안이라도)에서 접속하고 싶다면 포트 바인딩을 직접 바꿔야 하는데, 그 순간부터는 인증 없이 누구나 들어올 수 있다는 걸 꼭 알고 진행해주세요.
- 자주 쓰는 환경변수: `OLLAMA_HOST`(기본값 `http://localhost:11434`) · `SEC_USER_AGENT` · `STOCK_TERMINAL_DATA_DIR`.
- 이 폴더를 zip으로 압축하거나 백업해서 누군가에게 공유하기 전에는, `.env`에 넣어둔 키를 지우거나 새로 발급받아 바꿔주세요. `.env`는 커밋되지 않지만 디스크에는 평문으로 남아 있습니다.

---

## 지금은 이런 점이 아쉬워요

솔직하게 적어둡니다.

- 미국 시세는 약 15분 지연됩니다. 무료 정책상 어쩔 수 없는 부분이고, 적립식 장기 투자에는 크게 문제가 안 될 거예요.
- DART(한국 공시)는 키가 없으면 아예 안 뜨고, 키가 있어도 종목-기업코드 매핑이 아직 붙어 있지 않습니다.
- 포트폴리오 합계는 단일 통화(USD) 기준으로 계산돼요. 통화를 섞어서 보유하면 환산이 안 되고, 미실현 손익만 보여줍니다(거래내역·실현손익·배당은 아직 반영 안 됨).
- AI의 "사고(think)" 모드는 느립니다. 기본은 꺼둔 채로 빠른 스트리밍만 씁니다. MLX 모델을 쓰다 보면 아주 가끔 한글이 깨지기도 해요.
- yfinance는 공식 API가 아니라서 예고 없이 바뀌거나 멈출 수 있어요. 그럴 땐 `ERROR` 상태로 정직하게 표시됩니다(가짜 숫자로 채우지 않아요).
- 토스증권 연동으로 새로 발견되는 한국 종목을 코스피·코스닥 중 어디로 분류할지는 아직 확실하지 않습니다. 토스 API가 거래소 접미사 없이 종목 코드만 돌려주는데, 어느 거래소인지 구분할 방법이 응답 안에 있는지 실제 보유종목으로 아직 확인을 못 해봤어요. 확인되기 전까지는 무리해서 추측하지 않기로 했습니다.

---

## 개발하시는 분들께

```bash
# 백엔드 (검증 게이트)
cd backend && .venv/bin/ruff check . && .venv/bin/mypy . && .venv/bin/python -m pytest -q

# 프론트
cd frontend && npm run typecheck && npm run lint && npm test && npm run build
```

이 프로젝트는 "가짜 숫자를 만들지 않는다"는 원칙을 코드와 테스트에도 똑같이 적용하려고 합니다. 데이터가 없으면 없다고 정직하게 표시하는 쪽으로 코드를 짜주시면 정말 감사하겠습니다.

MIT 라이선스로 공개돼 있습니다. 자유롭게 가져다 쓰시고, 이슈나 PR도 언제든 환영합니다.
