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

  it("shows a friendly empty-portfolio guide for NO_DATA without a backend message (not a bug-sounding error)", () => {
    const empty: PortfolioRisk = {
      ...data,
      status: "NO_DATA",
      concentrationHhi: null,
      topSymbol: null,
      topWeight: null,
      weights: [],
      correlations: [],
      avgCorrelation: null,
      message: null,
    };
    render(<RiskPanel data={empty} mode="add" />);
    expect(screen.getByText(/보유 종목이 없어 아직 볼 게 없어요/)).toBeInTheDocument();
    expect(
      screen.getByText(/포트폴리오 탭에서 첫 거래를 기록하면/),
    ).toBeInTheDocument();
    expect(screen.queryByText("근거를 불러오지 못했습니다")).not.toBeInTheDocument();
  });

  it("keeps the generic failure message for a true ERROR status", () => {
    const errored: PortfolioRisk = {
      ...data,
      status: "ERROR",
      concentrationHhi: null,
      topSymbol: null,
      topWeight: null,
      weights: [],
      correlations: [],
      avgCorrelation: null,
      message: null,
    };
    render(<RiskPanel data={errored} mode="add" />);
    expect(screen.getByText("근거를 불러오지 못했습니다")).toBeInTheDocument();
  });

  it("attaches a glossary tooltip to 집중도(HHI)", () => {
    render(<RiskPanel data={data} mode="add" />);
    const el = screen.getByText(/집중도\(HHI\)/);
    expect(el.closest(".gloss")).not.toBeNull();
  });

  it("attaches a glossary tooltip to 평균 상관", () => {
    render(<RiskPanel data={data} mode="add" />);
    const el = screen.getByText(/평균 상관/);
    expect(el.closest(".gloss")).not.toBeNull();
  });
});
