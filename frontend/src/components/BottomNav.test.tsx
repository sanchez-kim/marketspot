import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { BottomNav } from "./BottomNav";
import { useUIStore } from "../store/uiStore";

describe("BottomNav", () => {
  beforeEach(() => {
    useUIStore.setState({ activeTab: "home" });
  });

  it("renders the three tabs with labels", () => {
    render(<BottomNav />);
    expect(screen.getByText("홈")).toBeInTheDocument();
    expect(screen.getByText("살펴보기")).toBeInTheDocument();
    expect(screen.getByText("포트폴리오")).toBeInTheDocument();
  });

  it("marks the active tab", () => {
    useUIStore.setState({ activeTab: "portfolio" });
    const { container } = render(<BottomNav />);
    const active = container.querySelector(".bn-item.active");
    expect(active?.getAttribute("data-tab")).toBe("portfolio");
  });

  it("calls setTab when a tab is clicked", () => {
    render(<BottomNav />);
    fireEvent.click(screen.getByText("살펴보기"));
    expect(useUIStore.getState().activeTab).toBe("symbol");
  });
});
