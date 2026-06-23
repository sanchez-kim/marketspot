import { describe, expect, it } from "vitest";
import { buildEvidenceContext } from "./evidenceContext";
import type {
  DrawdownContext,
  MacroConditions,
  PortfolioRisk,
  ValuationContext,
} from "../api/types";

const valuation: ValuationContext = {
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
  note: null,
  message: null,
};

const drawdown: DrawdownContext = {
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
  comparableCount: 14,
  recoveredCount: 14,
  medianRecoveryDays: 90,
  maxRecoveryDays: 400,
  worstDrawdownPct: -34,
  limitedHistory: false,
  note: null,
  message: null,
};

const macro: MacroConditions = {
  rate: {
    label: "미 기준금리(실효)",
    value: 3.63,
    unit: "%",
    asOf: null,
    change: 0,
    status: "DELAYED",
    source: "fred",
    note: null,
  },
  cpi: {
    label: "CPI(전년 대비)",
    value: 4.2,
    unit: "%",
    asOf: null,
    change: null,
    status: "DELAYED",
    source: "fred",
    note: null,
  },
  indices: [],
  asOf: null,
};

const risk: PortfolioRisk = {
  status: "DELAYED",
  asOf: null,
  concentrationHhi: 0.41,
  topSymbol: "VOO",
  topWeight: 47.6,
  weights: [],
  correlations: [],
  avgCorrelation: 0.62,
  lookbackDays: 250,
  excluded: [],
  message: null,
};

describe("buildEvidenceContext", () => {
  it("grounds the AI with the symbol's real numbers", () => {
    const out = buildEvidenceContext("VOO", { valuation, drawdown, macro, risk });
    expect(out).toContain("VOO");
    expect(out).toContain("26.9"); // PER (rounded)
    expect(out).toContain("92.8"); // 52주 위치
    expect(out).toContain("-1.5"); // 고점 대비
    expect(out).toContain("3.63"); // 기준금리
    expect(out).toContain("0.41"); // HHI
    // honesty: no fabricated/empty values leak
    expect(out).not.toMatch(/null|undefined|NaN/);
  });

  it("omits missing data honestly instead of inventing numbers", () => {
    const noKeyMacro: MacroConditions = {
      ...macro,
      rate: { ...macro.rate, value: null, status: "NEEDS_KEY" },
      cpi: { ...macro.cpi, value: null, status: "NEEDS_KEY" },
    };
    const out = buildEvidenceContext("VOO", {
      valuation: null,
      drawdown: null,
      macro: noKeyMacro,
      risk: null,
    });
    expect(out).not.toMatch(/null|undefined|NaN/);
    expect(out).not.toContain("PER");
    expect(out).not.toContain("기준금리 ");
  });

  it("returns an empty string when there is no usable evidence", () => {
    const out = buildEvidenceContext("VOO", {});
    expect(out).toBe("");
  });
});
