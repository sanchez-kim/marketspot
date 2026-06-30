import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { DataEnvelope, Quote, StripItem } from "../api/types";
import { IndexStrip } from "./IndexStrip";

function makeStripItem(
  symbol: string,
  label: string,
  quoteOverrides: Partial<DataEnvelope<Quote>> = {},
): StripItem {
  return {
    symbol,
    label,
    quote: {
      data: {
        symbol,
        price: 5400.25,
        change: -12.5,
        changePct: -0.23,
        currency: "USD",
        name: null,
      },
      status: "LIVE",
      source: "yfinance",
      asOf: "2026-06-30T00:00:00Z",
      delayMinutes: null,
      message: null,
      ...quoteOverrides,
    },
  };
}

function renderWithStrip(items: StripItem[]) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  qc.setQueryData(["strip"], items);
  return render(
    <QueryClientProvider client={qc}>
      <IndexStrip />
    </QueryClientProvider>,
  );
}

describe("IndexStrip STALE quote rendering (§0 honesty)", () => {
  it("shows price AND the STALE badge together when status is STALE", () => {
    renderWithStrip([
      makeStripItem("SPY", "S&P 500", { status: "STALE", source: "yfinance" }),
    ]);
    // Price is rendered
    expect(screen.getByText(/5,400/)).toBeInTheDocument();
    // Badge is also rendered alongside the price
    expect(screen.getByText(/갱신지연/)).toBeInTheDocument();
  });

  it("shows only price (no badge) for a LIVE quote", () => {
    renderWithStrip([makeStripItem("SPY", "S&P 500", { status: "LIVE" })]);
    expect(screen.getByText(/5,400/)).toBeInTheDocument();
    expect(screen.queryByText(/갱신지연/)).not.toBeInTheDocument();
  });

  it("shows only badge (no price) when data is null (NO_DATA)", () => {
    renderWithStrip([
      makeStripItem("SPY", "S&P 500", { data: null, status: "NO_DATA" }),
    ]);
    expect(screen.queryByText(/5,400/)).not.toBeInTheDocument();
    expect(screen.getByText(/데이터 없음/)).toBeInTheDocument();
  });
});
