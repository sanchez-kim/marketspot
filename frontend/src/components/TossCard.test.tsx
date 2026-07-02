import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { TossCard } from "./TossCard";
import { api } from "../api/client";
import { useUIStore } from "../store/uiStore";
import type { DataEnvelope, TossStatus, TossSyncResult } from "../api/types";

function renderCard(envelope: DataEnvelope<TossStatus>) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  qc.setQueryData(["toss-status"], envelope);
  return render(
    <QueryClientProvider client={qc}>
      <TossCard />
    </QueryClientProvider>,
  );
}

const needsKeyEnvelope: DataEnvelope<TossStatus> = {
  data: null,
  status: "NEEDS_KEY",
  source: "toss",
  asOf: null,
  delayMinutes: null,
  message: null,
};

function connectedEnvelope(overrides?: Partial<TossStatus>): DataEnvelope<TossStatus> {
  return {
    data: {
      connected: true,
      accounts: [
        {
          accountSeq: "1",
          accountNo: "1111-11",
          accountType: "종합",
          label: "종합 1111-11",
        },
        {
          accountSeq: "2",
          accountNo: "2222-22",
          accountType: "IRP",
          label: "IRP 2222-22",
        },
      ],
      selectedAccountSeq: "1",
      lastSync: "2026-07-01T09:00:00Z",
      ...overrides,
    },
    status: "LIVE",
    source: "toss",
    asOf: null,
    delayMinutes: null,
    message: null,
  };
}

describe("TossCard", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    useUIStore.setState({ settingsOpen: false });
  });

  it("shows guidance and an ⚙ 설정 button when not connected, which opens settings", () => {
    renderCard(needsKeyEnvelope);
    expect(screen.getByText(/자동으로 동기화돼요/)).toBeInTheDocument();
    const btn = screen.getByRole("button", { name: /설정/ });
    fireEvent.click(btn);
    expect(useUIStore.getState().settingsOpen).toBe(true);
  });

  it("shows the real backend message (not NEEDS_KEY guidance) when RATE_LIMITED", () => {
    const rateLimitedEnvelope: DataEnvelope<TossStatus> = {
      data: null,
      status: "RATE_LIMITED",
      source: "toss",
      asOf: null,
      delayMinutes: null,
      message: "토스 API 호출 제한에 도달했습니다. 잠시 후 다시 시도하세요.",
    };
    renderCard(rateLimitedEnvelope);
    expect(screen.getByText(/호출 제한/)).toBeInTheDocument();
    expect(screen.queryByText(/앱 키를 입력하세요/)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /설정/ })).not.toBeInTheDocument();
  });

  it("renders account select with options and lastSync when connected", () => {
    renderCard(connectedEnvelope());
    const select = screen.getByLabelText("계좌") as HTMLSelectElement;
    expect(select).toBeInTheDocument();
    expect(screen.getByText("종합 1111-11")).toBeInTheDocument();
    expect(screen.getByText("IRP 2222-22")).toBeInTheDocument();
    expect(screen.getByText(/2026-07-01T09:00:00Z/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /지금 동기화/ })).not.toBeDisabled();
  });

  it("calls api.tossSync on click and shows a message with the added count", async () => {
    const result: TossSyncResult = {
      mode: "incremental",
      added: 3,
      skippedUnpriced: 0,
      drift: [],
    };
    const spy = vi.spyOn(api, "tossSync").mockResolvedValue({
      data: result,
      status: "LIVE",
      source: "toss",
      asOf: null,
      delayMinutes: null,
      message: null,
    });
    renderCard(connectedEnvelope());
    fireEvent.click(screen.getByRole("button", { name: /지금 동기화/ }));
    await waitFor(() => expect(spy).toHaveBeenCalled());
    await waitFor(() => expect(screen.getByText(/거래 3건 추가/)).toBeInTheDocument());
  });

  it("shows an honest failure message when the sync request itself throws (no envelope)", async () => {
    vi.spyOn(api, "tossSync").mockRejectedValue(new Error("네트워크 오류"));
    renderCard(connectedEnvelope());
    fireEvent.click(screen.getByRole("button", { name: /지금 동기화/ }));
    await waitFor(() =>
      expect(screen.getByText(/동기화 요청에 실패했어요/)).toBeInTheDocument(),
    );
  });

  it("shows drift warnings visibly when the sync result includes them", async () => {
    const result: TossSyncResult = {
      mode: "incremental",
      added: 1,
      skippedUnpriced: 0,
      drift: [{ symbol: "AAPL", appQty: 5, tossQty: 7 }],
    };
    vi.spyOn(api, "tossSync").mockResolvedValue({
      data: result,
      status: "LIVE",
      source: "toss",
      asOf: null,
      delayMinutes: null,
      message: null,
    });
    renderCard(connectedEnvelope());
    fireEvent.click(screen.getByRole("button", { name: /지금 동기화/ }));
    await waitFor(() => expect(screen.getByText(/AAPL/)).toBeInTheDocument());
    expect(screen.getByText(/앱 5주/)).toBeInTheDocument();
    expect(screen.getByText(/토스 7주/)).toBeInTheDocument();
  });
});
