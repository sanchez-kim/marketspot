import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RiskPanel } from "./RiskPanel";
import type { PortfolioRisk } from "../api/types";

const data: PortfolioRisk = {
  status: "DELAYED",
  asOf: "2026-06-21T02:41:21Z",
  concentrationHhi: 0.4144,
  topSymbol: "VOO",
  topWeight: 47.58,
  weights: [
    { symbol: "VOO", weight: 47.58 },
    { symbol: "QQQM", weight: 42.11 },
    { symbol: "AAPL", weight: 10.3 },
  ],
  correlations: [{ a: "VOO", b: "QQQM", corr: 0.94 }],
  avgCorrelation: 0.62,
  lookbackDays: 251,
  excluded: [],
  message: null,
};

describe("RiskPanel", () => {
  it("shows concentration and average correlation", () => {
    render(<RiskPanel data={data} mode="add" />);
    expect(screen.getByText(/VOO/)).toBeInTheDocument();
    expect(screen.getByText(/47\.6|47\.58/)).toBeInTheDocument(); // top weight
    expect(screen.getByText(/0\.62/)).toBeInTheDocument(); // avg correlation
  });

  it("changes emphasis text by reviewMode", () => {
    const { rerender } = render(<RiskPanel data={data} mode="add" />);
    expect(screen.getByText(/추가 시/)).toBeInTheDocument();
    rerender(<RiskPanel data={data} mode="hold" />);
    expect(screen.getByText(/현재 비중|보유/)).toBeInTheDocument();
    rerender(<RiskPanel data={data} mode="new" />);
    expect(screen.getByText(/기존 보유와의/)).toBeInTheDocument();
  });

  it("shows NO_DATA message when empty (no fabricated numbers)", () => {
    const empty: PortfolioRisk = {
      ...data,
      status: "NO_DATA",
      concentrationHhi: null,
      topSymbol: null,
      topWeight: null,
      weights: [],
      correlations: [],
      avgCorrelation: null,
      message: "평가 가능한 보유 포지션이 없습니다",
    };
    render(<RiskPanel data={empty} mode="add" />);
    expect(screen.getByText(/보유 포지션이 없습니다/)).toBeInTheDocument();
  });
});
