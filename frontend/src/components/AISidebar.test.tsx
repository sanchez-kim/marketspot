import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AISidebar } from "./AISidebar";
import { api } from "../api/client";
import { useUIStore } from "../store/uiStore";

function renderSidebar() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  qc.setQueryData(["context", "VOO"], null);
  return render(
    <QueryClientProvider client={qc}>
      <AISidebar />
    </QueryClientProvider>,
  );
}

describe("AISidebar explainer tone", () => {
  beforeEach(() => {
    useUIStore.setState({
      aiOpen: true,
      aiMessages: [],
      symbol: "VOO",
      activeTab: "symbol",
    });
  });
  it("opens with an explainer intro (not a do-nothing reassurance)", () => {
    renderSidebar();
    // intro mentions explaining the evidence, not "그냥 두세요/안심"
    expect(screen.getAllByText(/근거|설명/).length).toBeGreaterThan(0);
    expect(screen.queryByText(/아무것도 하지|그냥 두세요/)).not.toBeInTheDocument();
  });

  it("shows a limited-mode banner when the latest answer is rule-based (Ollama 미연결)", () => {
    useUIStore.setState({
      aiOpen: true,
      symbol: "VOO",
      activeTab: "symbol",
      aiMessages: [
        { role: "user", text: "PER이 뭐야?" },
        { role: "assistant", text: "주가수익비율…", backend: "rule" },
      ],
    });
    renderSidebar();
    expect(screen.getByText(/규칙 기반으로 동작 중/)).toBeInTheDocument();
  });
});

describe("AISidebar greeting depends on active tab (§0 honesty — no unpicked ticker)", () => {
  afterEach(() => {
    // restore default so other describe blocks aren't affected by tab bleed
    useUIStore.setState({ activeTab: "home" });
  });

  it("uses a neutral, ticker-free greeting when NOT on the 살펴보기(symbol) tab", () => {
    useUIStore.setState({
      aiOpen: true,
      aiMessages: [],
      symbol: "VOO",
      activeTab: "home",
    });
    renderSidebar();
    // must not mention the default/leftover ticker as if the user picked it
    expect(screen.queryByText(/VOO/)).not.toBeInTheDocument();
    // neutral copy pointing the user to the 살펴보기 tab
    expect(screen.getByText(/살펴보기/)).toBeInTheDocument();
  });

  it("keeps the existing symbol-specific greeting when on the 살펴보기(symbol) tab", () => {
    useUIStore.setState({
      aiOpen: true,
      aiMessages: [],
      symbol: "VOO",
      activeTab: "symbol",
    });
    renderSidebar();
    expect(screen.getAllByText(/VOO/).length).toBeGreaterThan(0);
  });
});

describe("AISidebar markdown rendering", () => {
  beforeEach(() => {
    useUIStore.setState({
      aiOpen: true,
      symbol: "VOO",
      aiMessages: [{ role: "assistant", text: "**굵게** 설명\n\n- 항목1\n- 항목2" }],
    });
  });

  it("renders assistant markdown as HTML (bold + list), not raw asterisks", () => {
    const { container } = renderSidebar();
    expect(container.querySelector("strong")?.textContent).toBe("굵게");
    expect(container.querySelectorAll("li").length).toBe(2);
    // the literal markdown syntax must not leak as visible text
    expect(screen.queryByText(/\*\*굵게\*\*/)).not.toBeInTheDocument();
  });
});

describe("AISidebar pending-question queue", () => {
  beforeEach(() => {
    useUIStore.setState({
      aiOpen: true,
      aiMessages: [],
      symbol: "VOO",
      aiPending: null,
    });
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("does not drop a question queued while a previous answer is still streaming", async () => {
    let resolveFirst!: () => void;
    const asked: string[] = [];
    vi.spyOn(api, "aiAskStream").mockImplementation(
      async (_ctx: string, question: string) => {
        asked.push(question);
        if (asked.length === 1) {
          await new Promise<void>((res) => {
            resolveFirst = res;
          });
        }
        return "ollama";
      },
    );
    renderSidebar();

    // Q1 auto-sends via aiPending and starts streaming (stays in flight).
    act(() => useUIStore.getState().askAi("질문1"));
    await waitFor(() => expect(asked).toContain("질문1"));

    // Q2 queued WHILE Q1 is still streaming — must not be silently dropped.
    act(() => useUIStore.getState().askAi("질문2"));

    // Q1 finishes; Q2 should then be sent.
    await act(async () => {
      resolveFirst();
    });
    await waitFor(() => expect(asked).toContain("질문2"));
  });
});
