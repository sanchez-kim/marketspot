import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DrawdownCard } from "./DrawdownCard";
import type { DrawdownContext } from "../api/types";

const base: DrawdownContext = {
  symbol: "VOO",
  status: "DELAYED",
  asOf: null,
  assetType: "ETF",
  currentPrice: 688.1,
  peakPrice: 699.15,
  peakDate: "2026-06-01",
  currentDrawdownPct: -1.5,
  historyYears: 14,
  thresholdPct: 10,
  comparableCount: 0,
  recoveredCount: 0,
  medianRecoveryDays: null,
  maxRecoveryDays: null,
  worstDrawdownPct: null,
  limitedHistory: false,
  note: null,
  message: null,
};

describe("DrawdownCard honesty", () => {
  it("shows the real drawdown when present", () => {
    render(<DrawdownCard ctx={base} />);
    expect(screen.getByText(/고점 대비 -1\.5%/)).toBeInTheDocument();
  });

  it("does NOT fabricate '고점 대비 0.0%' when drawdown is null under a live status", () => {
    render(<DrawdownCard ctx={{ ...base, currentDrawdownPct: null }} />);
    // null drawdown must not be coerced to a confident 0.0% fact
    expect(screen.queryByText(/고점 대비 0\.0%/)).not.toBeInTheDocument();
    expect(screen.getByText(/고점 대비 —/)).toBeInTheDocument();
  });
});
