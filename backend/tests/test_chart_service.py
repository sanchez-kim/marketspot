"""차트 서비스 테스트.

★ 핵심 수용 기준(REQUIREMENTS FR-1): 기간/인터벌을 바꾸면 캐시 키가 달라져
실제로 새 데이터가 로드된다. 동일 파라미터는 캐시로 재사용된다.
"""

from __future__ import annotations

import pytest

from app.cache import TTLCache
from app.models import ChartData, DataEnvelope, DataStatus
from app.providers.registry import ProviderRegistry
from app.services.chart import ChartService, chart_cache_key

from .fakes import FakeProvider


def _service(provider: FakeProvider) -> tuple[ChartService, FakeProvider]:
    reg = ProviderRegistry({"US": [provider]})
    cache: TTLCache[DataEnvelope[ChartData]] = TTLCache()
    return ChartService(reg, cache), provider


@pytest.mark.asyncio
async def test_returns_chart_with_indicators() -> None:
    svc, _ = _service(FakeProvider("p", bars_status=DataStatus.DELAYED))
    env = await svc.get_chart("AAPL", "1Y", "1D")

    assert env.data is not None
    assert env.data.symbol == "AAPL"
    assert len(env.data.bars) == 40
    assert len(env.data.indicators.rsi) == 40  # 지표가 봉과 동일 길이로 채워짐


@pytest.mark.asyncio
async def test_same_params_use_cache_no_refetch() -> None:
    svc, provider = _service(FakeProvider("p"))
    await svc.get_chart("AAPL", "1Y", "1D")
    await svc.get_chart("AAPL", "1Y", "1D")

    assert provider.bars_calls == 1  # 두번째는 캐시


@pytest.mark.asyncio
async def test_different_period_refetches() -> None:
    svc, provider = _service(FakeProvider("p"))
    await svc.get_chart("AAPL", "1Y", "1D")
    await svc.get_chart("AAPL", "6M", "1D")  # 기간 변경

    assert provider.bars_calls == 2  # 새 데이터 로드됨


@pytest.mark.asyncio
async def test_different_interval_refetches() -> None:
    svc, provider = _service(FakeProvider("p"))
    await svc.get_chart("AAPL", "1Y", "1D")
    await svc.get_chart("AAPL", "1Y", "1W")  # 인터벌 변경

    assert provider.bars_calls == 2


@pytest.mark.asyncio
async def test_error_is_not_cached() -> None:
    svc, provider = _service(FakeProvider("p", bars_status=DataStatus.ERROR))
    env1 = await svc.get_chart("AAPL", "1Y", "1D")
    env2 = await svc.get_chart("AAPL", "1Y", "1D")

    assert env1.status is DataStatus.ERROR
    assert env1.data is None
    assert env2.status is DataStatus.ERROR
    assert provider.bars_calls == 2  # 에러는 캐시 안 되어 재시도됨


def test_cache_key_includes_all_params() -> None:
    k1 = chart_cache_key("AAPL", "1Y", "1D")
    k2 = chart_cache_key("AAPL", "6M", "1D")
    k3 = chart_cache_key("AAPL", "1Y", "1W")
    assert k1 != k2 != k3
    assert k1 != k3
    # 대소문자 정규화
    assert chart_cache_key("aapl", "1y", "1d") == k1
