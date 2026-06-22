import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import type { DrawdownContext } from "../api/types";
import { backendLabel } from "../lib/format";
import { useUIStore } from "../store/uiStore";

const HAS_DATA = ["LIVE", "DELAYED", "STALE"];

// 첫인사: 현재 종목의 맥락으로 *AI 도우미가 먼저 거는 말* + 이어 물어볼 만한 질문을
// 만든다(규칙기반, 즉시·정직 — 예측·매수매도 안 함).
function buildIntro(
  symbol: string,
  ctx: DrawdownContext | undefined,
): { greeting: string; chips: string[] } {
  const chips: string[] = [];
  const dd = ctx && HAS_DATA.includes(ctx.status) ? ctx.currentDrawdownPct : null;

  let ddContext = "";
  if (dd != null) {
    const p = dd.toFixed(1);
    if (dd <= -10) ddContext = ` 현재 ${symbol}는 고점 대비 ${p}% 구간에 있어요.`;
    else if (dd <= -3) ddContext = ` 현재 ${symbol}는 고점 대비 ${p}% 수준이에요.`;
    else ddContext = ` 현재 ${symbol}는 고점 대비 ${p}% 수준이에요.`;
  }

  const greeting =
    `${symbol}를 볼 때 따져볼 근거(밸류·기저율·거시·포트폴리오), 제가 하나씩 풀어드릴게요.${ddContext} ` +
    `대신 오를지 내릴지, 사라 팔라는 말은 안 해요.`;

  chips.push("PER이 무슨 뜻이야?");
  chips.push("지금 과열인지 어떻게 봐?");
  chips.push("기저율은 어떻게 읽어?");
  chips.push("내 포트폴리오에 어떤 영향?");

  return {
    greeting,
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
        <span className="ai-side-title">✦ AI 도우미</span>
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
