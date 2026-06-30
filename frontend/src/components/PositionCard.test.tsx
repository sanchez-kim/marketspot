import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { PositionCard } from "./PositionCard";
import type { PositionValuation } from "../api/types";

const base: PositionValuation = {
  symbol: "VOO",
  currency: "USD",
  quantity: 10,
  avgCost: 500,
  costBasis: 5000,
  name: "Vanguard S&P 500 ETF",
  price: 560,
  marketValue: 5600,
  unrealizedPnl: 600,
  unrealizedPnlPct: 12,
  realizedPnl: 0,
  weight: 40,
  status: "DELAYED",
};

describe("PositionCard", () => {
  it("shows symbol and key labelled values", () => {
    render(<PositionCard p={base} onOpen={() => {}} />);
    expect(screen.getByText("VOO")).toBeInTheDocument();
    expect(screen.getByText("평가액")).toBeInTheDocument();
    expect(screen.getByText("미실현손익")).toBeInTheDocument();
    expect(screen.getByText("비중")).toBeInTheDocument();
  });

  it("renders an honest '—' (not a fabricated 0) when a value is null", () => {
    const noVal: PositionValuation = {
      ...base,
      price: null,
      marketValue: null,
      unrealizedPnl: null,
      unrealizedPnlPct: null,
      weight: null,
      status: "NO_DATA",
    };
    const { container } = render(<PositionCard p={noVal} onOpen={() => {}} />);
    // 미실현손익이 0.00 으로 지어내지지 않고 — 로 표기되어야 한다(§0 정직성).
    expect(container.textContent).toContain("—");
    expect(container.textContent).not.toContain("+0.00");
  });

  it("calls onOpen with the symbol when the title is clicked", () => {
    const onOpen = vi.fn();
    render(<PositionCard p={base} onOpen={onOpen} />);
    fireEvent.click(screen.getByText("VOO"));
    expect(onOpen).toHaveBeenCalledWith("VOO");
  });
});
