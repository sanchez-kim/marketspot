import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { SettingsPanel } from "./SettingsPanel";
import { api } from "../api/client";
import { useUIStore } from "../store/uiStore";
import type { SafeSettings } from "../api/types";

function renderPanel(apiKeys: Record<string, boolean>) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  qc.setQueryData(["settings"], {
    apiKeys,
  } as unknown as SafeSettings);
  return render(
    <QueryClientProvider client={qc}>
      <SettingsPanel />
    </QueryClientProvider>,
  );
}

describe("SettingsPanel", () => {
  beforeEach(() => useUIStore.setState({ settingsOpen: true }));
  afterEach(() => {
    vi.restoreAllMocks();
    useUIStore.setState({ settingsOpen: false });
  });

  it("renders nothing when closed", () => {
    useUIStore.setState({ settingsOpen: false });
    const { container } = renderPanel({ fred: false, dart: false });
    expect(container).toBeEmptyDOMElement();
  });

  it("shows set/unset status per key", () => {
    renderPanel({ fred: false, dart: true });
    // FRED unset — scope to its own label so the (also-unset-by-default) Toss
    // field's "미설정" badge doesn't collide.
    expect(
      screen.getByLabelText("FRED 키").closest(".settings-field"),
    ).toHaveTextContent("미설정");
    expect(screen.getByText(/설정됨/)).toBeInTheDocument(); // DART set
  });

  it("saves a newly entered key via updateSettings (apiKeys patch)", async () => {
    const spy = vi.spyOn(api, "updateSettings").mockResolvedValue({
      apiKeys: { fred: true, dart: false },
    } as unknown as SafeSettings);
    renderPanel({ fred: false, dart: false });
    fireEvent.change(screen.getByLabelText("FRED 키"), {
      target: { value: "MY_FRED_KEY" },
    });
    act(() => {
      fireEvent.click(screen.getByRole("button", { name: /저장/ }));
    });
    await waitFor(() =>
      expect(spy).toHaveBeenCalledWith({ apiKeys: { fred: "MY_FRED_KEY" } }),
    );
  });

  it("renders Toss key inputs with status badge reflecting keys.toss", () => {
    renderPanel({ fred: false, dart: false, toss: true });
    expect(screen.getByLabelText("토스증권 앱 키")).toBeInTheDocument();
    expect(screen.getByLabelText("토스증권 시크릿")).toBeInTheDocument();
    expect(screen.getByText(/설정됨/)).toBeInTheDocument();
  });

  it("saves toss_app_key/toss_app_secret in the patch when filled", async () => {
    const spy = vi.spyOn(api, "updateSettings").mockResolvedValue({
      apiKeys: { fred: false, dart: false, toss: true },
    } as unknown as SafeSettings);
    renderPanel({ fred: false, dart: false, toss: false });
    fireEvent.change(screen.getByLabelText("토스증권 앱 키"), {
      target: { value: "MY_APP_KEY" },
    });
    fireEvent.change(screen.getByLabelText("토스증권 시크릿"), {
      target: { value: "MY_SECRET" },
    });
    act(() => {
      fireEvent.click(screen.getByRole("button", { name: /저장/ }));
    });
    await waitFor(() =>
      expect(spy).toHaveBeenCalledWith({
        apiKeys: { toss_app_key: "MY_APP_KEY", toss_app_secret: "MY_SECRET" },
      }),
    );
  });
});
