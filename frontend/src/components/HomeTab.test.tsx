import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { HomeTab } from "./HomeTab";

function renderHome() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  qc.setQueryData(["settings"], {
    watchlist: ["VOO"],
    defaultSymbol: "VOO",
    dashboard: { left: [], right: [], hidden: [] },
  });
  qc.setQueryData(["portfolio"], {
    positions: [],
    totalValue: 0,
    totalCost: 0,
    totalPnl: 0,
    totalPnlPct: null,
    valuedCount: 0,
    unvaluedCount: 0,
    asOf: null,
  });
  return render(
    <QueryClientProvider client={qc}>
      <HomeTab />
    </QueryClientProvider>,
  );
}

describe("HomeTab cockpit (verdict removed)", () => {
  it("does NOT render a verdict headline/todo banner", () => {
    renderHome();
    expect(screen.queryByText(/지금 할 일|계획대로 계속/)).not.toBeInTheDocument();
  });
  it("does NOT render the 투자원칙 card", () => {
    renderHome();
    expect(screen.queryByText("투자원칙")).not.toBeInTheDocument();
  });
});
