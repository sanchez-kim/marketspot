"""코치 프롬프트/예산 — 간결한 답변 + 정직성 유지 검증(네트워크 없음)."""

from __future__ import annotations

from app.ai.ollama_backend import _ask_budget, _coach_prompt


def test_normal_answer_budget_is_concise() -> None:
    # 일반 모드 답변은 장황하지 않게 토큰 예산을 짧게 둔다.
    assert _ask_budget(False) <= 400
    # 사고 모드는 thinking 토큰 때문에 여전히 넉넉해야 한다.
    assert _ask_budget(True) > _ask_budget(False)


def test_coach_prompt_demands_brevity_without_greeting() -> None:
    p = _coach_prompt("현재 종목: VOO. PER 26.9.", "PER이 뭐야?", beginner=True)
    # 간결 + 인사말/장황한 서두 금지
    assert "간결" in p
    assert "인사말" in p
    # 정직성(예측·매수매도 금지)은 유지
    assert "예측" in p
    assert "사라" in p or "매수" in p
    # 맥락/질문을 그대로 임베드
    assert "PER 26.9" in p
    assert "PER이 뭐야?" in p
