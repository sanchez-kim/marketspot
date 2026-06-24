import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import type { PortfolioSummary } from "../api/types";
import { useUIStore } from "../store/uiStore";
import { PortfolioSummaryCard } from "./PortfolioSummaryCard";

// ── helpers ────────────────────────────────────────────────────────────────

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

// Reset zustand to default state between tests so currency toggle doesn't bleed.
afterEach(() => {
  useUIStore.setState({ baseCurrency: "USD" });
});

// Minimal PortfolioSummary with both KRW and USD currency fields.
const baseSummary: PortfolioSummary = {
  positions: [
    {
      symbol: "VOO",
      quantity: 1,
      avgCost: 400,
      costBasis: 400,
      name: "Vanguard S&P 500 ETF",
      currency: "USD",
      price: 500,
      marketValue: 500,
      unrealizedPnl: 100,
      unrealizedPnlPct: 25,
      weight: 100,
      realizedPnl: 50,
      status: "LIVE",
    },
  ],
  totalValue: 500,
  totalCost: 400,
  totalPnl: 100,
  totalPnlPct: 25,
  valuedCount: 1,
  unvaluedCount: 0,
  asOf: "2026-06-24T00:00:00Z",
  totalRealized: 50,
  valueKrw: 680000,
  valueUsd: 500,
  unrealizedKrw: 136000,
  unrealizedUsd: 100,
  realizedKrw: 68000,
  realizedUsd: 50,
  fxRate: 1360,
  fxStatus: "LIVE",
};

// ── tests ──────────────────────────────────────────────────────────────────

describe("PortfolioSummaryCard — prop-driven", () => {
  it("renders without error when given a summary with positions", () => {
    wrap(<PortfolioSummaryCard summary={baseSummary} />);
    expect(screen.getByText("내 포트폴리오")).toBeInTheDocument();
  });

  it("returns null when positions array is empty", () => {
    const { container } = wrap(
      <PortfolioSummaryCard summary={{ ...baseSummary, positions: [] }} />,
    );
    expect(container.firstChild).toBeNull();
  });
});

describe("PortfolioSummaryCard — USD mode", () => {
  it("shows USD totals (valueUsd, unrealizedUsd, realizedUsd) with $ symbol", () => {
    useUIStore.setState({ baseCurrency: "USD" });
    wrap(<PortfolioSummaryCard summary={baseSummary} />);

    // USD value: $500 — use exact text match on the <b> element
    expect(screen.getByText("$500")).toBeInTheDocument();
    // USD unrealized P&L: $100
    expect(screen.getByText(/\$100/)).toBeInTheDocument();
    // USD realized P&L: $50 — exact match to avoid matching $500
    expect(screen.getByText("$50")).toBeInTheDocument();
  });
});

describe("PortfolioSummaryCard — KRW mode", () => {
  it("shows KRW totals (valueKrw, unrealizedKrw, realizedKrw) with ₩ symbol when baseCurrency=KRW", () => {
    useUIStore.setState({ baseCurrency: "KRW" });
    wrap(<PortfolioSummaryCard summary={baseSummary} />);

    // Multiple ₩ values are expected (평가액, 평가손익, 실현손익)
    const krwElements = screen.getAllByText(/₩/);
    expect(krwElements.length).toBeGreaterThan(0);
  });
});

describe("PortfolioSummaryCard — fx unavailable", () => {
  it("shows '—' and a DataStatusBadge when chosen-currency value is null (fx unavailable)", () => {
    useUIStore.setState({ baseCurrency: "KRW" });
    const noFxSummary: PortfolioSummary = {
      ...baseSummary,
      valueKrw: null,
      unrealizedKrw: null,
      realizedKrw: null,
      fxStatus: "ERROR",
    };
    wrap(<PortfolioSummaryCard summary={noFxSummary} />);

    // At least one '—' must appear for the null KRW value(s)
    const dashes = screen.getAllByText("—");
    expect(dashes.length).toBeGreaterThan(0);

    // Multiple fx error badges are shown (one per null KPI) — check at least one
    const badges = screen.getAllByText("오류");
    expect(badges.length).toBeGreaterThan(0);
  });
});
