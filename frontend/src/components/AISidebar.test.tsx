import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { AISidebar } from "./AISidebar";
import { useUIStore } from "../store/uiStore";

function renderSidebar() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  qc.setQueryData(["context", "VOO"], null);
  return render(
    <QueryClientProvider client={qc}>
      <AISidebar />
    </QueryClientProvider>,
  );
}

describe("AISidebar explainer tone", () => {
  beforeEach(() => {
    useUIStore.setState({ aiOpen: true, aiMessages: [], symbol: "VOO" });
  });
  it("opens with an explainer intro (not a do-nothing reassurance)", () => {
    renderSidebar();
    // intro mentions explaining the evidence, not "그냥 두세요/안심"
    expect(screen.getAllByText(/근거|설명/).length).toBeGreaterThan(0);
    expect(screen.queryByText(/아무것도 하지|그냥 두세요/)).not.toBeInTheDocument();
  });
});
