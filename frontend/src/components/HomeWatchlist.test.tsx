import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { DataEnvelope, Quote } from "../api/types";
import { HomeWatchlist } from "./HomeWatchlist";

function makeQuoteEnv(overrides: Partial<DataEnvelope<Quote>>): DataEnvelope<Quote> {
  return {
    data: {
      symbol: "VOO",
      price: 688.1,
      change: -1.5,
      changePct: -0.22,
      currency: "USD",
      name: "Vanguard S&P 500 ETF",
    },
    status: "LIVE",
    source: "yfinance",
    asOf: "2026-06-30T00:00:00Z",
    delayMinutes: null,
    message: null,
    ...overrides,
  };
}

function renderWithQuotes(quotes: Record<string, DataEnvelope<Quote>>) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  qc.setQueryData(["settings"], {
    watchlist: Object.keys(quotes),
    defaultSymbol: "VOO",
  });
  qc.setQueryData(["quotes", Object.keys(quotes)], quotes);
  return render(
    <QueryClientProvider client={qc}>
      <HomeWatchlist />
    </QueryClientProvider>,
  );
}

describe("HomeWatchlist STALE quote rendering (§0 honesty)", () => {
  it("shows the STALE badge (갱신지연) when status is STALE", () => {
    renderWithQuotes({
      VOO: makeQuoteEnv({
        status: "STALE",
        asOf: "2026-06-30T00:00:00Z",
        source: "yfinance",
      }),
    });
    expect(screen.getByText(/갱신지연/)).toBeInTheDocument();
  });

  it("shows age text (약 N분 전) when status is STALE", () => {
    renderWithQuotes({
      VOO: makeQuoteEnv({
        status: "STALE",
        asOf: "2026-06-30T00:00:00Z",
        source: "yfinance",
      }),
    });
    expect(screen.getByText(/약 \d+분 전|약 \d+시간 전/)).toBeInTheDocument();
  });

  it("does NOT show a colored changePct span when STALE (no current-movement false signal)", () => {
    const { container } = renderWithQuotes({
      VOO: makeQuoteEnv({
        status: "STALE",
        asOf: "2026-06-30T00:00:00Z",
        source: "yfinance",
      }),
    });
    // The colored changePct spans carry "up"/"down"/"flat" class on a <span>
    const coloredSpans = container.querySelectorAll("span.up, span.down, span.flat");
    expect(coloredSpans.length).toBe(0);
  });

  it("shows colored changePct for a LIVE quote (baseline)", () => {
    const { container } = renderWithQuotes({
      VOO: makeQuoteEnv({ status: "LIVE" }),
    });
    const coloredSpans = container.querySelectorAll("span.up, span.down, span.flat");
    expect(coloredSpans.length).toBeGreaterThan(0);
  });
});
