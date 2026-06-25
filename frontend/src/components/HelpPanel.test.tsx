import { act, render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { HelpPanel } from "./HelpPanel";
import { useUIStore } from "../store/uiStore";

describe("HelpPanel", () => {
  it("renders nothing when closed", () => {
    act(() => useUIStore.setState({ helpOpen: false }));
    const { container } = render(<HelpPanel />);
    expect(container).toBeEmptyDOMElement();
  });
  it("shows app intro + tab guide and can restart the tour", () => {
    act(() => useUIStore.setState({ helpOpen: true, tourOpen: false }));
    render(<HelpPanel />);
    expect(screen.getByText(/근거를 차려주는/)).toBeInTheDocument();
    expect(screen.getByText("살펴보기")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /투어 다시 보기/ }));
    expect(useUIStore.getState().helpOpen).toBe(false);
    expect(useUIStore.getState().tourOpen).toBe(true);
  });
});
