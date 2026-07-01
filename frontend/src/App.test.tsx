import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, waitFor } from "@testing-library/react";
import { describe, expect, it, beforeEach, vi } from "vitest";
import App from "./App";
import { useUIStore } from "./store/uiStore";

// Stub heavy child components that fire their own queries / DOM side-effects
vi.mock("./components/IndexStrip", () => ({ IndexStrip: () => null }));
vi.mock("./components/HomeTab", () => ({ HomeTab: () => null }));
vi.mock("./components/SymbolTab", () => ({ SymbolTab: () => null }));
vi.mock("./components/PortfolioTab", () => ({ PortfolioTab: () => null }));
vi.mock("./components/AISidebar", () => ({ AISidebar: () => null }));
vi.mock("./components/Tour", () => ({
  Tour: ({ onFinish }: { onFinish: () => void }) => (
    <div data-testid="tour" onClick={onFinish} />
  ),
}));
vi.mock("./components/HelpPanel", () => ({ HelpPanel: () => null }));

function makeSettings(onboarded: boolean) {
  return {
    watchlist: ["VOO"],
    defaultSymbol: "VOO",
    ui: {
      theme: "dark",
      density: "comfortable",
      upColor: "green",
      defaultPeriod: "1Y",
      baseCurrency: "KRW",
      onboarded,
    },
    apiKeys: {},
    ai: { backend: "ollama", model: "llama3", beginnerMode: false },
    plan: {},
    dashboard: {},
  };
}

function renderApp(onboarded: boolean) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  qc.setQueryData(["settings"], makeSettings(onboarded));
  return render(
    <QueryClientProvider client={qc}>
      <App />
    </QueryClientProvider>,
  );
}

describe("App auto-tour", () => {
  beforeEach(() => useUIStore.setState({ tourOpen: false, helpOpen: false }));

  it("starts the tour when onboarded is false", async () => {
    renderApp(false);
    await waitFor(() => expect(useUIStore.getState().tourOpen).toBe(true));
  });

  it("does NOT start the tour when onboarded is true", async () => {
    renderApp(true);
    await new Promise((r) => setTimeout(r, 50));
    expect(useUIStore.getState().tourOpen).toBe(false);
  });
});
