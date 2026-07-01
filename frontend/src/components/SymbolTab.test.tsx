import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useIsMobile } from "../hooks/useIsMobile";
import { SymbolTab } from "./SymbolTab";
import type { DataEnvelope, Quote, ValuationContext } from "../api/types";

vi.mock("../hooks/useIsMobile");

// Default all existing tests to desktop so matchMedia absence in jsdom is not an issue.
beforeEach(() => {
  vi.mocked(useIsMobile).mockReturnValue(false);
});

function renderWithEmptyWatchlist() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  qc.setQueryData(["settings"], { watchlist: [], defaultSymbol: "VOO" });
  return render(
    <QueryClientProvider client={qc}>
      <SymbolTab />
    </QueryClientProvider>,
  );
}

function renderWithCache() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const val: ValuationContext = {
    symbol: "VOO",
    status: "DELAYED",
    asOf: null,
    peRatio: 26.85,
    pe5YAvg: null,
    peVs5YAvgPct: null,
    dividendYield: 1.03,
    week52High: 699.15,
    week52Low: 545.75,
    week52PositionPct: 92.8,
    price: 688.1,
    vsMa200Pct: 9.1,
    note: "현재 PER만",
    message: null,
  };
  qc.setQueryData(["valuation", "VOO"], val);
  qc.setQueryData(["settings"], { watchlist: ["VOO"], defaultSymbol: "VOO" });
  return render(
    <QueryClientProvider client={qc}>
      <SymbolTab />
    </QueryClientProvider>,
  );
}

function renderWithStaleQuote(mobile: boolean) {
  vi.mocked(useIsMobile).mockReturnValue(mobile);
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const staleEnv: DataEnvelope<Quote> = {
    data: {
      symbol: "VOO",
      price: 688.1,
      change: -1.5,
      changePct: -0.22,
      currency: "USD",
      name: null,
    },
    status: "STALE",
    source: "yfinance",
    asOf: "2026-06-30T00:00:00Z",
    delayMinutes: null,
    message: null,
  };
  qc.setQueryData(["settings"], { watchlist: ["VOO"], defaultSymbol: "VOO" });
  qc.setQueryData(["quotes", ["VOO"]], { VOO: staleEnv });
  return render(
    <QueryClientProvider client={qc}>
      <SymbolTab />
    </QueryClientProvider>,
  );
}

describe("SymbolTab as Decision Briefing", () => {
  it("renders the four evidence axes and the honesty footer", () => {
    renderWithCache();
    expect(screen.getByText("밸류·과열도")).toBeInTheDocument();
    expect(screen.getByText("포트폴리오 영향")).toBeInTheDocument();
    expect(screen.getByText("거시 환경")).toBeInTheDocument();
    expect(screen.getByText(/판단은 당신/)).toBeInTheDocument(); // honesty footer
  });

  it("has the review-mode toggle and AI-explain action", () => {
    renderWithCache();
    expect(screen.getByText(/추가매수/)).toBeInTheDocument();
    expect(screen.getByText(/설명 요청|AI/)).toBeInTheDocument();
  });

  it("labels the review-mode toggle with an info hint explaining what it changes", () => {
    renderWithCache();
    const label = screen.getByText("관점");
    expect(label).toBeInTheDocument();
    expect(label.className).toContain("review-label");
    const hint = label.querySelector(".gloss");
    expect(hint).toHaveAttribute("title", expect.stringContaining("포트폴리오 영향"));
    expect(hint?.textContent).toContain("ⓘ");
  });
});

describe("SymbolTab watchlist rail empty state", () => {
  it("shows search guidance when watchlist is empty", () => {
    renderWithEmptyWatchlist();
    expect(screen.getByText(/검색으로 종목을 추가/)).toBeInTheDocument();
  });

  it("shows search guidance on mobile when watchlist is empty", () => {
    vi.mocked(useIsMobile).mockReturnValue(true);
    renderWithEmptyWatchlist();
    expect(screen.getByText(/검색으로 종목을 추가/)).toBeInTheDocument();
  });
});

describe("SymbolTab responsive watchlist", () => {
  it("renders a horizontal chip strip on phone (not the vertical rail)", () => {
    vi.mocked(useIsMobile).mockReturnValue(true);
    const { container } = renderWithCache();
    expect(container.querySelector(".rail-chips")).not.toBeNull();
    expect(container.querySelector(".symbol-rail")).toBeNull();
  });

  it("renders the vertical rail on desktop", () => {
    vi.mocked(useIsMobile).mockReturnValue(false);
    const { container } = renderWithCache();
    expect(container.querySelector(".symbol-rail")).not.toBeNull();
    expect(container.querySelector(".rail-chips")).toBeNull();
  });
});

describe("SymbolTab STALE quote rendering (§0 honesty)", () => {
  it("desktop rail: shows STALE badge and no colored changePct for a STALE quote", () => {
    const { container } = renderWithStaleQuote(false);
    // 레일 + 헤더 두 곳에 정직하게 STALE 뱃지가 뜬다(둘 다 실시간처럼 보이면 안 됨).
    expect(screen.getAllByText(/갱신지연/).length).toBeGreaterThan(0);
    const coloredSpans = container.querySelectorAll("span.up, span.down, span.flat");
    expect(coloredSpans.length).toBe(0);
    // "지연"과 구별되도록 나이("약 N분/시간 전")도 뱃지 옆에 뜬다.
    const railRow = container.querySelector(".rail-row");
    expect(railRow).not.toBeNull();
    expect(railRow!.textContent).toMatch(/분 전|시간 전/);
  });

  it("mobile chip: shows STALE badge and no colored changePct for a STALE quote", () => {
    const { container } = renderWithStaleQuote(true);
    expect(screen.getAllByText(/갱신지연/).length).toBeGreaterThan(0);
    const coloredSpans = container.querySelectorAll("span.up, span.down, span.flat");
    expect(coloredSpans.length).toBe(0);
    const chip = container.querySelector(".wl-chip");
    expect(chip).not.toBeNull();
    expect(chip!.textContent).toMatch(/분 전|시간 전/);
  });
});

describe("SymbolTab header price line (#1 timing legibility, §0 honesty)", () => {
  it("shows the current symbol's price + STALE badge/age (not a colored %) in the detail head", () => {
    const { container } = renderWithStaleQuote(false);
    const head = container.querySelector(".symbol-detail-head");
    expect(head).not.toBeNull();
    const priceEl = head!.querySelector(".sym-price");
    expect(priceEl).not.toBeNull();
    expect(priceEl!.textContent).toContain("688.10");
    expect(priceEl!.querySelector(".status-badge")).not.toBeNull();
    expect(priceEl!.textContent).toMatch(/분 전|시간 전/);
    expect(priceEl!.querySelector("span.up, span.down, span.flat")).toBeNull();
  });

  it("renders nothing in the price line when the current symbol has no quote (not in watchlist)", () => {
    const { container } = renderWithEmptyWatchlist();
    const head = container.querySelector(".symbol-detail-head");
    expect(head).not.toBeNull();
    expect(head!.querySelector(".sym-price")).toBeNull();
  });
});
