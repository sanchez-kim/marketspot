// frontend/src/components/Tour.test.tsx
import { act, render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Tour } from "./Tour";
import { useUIStore } from "../store/uiStore";

describe("Tour", () => {
  it("renders nothing when tour is closed", () => {
    act(() => useUIStore.setState({ tourOpen: false }));
    const { container } = render(<Tour onFinish={vi.fn()} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("steps through and finishes, calling onFinish + endTour", () => {
    const onFinish = vi.fn();
    act(() => useUIStore.setState({ tourOpen: true }));
    render(<Tour onFinish={onFinish} />);
    // first step title shows
    expect(screen.getByText("홈")).toBeInTheDocument();
    // click 다음 until 완료 (5 steps)
    for (let i = 0; i < 4; i++) {
      fireEvent.click(screen.getByRole("button", { name: /다음/ }));
    }
    fireEvent.click(screen.getByRole("button", { name: /완료/ }));
    expect(onFinish).toHaveBeenCalledOnce();
    expect(useUIStore.getState().tourOpen).toBe(false);
  });

  it("skip closes the tour", () => {
    const onFinish = vi.fn();
    act(() => useUIStore.setState({ tourOpen: true }));
    render(<Tour onFinish={onFinish} />);
    fireEvent.click(screen.getByRole("button", { name: /건너뛰기/ }));
    expect(useUIStore.getState().tourOpen).toBe(false);
  });
});
