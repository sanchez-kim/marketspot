import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ValuationPanel } from "./ValuationPanel";
import type { ValuationContext } from "../api/types";

const base: ValuationContext = {
  symbol: "AAPL",
  status: "DELAYED",
  asOf: "2026-06-18T00:00:00-04:00",
  peRatio: 36.12,
  pe5YAvg: null,
  peVs5YAvgPct: null,
  dividendYield: 0.36,
  week52High: 317.4,
  week52Low: 198.96,
  week52PositionPct: 83.6,
  price: 298.01,
  vsMa200Pct: 11.3,
  note: "5년 평균 PER 은 무료 데이터 한계로 제공하지 않습니다(현재 PER만).",
  message: null,
};

describe("ValuationPanel", () => {
  it("shows PER, 52w position, and overheating", () => {
    render(<ValuationPanel data={base} />);
    expect(screen.getByText(/36\.1/)).toBeInTheDocument(); // PER
    expect(screen.getByText(/83\.6/)).toBeInTheDocument(); // 52w position
    expect(screen.getByText(/11\.3/)).toBeInTheDocument(); // vs MA200
  });

  it("shows honest note that 5y PER is unavailable (no fabricated value)", () => {
    render(<ValuationPanel data={base} />);
    expect(screen.getByText(/5년 평균 PER/)).toBeInTheDocument();
    // pe5YAvg null → must NOT render a number for it
    expect(screen.queryByText(/5년 평균 PER 26/)).not.toBeInTheDocument();
  });

  it("renders status badge and handles null data", () => {
    const { rerender } = render(<ValuationPanel data={base} />);
    expect(screen.getByText("지연")).toBeInTheDocument(); // DataStatusBadge renders Korean label for DELAYED
    rerender(<ValuationPanel data={null} />);
    expect(
      screen.getByText(/근거를 불러오지 못했습니다|불러오는 중|—/),
    ).toBeInTheDocument();
  });
});
