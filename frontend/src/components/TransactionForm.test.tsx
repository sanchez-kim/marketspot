import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { TransactionForm } from "./TransactionForm";
import { api } from "../api/client";

function renderForm(onAdded = vi.fn()) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <TransactionForm onAdded={onAdded} />
    </QueryClientProvider>,
  );
}

describe("TransactionForm", () => {
  afterEach(() => vi.restoreAllMocks());

  it("surfaces the server error on oversell instead of failing silently", async () => {
    vi.spyOn(api, "addTransaction").mockRejectedValue(
      new Error("보유 수량(5)을 초과해 매도할 수 없습니다"),
    );
    renderForm();
    // Fill quantity and price via aria-labels
    fireEvent.change(screen.getByLabelText(/수량/), { target: { value: "9" } });
    fireEvent.change(screen.getByLabelText(/가격/), { target: { value: "120" } });
    // The test seam: set symbol via data-testid hidden input (see TransactionForm.tsx)
    fireEvent.change(screen.getByTestId("txn-symbol"), { target: { value: "AAPL" } });
    // Click the submit button (unique data-testid to avoid matching toggle buttons)
    fireEvent.click(screen.getByTestId("txn-submit"));
    await waitFor(() =>
      expect(screen.getByText(/초과해 매도할 수 없습니다/)).toBeInTheDocument(),
    );
  });

  it("calls onAdded and resets the form on success", async () => {
    const mockSummary = {
      positions: [],
      totalValue: 0,
      totalCost: 0,
      totalPnl: 0,
      totalPnlPct: null,
      valuedCount: 0,
      unvaluedCount: 0,
      asOf: null,
      totalRealized: 0,
      valueKrw: null,
      valueUsd: null,
      unrealizedKrw: null,
      unrealizedUsd: null,
      realizedKrw: null,
      realizedUsd: null,
      fxRate: null,
      fxStatus: "NO_DATA" as const,
    };
    vi.spyOn(api, "addTransaction").mockResolvedValue(mockSummary);
    const onAdded = vi.fn();
    renderForm(onAdded);

    fireEvent.change(screen.getByLabelText(/수량/), { target: { value: "5" } });
    fireEvent.change(screen.getByLabelText(/가격/), { target: { value: "100" } });
    fireEvent.change(screen.getByTestId("txn-symbol"), { target: { value: "AAPL" } });
    fireEvent.click(screen.getByTestId("txn-submit"));

    await waitFor(() => expect(onAdded).toHaveBeenCalledWith(mockSummary));
    // Form should reset: quantity should be empty
    expect((screen.getByLabelText(/수량/) as HTMLInputElement).value).toBe("");
  });
});
