import { describe, expect, it } from "vitest";
import { useUIStore } from "./uiStore";

describe("uiStore initial state", () => {
  it("defaults baseCurrency to KRW for Korean users", () => {
    const state = useUIStore.getState();
    expect(state.baseCurrency).toBe("KRW");
  });
});

describe("uiStore onboarding state", () => {
  it("toggles help and tour open state", () => {
    useUIStore.getState().startTour();
    expect(useUIStore.getState().tourOpen).toBe(true);
    useUIStore.getState().endTour();
    expect(useUIStore.getState().tourOpen).toBe(false);
    useUIStore.getState().openHelp();
    expect(useUIStore.getState().helpOpen).toBe(true);
    useUIStore.getState().closeHelp();
    expect(useUIStore.getState().helpOpen).toBe(false);
  });
});
