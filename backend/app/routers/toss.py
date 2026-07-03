"""토스증권 연동 라우터 (Phase A, 스펙 §3.4).

- ``GET  /api/toss/status``  — 연동 여부·계좌 목록·선택 계좌·마지막 동기화.
- ``PUT  /api/toss/account`` — 선택 계좌 seq 저장.
- ``POST /api/toss/sync``    — 부트스트랩(최초) 또는 증분 동기화 실행.

모든 응답은 ``DataEnvelope`` 로 감싼다 — 키 없음 ``NEEDS_KEY``, 레이트리밋
``RATE_LIMITED``, 그 외 실패 ``ERROR``(§0: 에러를 삼키지 않고 상태로 변환).
"""

from __future__ import annotations

from typing import Annotated

import httpx
from fastapi import APIRouter, Depends

from ..config import load_settings, set_toss_account_seq
from ..deps import get_toss_client_factory, get_toss_sync_service
from ..models import (
    CamelModel,
    DataEnvelope,
    DataStatus,
    TossAccountInfo,
    TossStatus,
    TossSyncResult,
)
from ..providers.toss_client import TossAccount, TossClient
from ..services.toss_sync import TossSyncError, TossSyncService

router = APIRouter(prefix="/api/toss", tags=["toss"])

_SOURCE = "toss"


class AccountUpdate(CamelModel):
    account_seq: str  # 프론트는 camelCase(accountSeq)로 보낸다


def _has_keys() -> bool:
    keys = load_settings().api_keys
    return bool(keys.toss_app_key and keys.toss_app_secret)


def _account_label(acc: TossAccount) -> str:
    kind = acc.account_type or "계좌"
    return f"{kind} ({acc.account_no})"


def _to_info(acc: TossAccount) -> TossAccountInfo:
    return TossAccountInfo(
        account_seq=str(acc.account_seq),
        account_no=acc.account_no,
        account_type=acc.account_type,
        label=_account_label(acc),
    )


def _toss_error_message(exc: BaseException) -> str:
    """토스 표준 에러 바디(``{"error":{"message":...}}``)에서 사람이 읽을
    메시지를 뽑는다(문서 확인, 2026-07). ``httpx.HTTPStatusError`` 가 아니거나
    응답이 그 형식이 아니면(연결 오류 등) httpx 의 일반 문자열로 폴백한다
    (§0 — 정보를 못 뽑아도 조용히 삼키지 않고 뭔가는 보여준다).
    """
    if isinstance(exc, httpx.HTTPStatusError):
        try:
            body = exc.response.json()
            msg = body.get("error", {}).get("message")
            if isinstance(msg, str) and msg:
                return msg
        except ValueError:
            pass
    return str(exc)


def _http_error_envelope(exc: httpx.HTTPError) -> DataEnvelope[TossStatus]:
    """httpx 오류 → 적절한 DataStatus 봉투(429 는 RATE_LIMITED, 그 외 ERROR)."""
    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 429:
        return DataEnvelope[TossStatus].empty(
            source=_SOURCE,
            status=DataStatus.RATE_LIMITED,
            message="토스 API 호출 제한에 도달했습니다. 잠시 후 다시 시도하세요.",
        )
    return DataEnvelope[TossStatus].empty(
        source=_SOURCE,
        status=DataStatus.ERROR,
        message=f"토스 API 오류: {_toss_error_message(exc)}",
    )


async def _build_status() -> DataEnvelope[TossStatus]:
    """현재 설정 + 계좌 목록으로 상태 봉투를 만든다(키 있을 때만 네트워크)."""
    if not _has_keys():
        return DataEnvelope[TossStatus].empty(
            source=_SOURCE,
            status=DataStatus.NEEDS_KEY,
            message="토스증권 app key/secret 를 설정에서 입력하세요.",
        )
    settings = load_settings()
    factory = get_toss_client_factory()
    client: TossClient = factory()
    try:
        accounts = await client.get_accounts()
    except httpx.HTTPError as exc:
        return _http_error_envelope(exc)
    finally:
        await client.aclose()

    status = TossStatus(
        connected=True,
        accounts=[_to_info(a) for a in accounts],
        selected_account_seq=settings.toss_account_seq or None,
        last_sync=settings.toss_last_sync or None,
    )
    return DataEnvelope.ok(status, source=_SOURCE, status=DataStatus.LIVE)


@router.get("/status")
async def toss_status() -> DataEnvelope[TossStatus]:
    return await _build_status()


@router.put("/account")
async def set_account(body: AccountUpdate) -> DataEnvelope[TossStatus]:
    if not _has_keys():
        return DataEnvelope[TossStatus].empty(
            source=_SOURCE,
            status=DataStatus.NEEDS_KEY,
            message="토스증권 app key/secret 를 먼저 설정하세요.",
        )
    set_toss_account_seq(body.account_seq.strip())
    return await _build_status()


@router.post("/sync")
async def toss_sync(
    service: Annotated[TossSyncService, Depends(get_toss_sync_service)],
) -> DataEnvelope[TossSyncResult]:
    if not _has_keys():
        return DataEnvelope[TossSyncResult].empty(
            source=_SOURCE,
            status=DataStatus.NEEDS_KEY,
            message="토스증권 app key/secret 를 먼저 설정하세요.",
        )
    account_seq = load_settings().toss_account_seq.strip()
    if not account_seq:
        return DataEnvelope[TossSyncResult].empty(
            source=_SOURCE,
            status=DataStatus.NO_DATA,
            message="동기화할 계좌를 먼저 선택하세요.",
        )

    try:
        if service.has_baseline(account_seq):
            result = await service.incremental(account_seq)
        else:
            result = await service.bootstrap(account_seq)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 429:
            return DataEnvelope[TossSyncResult].empty(
                source=_SOURCE,
                status=DataStatus.RATE_LIMITED,
                message="토스 API 호출 제한에 도달했습니다. 잠시 후 다시 시도하세요.",
            )
        return DataEnvelope[TossSyncResult].empty(
            source=_SOURCE,
            status=DataStatus.ERROR,
            message=f"토스 API 오류: {_toss_error_message(exc)}",
        )
    except (httpx.HTTPError, TossSyncError) as exc:
        return DataEnvelope[TossSyncResult].empty(
            source=_SOURCE,
            status=DataStatus.ERROR,
            message=f"동기화 실패: {_toss_error_message(exc)}",
        )

    try:
        result.drift = await service.drift_check(account_seq)
    except (httpx.HTTPError, TossSyncError) as exc:
        # 동기화(거래 저장)는 이미 성공했다 — 드리프트 확인이 실패했다고
        # 그 성공을 지워버리지 않는다(§0: 부분 성공을 숨기지 않는다).
        # drift 는 "모른다"는 뜻으로 빈 채 두고, message 로 정직하게 알린다.
        return DataEnvelope[TossSyncResult](
            data=result,
            status=DataStatus.LIVE,
            source=_SOURCE,
            message=(
                "동기화는 완료됐지만 잔고 대조(드리프트 확인)는 실패했습니다: "
                f"{_toss_error_message(exc)}"
            ),
        )

    return DataEnvelope.ok(result, source=_SOURCE, status=DataStatus.LIVE)
