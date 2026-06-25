import { renderHook, act } from "@testing-library/react";
import { describe, it, expect, beforeEach } from "vitest";
import { useAutoTour } from "./useAutoTour";
import { useUIStore } from "../store/uiStore";

describe("useAutoTour", () => {
  beforeEach(() => {
    useUIStore.setState({ tourOpen: false });
  });

  it("starts the tour when onboarded is false", () => {
    renderHook(() => useAutoTour(false));
    expect(useUIStore.getState().tourOpen).toBe(true);
  });

  it("does NOT start the tour when onboarded is true", async () => {
    renderHook(() => useAutoTour(true));
    await act(async () => {});
    expect(useUIStore.getState().tourOpen).toBe(false);
  });

  it("does NOT start the tour when onboarded is undefined (loading)", async () => {
    renderHook(() => useAutoTour(undefined));
    await act(async () => {});
    expect(useUIStore.getState().tourOpen).toBe(false);
  });

  it("does not re-fire on re-render when already triggered", () => {
    const { rerender } = renderHook(({ v }) => useAutoTour(v), {
      initialProps: { v: false as boolean | undefined },
    });
    expect(useUIStore.getState().tourOpen).toBe(true);

    // Manually close tour, then re-render — should NOT re-open
    act(() => useUIStore.setState({ tourOpen: false }));
    rerender({ v: false });
    expect(useUIStore.getState().tourOpen).toBe(false);
  });
});
