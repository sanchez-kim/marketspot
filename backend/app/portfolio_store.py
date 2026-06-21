"""포트폴리오 보유 포지션 로컬 저장 (data/portfolio.json).

로그인 없는 단일 사용자라 파일 하나로 보관한다. 시세/평가는 저장하지 않고
**원금 정보(symbol/quantity/avgCost)만** 저장한다 — 평가는 항상 실시간 시세로
계산한다(가짜 스냅샷 금지).
"""

from __future__ import annotations

import json

from .config import data_dir
from .models import Position


def _path() -> str:
    return str(data_dir() / "portfolio.json")


def load_positions() -> list[Position]:
    path = _path()
    try:
        raw = json.loads(open(path, encoding="utf-8").read())
    except FileNotFoundError:
        return []
    if not isinstance(raw, list):
        return []
    return [Position.model_validate(item) for item in raw]


def save_positions(positions: list[Position]) -> None:
    payload = [p.model_dump(by_alias=True) for p in positions]
    with open(_path(), "w", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False, indent=2))
