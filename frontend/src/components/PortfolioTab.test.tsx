import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PortfolioTab } from "./PortfolioTab";
import type { PortfolioSummary } from "../api/types";

function makeSummary(): PortfolioSummary {
  return {
    positions: [
      {
        symbol: "VOO",
        quantity: 6,
        avgCost: 500,
        costBasis: 3000,
        name: null,
        currency: "USD",
        price: 680,
        marketValue: 4080,
        unrealizedPnl: 1080,
        unrealizedPnlPct: 36,
        realizedPnl: 800,
        weight: 100,
        status: "DELAYED",
      },
    ],
    totalValue: 4080,
    totalCost: 3000,
    totalPnl: 1080,
    totalPnlPct: 36,
    totalRealized: 800,
    valuedCount: 1,
    unvaluedCount: 0,
    asOf: null,
    valueUsd: 4080,
    valueKrw: null,
    unrealizedUsd: 1080,
    unrealizedKrw: null,
    realizedUsd: 800,
    realizedKrw: null,
    fxRate: null,
    fxStatus: "NO_DATA",
  };
}

function renderTab() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  qc.setQueryData(["portfolio"], makeSummary());
  qc.setQueryData(["transactions"], []);
  return render(
    <QueryClientProvider client={qc}>
      <PortfolioTab />
    </QueryClientProvider>,
  );
}

function makeEmptySummary(): PortfolioSummary {
  return {
    positions: [],
    totalValue: 0,
    totalCost: 0,
    totalPnl: 0,
    totalPnlPct: 0,
    totalRealized: 0,
    valuedCount: 0,
    unvaluedCount: 0,
    asOf: null,
    valueUsd: 0,
    valueKrw: null,
    unrealizedUsd: 0,
    unrealizedKrw: null,
    realizedUsd: 0,
    realizedKrw: null,
    fxRate: null,
    fxStatus: "NO_DATA",
  };
}

function renderEmptyTab() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  qc.setQueryData(["portfolio"], makeEmptySummary());
  qc.setQueryData(["transactions"], []);
  return render(
    <QueryClientProvider client={qc}>
      <PortfolioTab />
    </QueryClientProvider>,
  );
}

describe("PortfolioTab", () => {
  it("renders the position with its realized P&L", () => {
    renderTab();
    // 파생된 포지션 표가 종목과 실현손익을 보여준다.
    expect(screen.getAllByText(/VOO/).length).toBeGreaterThan(0);
    // 실현손익 컬럼: 표 셀은 부호 포함 "+800.00" 으로 포맷된다.
    expect(screen.getByText("+800.00")).toBeInTheDocument();
  });

  it("shows the currency indicator for the position", () => {
    renderTab();
    // 통화 표기(USD) — 종목 옆 배지 또는 통화 열.
    expect(screen.getAllByText(/USD/).length).toBeGreaterThan(0);
  });

  it("renders the transaction form and an empty transaction list", () => {
    renderTab();
    // 거래 폼(매수/매도) + 빈 내역 메시지.
    expect(screen.getByText("매수")).toBeInTheDocument();
    expect(screen.getByText("매도")).toBeInTheDocument();
    expect(screen.getByText(/거래내역이 없습니다/)).toBeInTheDocument();
  });

  it("guides the user to add a first transaction when empty", () => {
    renderEmptyTab();
    // 포지션도 거래도 없을 때 행동 유도 문구가 나타나야 한다.
    // "첫 거래를 기록" is only in the empty-state guidance text, not the form.
    expect(screen.getByText(/첫 거래를 기록/)).toBeInTheDocument();
  });
});
