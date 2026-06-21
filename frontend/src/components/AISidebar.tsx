import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import type { DrawdownContext } from "../api/types";
import { backendLabel } from "../lib/format";
import { useUIStore } from "../store/uiStore";

const HAS_DATA = ["LIVE", "DELAYED", "STALE"];

// 선제 코치: 현재 종목의 하락 맥락으로 *코치가 먼저 거는 말* + 상황 맞춤 질문을
// 만든다(규칙기반, 즉시·정직 — 예측 안 함).
function buildIntro(
  symbol: string,
  ctx: DrawdownContext | undefined,
): { greeting: string; chips: string[] } {
  const chips: string[] = [];
  let mood = "무엇이든 편하게 물어보세요.";
  const dd = ctx && HAS_DATA.includes(ctx.status) ? ctx.currentDrawdownPct : null;

  if (dd != null) {
    const p = dd.toFixed(1);
    if (dd <= -10) mood = `${symbol}는 지금 고점 대비 ${p}% — 꽤 깊은 조정 구간이에요.`;
    else if (dd <= -3) mood = `오늘 좀 빨갛죠. ${symbol}는 고점 대비 ${p}% 수준이에요.`;
    else mood = `${symbol}는 고점 대비 ${p}% — 비교적 안정적인 흐름이에요.`;
    if (dd <= -3) chips.push("이 하락 정상이야?");
  }

  chips.push(`${symbol} 지금 어때?`);
  chips.push("지금 적립해도 괜찮은 구간이야?");
  chips.push("RSI가 70을 넘으면 무슨 뜻이야?");

  return {
    greeting: `${mood} (예측·매수매도 조언은 하지 않아요.)`,
    chips: chips.slice(0, 4),
  };
}

export function AISidebar() {
  const {
    aiOpen,
    toggleAi,
    aiMessages,
    aiThink,
    toggleThink,
    aiPending,
    clearAiPending,
    pushAiMessage,
    appendAiChunk,
    setLastAiBackend,
    clearAi,
    symbol,
  } = useUIStore();
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const bodyRef = useRef<HTMLDivElement | null>(null);

  const ctx = useQuery({
    queryKey: ["context", symbol],
    queryFn: () => api.context(symbol),
    enabled: aiOpen,
  });

  useEffect(() => {
    bodyRef.current?.scrollTo({ top: bodyRef.current.scrollHeight });
  }, [aiMessages, sending]);

  // 외부(예: 기본정보의 '쉽게 설명')에서 들어온 질문을 한 번 자동 전송.
  useEffect(() => {
    if (aiPending && !sending) {
      const q = aiPending;
      clearAiPending();
      void send(q);
    }
    // send/sending 은 의도적으로 제외 — aiPending 이 들어올 때 한 번만 전송한다.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [aiPending]);

  if (!aiOpen) return null;

  const intro = buildIntro(symbol, ctx.data);

  const send = async (q: string) => {
    const text = q.trim();
    if (!text || sending) return;
    setDraft("");
    const history = aiMessages
      .slice(-4)
      .map((m) => `${m.role === "user" ? "Q" : "A"}: ${m.text}`)
      .join("\n");
    const context = `현재 보고 있는 종목: ${symbol}.\n${history}`;
    pushAiMessage({ role: "user", text });
    pushAiMessage({ role: "assistant", text: "" }); // 스트리밍 대상
    setSending(true);
    try {
      const backend = await api.aiAskStream(context, text, aiThink, (chunk) =>
        appendAiChunk(chunk),
      );
      setLastAiBackend(backend);
    } catch {
      appendAiChunk("응답을 가져오지 못했어요. 잠시 후 다시 시도해 주세요.");
    } finally {
      setSending(false);
    }
  };

  return (
    <aside className="ai-side">
      <div className="ai-side-head">
        <span className="ai-side-title">✦ AI 코치</span>
        <div className="ai-side-actions">
          <button
            className={`ai-think ${aiThink ? "on" : ""}`}
            title="사고 모드 — 느리지만 더 깊은 추론"
            onClick={toggleThink}
          >
            🧠 사고 {aiThink ? "ON" : "OFF"}
          </button>
          {aiMessages.length > 0 && (
            <button className="ai-side-x" title="대화 비우기" onClick={clearAi}>
              지우기
            </button>
          )}
          <button className="ai-side-x" title="닫기" onClick={toggleAi}>
            ✕
          </button>
        </div>
      </div>

      <div className="ai-side-body" ref={bodyRef}>
        {aiMessages.length === 0 && (
          <>
            <div className="ai-msg ai-msg-assistant">
              <div className="ai-bubble">{intro.greeting}</div>
            </div>
            <div className="ai-suggestions">
              {intro.chips.map((c) => (
                <button key={c} className="chip" onClick={() => send(c)}>
                  {c}
                </button>
              ))}
            </div>
          </>
        )}

        {aiMessages.map((m, i) => (
          <div key={i} className={`ai-msg ai-msg-${m.role}`}>
            <div className="ai-bubble">
              {m.text || (m.role === "assistant" ? "생각 중…" : "")}
            </div>
            {m.role === "assistant" && m.backend === "rule" && (
              <div className="ai-msg-meta muted">{backendLabel(m.backend)}</div>
            )}
          </div>
        ))}
      </div>

      <div className="ai-side-input">
        <textarea
          placeholder="질문 입력 (Enter 전송 · Shift+Enter 줄바꿈)"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send(draft);
            }
          }}
        />
        <button
          className="icon-btn"
          disabled={sending || !draft.trim()}
          onClick={() => send(draft)}
        >
          전송
        </button>
      </div>
    </aside>
  );
}
