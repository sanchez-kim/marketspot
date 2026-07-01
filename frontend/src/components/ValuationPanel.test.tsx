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

  it("attaches a glossary tooltip to 52주 밴드 내 위치", () => {
    render(<ValuationPanel data={base} />);
    const el = screen.getByText(/52주 밴드 내 위치/);
    expect(el.closest(".gloss")).not.toBeNull();
  });

  it("attaches a glossary tooltip to 200일선 대비", () => {
    render(<ValuationPanel data={base} />);
    const el = screen.getByText(/200일선 대비/);
    expect(el.closest(".gloss")).not.toBeNull();
  });

  it("renders status badge and handles null data", () => {
    const { rerender } = render(<ValuationPanel data={base} />);
    expect(screen.getByText("지연")).toBeInTheDocument(); // DataStatusBadge renders Korean label for DELAYED
    rerender(<ValuationPanel data={null} />);
    expect(
      screen.getByText(/근거를 불러오지 못했습니다|불러오는 중|—/),
    ).toBeInTheDocument();
  });

  it("shows a friendly '아직 볼 게 없어요' message for NO_DATA without a backend message (not a bug-sounding error)", () => {
    render(<ValuationPanel data={{ ...base, status: "NO_DATA", message: null }} />);
    expect(screen.getByText(/아직 볼 게 없어요/)).toBeInTheDocument();
    expect(screen.queryByText("근거를 불러오지 못했습니다")).not.toBeInTheDocument();
  });

  it("keeps the generic failure message for a true ERROR status", () => {
    render(<ValuationPanel data={{ ...base, status: "ERROR", message: null }} />);
    expect(screen.getByText("근거를 불러오지 못했습니다")).toBeInTheDocument();
  });

  it("prefers the backend's honest message when present, even for NO_DATA", () => {
    render(
      <ValuationPanel
        data={{ ...base, status: "NO_DATA", message: "심볼을 찾을 수 없습니다" }}
      />,
    );
    expect(screen.getByText("심볼을 찾을 수 없습니다")).toBeInTheDocument();
    expect(screen.queryByText(/아직 볼 게 없어요/)).not.toBeInTheDocument();
  });
});
