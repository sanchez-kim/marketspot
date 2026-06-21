"""yfinance 시세 파싱 regression 테스트(네트워크 없음).

실제 ``FastInfo`` 를 흉내 낸 가짜 객체로 검증한다: dict 키는 camelCase 지만
속성은 snake_case 다. 이 구분을 놓쳐 시세가 NO_DATA 로 나오던 버그를 고정한다.
"""

from __future__ import annotations

from app.providers.yfinance_provider import quote_from_fast_info


class FakeFastInfo:
    """yfinance FastInfo 모사: snake_case 속성 + camelCase dict 키."""

    def __init__(self, last_price: float, previous_close: float, currency: str) -> None:
        self.last_price = last_price
        self.previous_close = previous_close
        self.currency = currency
        self._d = {
            "lastPrice": last_price,
            "previousClose": previous_close,
            "currency": currency,
        }

    def get(self, key: str, default: object = None) -> object:
        # 실제 FastInfo 처럼 camelCase 키만 인식 → 'last_price' 로는 못 찾음
        return self._d.get(key, default)


def test_parses_quote_via_attribute_access() -> None:
    fi = FakeFastInfo(last_price=696.06, previous_close=690.06, currency="USD")
    q = quote_from_fast_info("VOO", fi)
    assert q is not None
    assert q.price == 696.06
    assert q.currency == "USD"
    assert q.change is not None
    assert abs(q.change - 6.0) < 1e-6
    assert q.change_pct is not None
    assert q.change_pct > 0


def test_regression_dict_get_snake_case_would_fail() -> None:
    # 과거 버그 경로(.get('last_price'))는 None 을 반환했음을 명시적으로 고정
    fi = FakeFastInfo(last_price=100.0, previous_close=100.0, currency="USD")
    assert fi.get("last_price") is None  # camelCase 키만 있으므로
    # 그러나 올바른 구현(속성 접근)은 정상 동작해야 한다
    q = quote_from_fast_info("X", fi)
    assert q is not None
    assert q.price == 100.0


def test_no_price_returns_none() -> None:
    class Empty:
        pass

    assert quote_from_fast_info("X", Empty()) is None
