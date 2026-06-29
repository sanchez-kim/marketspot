import { create } from "zustand";
import type { Interval, Period } from "../api/types";

export type TabId = "home" | "symbol" | "portfolio";

export interface ChatMessage {
  role: "user" | "assistant";
  text: string;
  backend?: string; // assistant 메시지의 응답 엔진
}

interface UIState {
  activeTab: TabId;
  symbol: string; // 현재 선택 종목
  period: Period;
  interval: Interval;
  upColor: "green" | "red"; // 미국식 / 한국식
  density: "comfortable" | "normal" | "compact";
  baseCurrency: "KRW" | "USD"; // 기준 통화 — 포트폴리오 합계 표시 단위

  aiOpen: boolean; // AI 사이드바 표시 여부
  aiMessages: ChatMessage[]; // 연속 대화 기록(토글해도 유지)
  aiThink: boolean; // 사고(thinking) 모드 — 느리지만 더 깊은 추론
  aiPending: string | null; // 외부에서 코치에게 보낼 질문(자동 전송)
  exploreMode: boolean; // 탐구 모드(RSI/MACD 등). 기본 off=차분
  // 살펴보기 검토모드 — ④패널 강조점만 바꾼다(추가매수/보유점검/신규편입)
  reviewMode: "add" | "hold" | "new";
  setReviewMode: (m: "add" | "hold" | "new") => void;

  setTab: (t: TabId) => void;
  setSymbol: (s: string) => void;
  setPeriod: (p: Period) => void;
  setInterval: (i: Interval) => void;
  setUpColor: (c: "green" | "red") => void;
  setDensity: (d: "comfortable" | "normal" | "compact") => void;
  setBaseCurrency: (c: "KRW" | "USD") => void;
  toggleAi: () => void;
  pushAiMessage: (m: ChatMessage) => void;
  appendAiChunk: (text: string) => void; // 마지막 메시지에 토큰 누적(스트리밍)
  setLastAiBackend: (backend: string) => void;
  clearAi: () => void;
  toggleThink: () => void;
  askAi: (question: string) => void; // 사이드바 열고 질문 자동 전송
  clearAiPending: () => void;
  toggleExplore: () => void;

  helpOpen: boolean;
  tourOpen: boolean;
  openHelp: () => void;
  closeHelp: () => void;
  startTour: () => void;
  endTour: () => void;

  settingsOpen: boolean;
  openSettings: () => void;
  closeSettings: () => void;
}

export const useUIStore = create<UIState>((set) => ({
  activeTab: "home",
  symbol: "VOO",
  period: "1Y",
  interval: "1D",
  upColor: "green",
  density: "comfortable",
  baseCurrency: "USD",

  aiOpen: false,
  aiMessages: [],
  aiThink: false,
  aiPending: null,
  exploreMode: false,
  reviewMode: "add",
  setReviewMode: (reviewMode) => set({ reviewMode }),

  setTab: (activeTab) => set({ activeTab }),
  setSymbol: (symbol) => set({ symbol }),
  setPeriod: (period) => set({ period }),
  setInterval: (interval) => set({ interval }),
  setUpColor: (upColor) => set({ upColor }),
  setDensity: (density) => set({ density }),
  setBaseCurrency: (baseCurrency) => set({ baseCurrency }),
  toggleAi: () => set((s) => ({ aiOpen: !s.aiOpen })),
  pushAiMessage: (m) => set((s) => ({ aiMessages: [...s.aiMessages, m] })),
  appendAiChunk: (text) =>
    set((s) => {
      const msgs = s.aiMessages.slice();
      const last = msgs[msgs.length - 1];
      if (last) msgs[msgs.length - 1] = { ...last, text: last.text + text };
      return { aiMessages: msgs };
    }),
  setLastAiBackend: (backend) =>
    set((s) => {
      const msgs = s.aiMessages.slice();
      const last = msgs[msgs.length - 1];
      if (last) msgs[msgs.length - 1] = { ...last, backend };
      return { aiMessages: msgs };
    }),
  clearAi: () => set({ aiMessages: [] }),
  toggleThink: () => set((s) => ({ aiThink: !s.aiThink })),
  askAi: (question) => set({ aiOpen: true, aiPending: question }),
  clearAiPending: () => set({ aiPending: null }),
  toggleExplore: () => set((s) => ({ exploreMode: !s.exploreMode })),

  helpOpen: false,
  tourOpen: false,
  openHelp: () => set({ helpOpen: true }),
  closeHelp: () => set({ helpOpen: false }),
  startTour: () => set({ tourOpen: true }),
  endTour: () => set({ tourOpen: false }),

  settingsOpen: false,
  openSettings: () => set({ settingsOpen: true }),
  closeSettings: () => set({ settingsOpen: false }),
}));
