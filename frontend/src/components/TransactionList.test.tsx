import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { TransactionList } from "./TransactionList";
import type { Transaction } from "../api/types";

vi.mock("../api/client", () => ({
  api: {
    deleteTransaction: vi.fn(),
  },
}));

function makeTxn(overrides: Partial<Transaction>): Transaction {
  return {
    id: overrides.id ?? "1",
    date: "2026-01-01",
    type: "buy",
    symbol: "AAPL",
    quantity: 1,
    price: 100,
    currency: "USD",
    ...overrides,
  };
}

describe("TransactionList", () => {
  it("shows the source label per transaction (토스/기초/수동)", () => {
    const transactions: Transaction[] = [
      makeTxn({ id: "1", symbol: "AAPL", source: "toss" }),
      makeTxn({ id: "2", symbol: "VOO", source: "toss-baseline" }),
      makeTxn({ id: "3", symbol: "QQQM", source: undefined }),
    ];
    render(<TransactionList transactions={transactions} onDeleted={vi.fn()} />);
    expect(screen.getByText("토스")).toBeInTheDocument();
    expect(screen.getByText("기초")).toBeInTheDocument();
    expect(screen.getByText("수동")).toBeInTheDocument();
  });
});
