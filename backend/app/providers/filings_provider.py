"""공시(Filings) 제공자.

미국: SEC EDGAR (키 불필요, User-Agent 필요). 티커→CIK 매핑 후 submissions
JSON 을 정규화한다. ETF/펀드는 신탁(trust) 단위 CIK 로 보고되므로 entity 에
신탁명을 그대로 노출해 정직하게 표기한다.

한국: DART. 키가 없으면 ``NEEDS_KEY`` 로 정직하게 표기한다. corp_code 매핑은
아직 연동되지 않았다(STATUS 의 알려진 한계 참조).

가짜 데이터 금지(CLAUDE.md §0): 실패/미구현은 적절한 ``DataStatus`` 로만
표기하고 임의 값으로 채우지 않는다.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from datetime import datetime
from typing import Protocol, runtime_checkable

import httpx

from ..models import DataEnvelope, DataStatus, Filing, FilingList

JsonDict = Mapping[str, object]

_SEC_UA = os.environ.get(
    "SEC_USER_AGENT", "MarketSpot/0.1 (local research; contact: user@example.com)"
)
_SEC_TICKERS = "https://www.sec.gov/files/company_tickers.json"
_SEC_TICKERS_MF = "https://www.sec.gov/files/company_tickers_mf.json"


def _submissions_url(cik: str) -> str:
    return f"https://data.sec.gov/submissions/CIK{cik}.json"


@runtime_checkable
class FilingsProvider(Protocol):
    name: str

    async def get_filings(
        self, symbol: str, limit: int = 20
    ) -> DataEnvelope[FilingList]: ...


# ---- 순수 파싱 함수(네트워크 없음, 테스트 대상) -------------------------------


def build_ticker_index(stock_map: JsonDict, fund_map: JsonDict) -> dict[str, str]:
    """SEC 티커 매핑 두 종류를 합쳐 ``{TICKER: 10자리 CIK}`` 로 만든다.

    - ``company_tickers.json``: ``{"0": {"cik_str": int, "ticker": str, ...}}``
    - ``company_tickers_mf.json``: ``{"fields": [...], "data": [[cik, .., sym]]}``

    일반주식을 우선한다(펀드 매핑은 같은 티커가 있으면 덮어쓰지 않는다).
    """
    index: dict[str, str] = {}

    # 펀드 먼저 채우고 → 주식으로 덮어써서 주식 우선이 되게 한다.
    data = fund_map.get("data")
    if isinstance(data, list):
        for row in data:
            if isinstance(row, list) and len(row) >= 4:
                cik, sym = row[0], row[3]
                if isinstance(cik, int) and isinstance(sym, str):
                    index[sym.upper()] = f"{cik:010d}"

    for entry in stock_map.values():
        if isinstance(entry, Mapping):
            cik = entry.get("cik_str")
            sym = entry.get("ticker")
            if isinstance(cik, int) and isinstance(sym, str):
                index[sym.upper()] = f"{cik:010d}"

    return index


def _filing_url(cik_int: int, accession: str, primary_doc: str) -> str:
    """공시 원문(또는 접수 디렉터리) URL 을 만든다."""
    acc_nodash = accession.replace("-", "")
    base = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc_nodash}"
    return f"{base}/{primary_doc}" if primary_doc else f"{base}/"


def _parse_date(value: object) -> datetime | None:
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return None


def parse_submissions(payload: JsonDict, limit: int = 20) -> FilingList:
    """SEC submissions JSON → ``FilingList`` (순수 함수)."""
    cik_raw = payload.get("cik")
    cik_int = int(cik_raw) if isinstance(cik_raw, (int, str)) and str(cik_raw) else 0
    cik_str = f"{cik_int:010d}" if cik_int else None
    name = payload.get("name")
    entity = name if isinstance(name, str) and name else "(이름 없음)"

    filings_obj = payload.get("filings")
    recent: JsonDict = {}
    if isinstance(filings_obj, Mapping):
        r = filings_obj.get("recent")
        if isinstance(r, Mapping):
            recent = r

    forms = recent.get("form")
    if not isinstance(forms, list):
        return FilingList(entity=entity, cik=cik_str, market="US", filings=[])

    accs = _col(recent, "accessionNumber")
    filed = _col(recent, "filingDate")
    reports = _col(recent, "reportDate")
    docs = _col(recent, "primaryDocument")
    descs = _col(recent, "primaryDocDescription")

    items: list[Filing] = []
    for i, form in enumerate(forms):
        if not isinstance(form, str) or not form:
            continue
        filed_dt = _parse_date(_at(filed, i))
        if filed_dt is None:  # 접수일이 없으면 정직하게 제외
            continue
        acc = str(_at(accs, i) or "")
        desc = _at(descs, i)
        title = desc if isinstance(desc, str) and desc.strip() else form
        items.append(
            Filing(
                form=form,
                title=title,
                filed=filed_dt,
                report_date=_parse_date(_at(reports, i)),
                url=_filing_url(cik_int, acc, str(_at(docs, i) or "")),
                accession=acc,
            )
        )
        if len(items) >= limit:
            break

    return FilingList(entity=entity, cik=cik_str, market="US", filings=items)


def _col(recent: JsonDict, key: str) -> list[object]:
    v = recent.get(key)
    return v if isinstance(v, list) else []


def _at(col: list[object], i: int) -> object:
    return col[i] if i < len(col) else None


# ---- 미국: SEC EDGAR ---------------------------------------------------------


class SecEdgarProvider:
    name = "sec-edgar"

    def __init__(self) -> None:
        self._index: dict[str, str] | None = None

    async def _ticker_index(self, client: httpx.AsyncClient) -> dict[str, str]:
        if self._index is None:
            stock_resp = await client.get(_SEC_TICKERS)
            stock_resp.raise_for_status()
            fund_resp = await client.get(_SEC_TICKERS_MF)
            fund_resp.raise_for_status()
            self._index = build_ticker_index(stock_resp.json(), fund_resp.json())
        return self._index

    async def get_filings(
        self, symbol: str, limit: int = 20
    ) -> DataEnvelope[FilingList]:
        headers = {"User-Agent": _SEC_UA, "Accept-Encoding": "gzip, deflate"}
        try:
            async with httpx.AsyncClient(timeout=15, headers=headers) as client:
                index = await self._ticker_index(client)
                cik = index.get(symbol.upper())
                if cik is None:
                    return DataEnvelope[FilingList].empty(
                        source=self.name,
                        status=DataStatus.NO_DATA,
                        message=f"'{symbol}' 의 SEC CIK 를 찾지 못했습니다",
                    )
                resp = await client.get(_submissions_url(cik))
                if resp.status_code == 429:
                    return DataEnvelope[FilingList].empty(
                        source=self.name,
                        status=DataStatus.RATE_LIMITED,
                        message="SEC 호출 제한에 도달했습니다",
                    )
                resp.raise_for_status()
                payload = resp.json()
        except httpx.HTTPError as exc:
            return DataEnvelope[FilingList].empty(
                source=self.name,
                status=DataStatus.ERROR,
                message=f"SEC 공시 조회 실패: {exc}",
            )

        result = parse_submissions(payload, limit)
        if not result.filings:
            return DataEnvelope[FilingList].empty(
                source=self.name,
                status=DataStatus.NO_DATA,
                message=f"'{symbol}' 관련 공시가 없습니다",
            )
        # 공시는 접수 후 공개되는 지연 데이터
        as_of = _latest_filed(result.filings)
        return DataEnvelope.ok(
            result, source=self.name, status=DataStatus.DELAYED, as_of=as_of
        )


def _latest_filed(filings: list[Filing]) -> datetime | None:
    return max((f.filed for f in filings), default=None)


# ---- 한국: DART --------------------------------------------------------------


class DartProvider:
    """DART 공시 제공자.

    키가 없으면 ``NEEDS_KEY``. 키가 있어도 corp_code(corpCode.zip) 매핑이
    아직 연동되지 않아 데이터를 만들지 않는다 — 가짜로 채우지 않고 정직하게
    표기한다(STATUS 알려진 한계).
    """

    name = "dart"

    def __init__(self, api_key: str = "") -> None:
        self._api_key = api_key

    async def get_filings(
        self, symbol: str, limit: int = 20
    ) -> DataEnvelope[FilingList]:
        if not self._api_key:
            return DataEnvelope[FilingList].empty(
                source=self.name,
                status=DataStatus.NEEDS_KEY,
                message="DART API 키가 필요합니다 (설정에서 입력)",
            )
        return DataEnvelope[FilingList].empty(
            source=self.name,
            status=DataStatus.NO_DATA,
            message="DART corp_code 매핑이 아직 연동되지 않았습니다",
        )
