import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MacroPanel } from "./MacroPanel";
import type { MacroConditions } from "../api/types";

const data: MacroConditions = {
  rate: {
    label: "미 기준금리(실효)",
    value: 3.63,
    unit: "%",
    asOf: "2026-06-17",
    change: 0,
    status: "DELAYED",
    source: "fred",
    note: null,
  },
  cpi: {
    label: "CPI(전년 대비)",
    value: 4.2,
    unit: "%",
    asOf: "2026-05-01",
    change: null,
    status: "DELAYED",
    source: "fred",
    note: null,
  },
  indices: [
    {
      label: "S&P 500",
      symbol: "^GSPC",
      price: 7500.58,
      vsMa50Pct: 2.5,
      vsMa200Pct: 8.7,
      status: "DELAYED",
    },
  ],
  asOf: "2026-06-21T02:40:43Z",
};

describe("MacroPanel", () => {
  it("shows rate, CPI YoY, and index trend", () => {
    render(<MacroPanel data={data} />);
    expect(screen.getByText(/3\.63/)).toBeInTheDocument();
    expect(screen.getByText(/4\.2/)).toBeInTheDocument();
    expect(screen.getByText(/S&P 500/)).toBeInTheDocument();
    expect(screen.getByText(/8\.7/)).toBeInTheDocument(); // vs MA200
  });

  it("surfaces a per-metric honesty note when the backend sets one", () => {
    const withNote: MacroConditions = {
      ...data,
      cpi: { ...data.cpi, note: "전년 동월 데이터가 부족합니다" },
    };
    render(<MacroPanel data={withNote} />);
    expect(screen.getByText("전년 동월 데이터가 부족합니다")).toBeInTheDocument();
  });

  it("shows an honest badge for an index whose data is missing (not a silent —)", () => {
    const badIndex: MacroConditions = {
      ...data,
      indices: [
        {
          label: "S&P 500",
          symbol: "^GSPC",
          price: null,
          vsMa50Pct: null,
          vsMa200Pct: null,
          status: "NEEDS_KEY",
        },
      ],
    };
    render(<MacroPanel data={badIndex} />);
    // the index row must surface its status, not render a bare "—" with no explanation
    expect(screen.getAllByText("API 키 필요").length).toBeGreaterThan(0);
  });

  it("attaches a glossary tooltip to the rate label", () => {
    render(<MacroPanel data={data} />);
    const el = screen.getByText(/미 기준금리/);
    expect(el.closest(".gloss")).not.toBeNull();
  });

  it("attaches a glossary tooltip to the CPI label", () => {
    render(<MacroPanel data={data} />);
    const el = screen.getByText(/CPI/);
    expect(el.closest(".gloss")).not.toBeNull();
  });

  it("shows NEEDS_KEY honestly when CPI value is null with that status", () => {
    const noKey: MacroConditions = {
      ...data,
      cpi: { ...data.cpi, value: null, status: "NEEDS_KEY", note: null },
    };
    render(<MacroPanel data={noKey} />);
    expect(screen.getAllByText("API 키 필요").length).toBeGreaterThan(0); // DataStatusBadge label for NEEDS_KEY
    // null value → must not fabricate a CPI number
    expect(screen.queryByText(/CPI.*4\.2/)).not.toBeInTheDocument();
  });
});
