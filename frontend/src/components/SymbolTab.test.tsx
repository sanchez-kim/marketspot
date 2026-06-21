import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SymbolTab } from "./SymbolTab";
import type { ValuationContext } from "../api/types";

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
});
