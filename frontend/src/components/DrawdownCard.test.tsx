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

  it("attaches a glossary tooltip to the 회복 소요 label", () => {
    render(
      <DrawdownCard
        ctx={{
          ...base,
          comparableCount: 3,
          recoveredCount: 3,
          medianRecoveryDays: 60,
          maxRecoveryDays: 120,
          worstDrawdownPct: -25,
        }}
      />,
    );
    const el = screen.getByText(/회복 소요/);
    expect(el.closest(".gloss")).not.toBeNull();
  });

  it("does NOT fabricate '고점 대비 0.0%' when drawdown is null under a live status", () => {
    render(<DrawdownCard ctx={{ ...base, currentDrawdownPct: null }} />);
    // null drawdown must not be coerced to a confident 0.0% fact
    expect(screen.queryByText(/고점 대비 0\.0%/)).not.toBeInTheDocument();
    expect(screen.getByText(/고점 대비 —/)).toBeInTheDocument();
  });

  it("shows a visible '기저율' axis title so beginners can map this card to the 4-axis onboarding", () => {
    render(<DrawdownCard ctx={base} />);
    expect(screen.getByText("기저율")).toBeInTheDocument();
  });

  it("shows exactly one ⓘ glossary marker (no duplicate tooltip between axis title and ticker)", () => {
    render(<DrawdownCard ctx={base} />);
    expect(screen.getAllByText("ⓘ")).toHaveLength(1);
  });

  it("attaches the 기저율 glossary tooltip next to the axis title", () => {
    render(<DrawdownCard ctx={base} />);
    const titleEl = screen.getByText("기저율");
    const glossEl = titleEl.parentElement?.querySelector(".gloss");
    expect(glossEl).not.toBeNull();
    expect(glossEl).toHaveAttribute("title", expect.stringContaining("낙폭"));
  });
});
