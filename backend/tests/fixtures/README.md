# 테스트 픽스처 출처 (CLAUDE.md §1.3 — 진짜 응답만, 숫자 날조 금지)

모두 **실제 SEC EDGAR 응답**을 녹화 후 앞부분만 잘라낸 것이다. 값은 가공하지 않았다.

| 파일 | 출처 URL | 녹화일 | 비고 |
|---|---|---|---|
| `sec_submissions_aapl.json` | `https://data.sec.gov/submissions/CIK0000320193.json` | 2026-06-05 | Apple Inc. 최근 공시 12건만 |
| `sec_submissions_voo.json` | `https://data.sec.gov/submissions/CIK0000036405.json` | 2026-06-05 | VANGUARD INDEX FUNDS(VOO 신탁) 최근 12건 |
| `sec_company_tickers.json` | `https://www.sec.gov/files/company_tickers.json` | 2026-06-05 | 일반주식 티커→CIK 일부(AAPL/NVDA/TSLA/SPY/QQQ) |
| `sec_company_tickers_mf.json` | `https://www.sec.gov/files/company_tickers_mf.json` | 2026-06-05 | 펀드/ETF 티커→CIK 일부(VOO/QQQM/LACAX) |
| `yahoo_search_plt.json` | `https://query1.finance.yahoo.com/v1/finance/search?q=PLT` | 2026-06-08 | 심볼 검색 자동완성 — "PLT" 결과 7건 |
| `yf_fundamentals_aapl.json` | `yfinance Ticker("AAPL").info` | 2026-06-09 | 주식 기본정보(섹터·시총·PER·배당·요약) |
| `yf_fundamentals_voo.json` | `yfinance Ticker("VOO").info + funds_data` | 2026-06-09 | ETF 기본정보(카테고리·AUM·보유 top10) |

> 잘라낸 이유: 원본은 100KB~1MB 라 저장소에 통째로 두기엔 크다. 자른 뒤에도
> 각 배열의 인덱스 정렬(accessionNumber/filingDate/form …)은 원본 그대로 유지한다.
