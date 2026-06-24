import type {
  AskResult,
  CalendarEvent,
  ChartData,
  DataEnvelope,
  DrawdownContext,
  FilingList,
  Fundamentals,
  HomeVerdict,
  Interval,
  MacroConditions,
  NewsItem,
  NewsSummaryResult,
  Period,
  PortfolioRisk,
  PortfolioSummary,
  Quote,
  SafeSettings,
  SettingsPatch,
  StripItem,
  SymbolMatch,
  Transaction,
  ValuationContext,
} from "./types";

async function postJSON<T>(url: string, body: unknown): Promise<T> {
  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!resp.ok) throw new Error(`요청 실패 (${resp.status}): ${url}`);
  return (await resp.json()) as T;
}

async function getJSON<T>(url: string): Promise<T> {
  const resp = await fetch(url);
  if (!resp.ok) {
    throw new Error(`요청 실패 (${resp.status}): ${url}`);
  }
  return (await resp.json()) as T;
}

async function delJSON<T>(url: string): Promise<T> {
  const resp = await fetch(url, {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
  });
  if (!resp.ok) throw new Error(`요청 실패 (${resp.status}): ${url}`);
  return (await resp.json()) as T;
}

export const api = {
  quotes: (symbols: string[]) =>
    getJSON<Record<string, DataEnvelope<Quote>>>(
      `/api/quotes?symbols=${encodeURIComponent(symbols.join(","))}`,
    ),

  chart: (symbol: string, period: Period, interval: Interval) =>
    getJSON<DataEnvelope<ChartData>>(
      `/api/chart/${encodeURIComponent(symbol)}?period=${period}&interval=${interval}`,
    ),

  strip: () => getJSON<StripItem[]>(`/api/macro/strip`),

  calendar: (symbols: string[], limit = 6) =>
    getJSON<CalendarEvent[]>(
      `/api/calendar?symbols=${encodeURIComponent(symbols.join(","))}&limit=${limit}`,
    ),

  spark: (symbols: string[], period = "3M") =>
    getJSON<Record<string, number[]>>(
      `/api/spark?symbols=${encodeURIComponent(symbols.join(","))}&period=${period}`,
    ),

  news: (symbol: string, limit = 20) =>
    getJSON<DataEnvelope<NewsItem[]>>(
      `/api/news?symbol=${encodeURIComponent(symbol)}&limit=${limit}`,
    ),

  summarizeNews: (symbol: string, limit = 12) =>
    postJSON<NewsSummaryResult>(`/api/news/summarize`, { symbol, limit }),

  newsDigest: (symbols: string[], top = 6) =>
    getJSON<NewsSummaryResult>(
      `/api/news/digest?symbols=${encodeURIComponent(symbols.join(","))}&top=${top}`,
    ),

  aiAsk: (context: string, question: string) =>
    postJSON<AskResult>(`/api/ai/ask`, { context, question }),

  // 스트리밍 질의 — 토큰을 받는 대로 onChunk 로 흘리고, 백엔드명을 반환.
  aiAskStream: async (
    context: string,
    question: string,
    think: boolean,
    onChunk: (text: string) => void,
  ): Promise<string> => {
    const resp = await fetch(`/api/ai/ask/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ context, question, think }),
    });
    if (!resp.ok || !resp.body) throw new Error(`스트림 실패 (${resp.status})`);
    const backend = resp.headers.get("X-AI-Backend") ?? "ollama";
    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      onChunk(decoder.decode(value, { stream: true }));
    }
    return backend;
  },

  filings: (symbol: string, limit = 20) =>
    getJSON<DataEnvelope<FilingList>>(
      `/api/filings?symbol=${encodeURIComponent(symbol)}&limit=${limit}`,
    ),

  search: (q: string, limit = 8) =>
    getJSON<SymbolMatch[]>(`/api/search?q=${encodeURIComponent(q)}&limit=${limit}`),

  home: () => getJSON<HomeVerdict>(`/api/home`),

  context: (symbol: string) =>
    getJSON<DrawdownContext>(`/api/context/${encodeURIComponent(symbol)}`),

  fundamentals: (symbol: string) =>
    getJSON<Fundamentals>(`/api/fundamentals/${encodeURIComponent(symbol)}`),

  contexts: (symbols: string[]) =>
    getJSON<DrawdownContext[]>(
      `/api/context?symbols=${encodeURIComponent(symbols.join(","))}`,
    ),

  portfolio: () => getJSON<PortfolioSummary>(`/api/portfolio`),

  macroConditions: () => getJSON<MacroConditions>("/api/macro/conditions"),
  portfolioRisk: () => getJSON<PortfolioRisk>("/api/portfolio/risk"),
  valuation: (symbol: string) =>
    getJSON<ValuationContext>(`/api/valuation/${encodeURIComponent(symbol)}`),

  transactions: () => getJSON<Transaction[]>(`/api/portfolio/transactions`),

  addTransaction: (body: {
    type: "buy" | "sell";
    symbol: string;
    quantity: number;
    price: number;
    date: string | null;
  }) => postJSON<PortfolioSummary>(`/api/portfolio/transactions`, body),

  deleteTransaction: (id: string) =>
    delJSON<PortfolioSummary>(`/api/portfolio/transactions/${encodeURIComponent(id)}`),

  settings: () => getJSON<SafeSettings>(`/api/settings`),

  updateSettings: async (patch: SettingsPatch): Promise<SafeSettings> => {
    const resp = await fetch(`/api/settings`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    });
    if (!resp.ok) throw new Error(`설정 저장 실패 (${resp.status})`);
    return (await resp.json()) as SafeSettings;
  },
};
