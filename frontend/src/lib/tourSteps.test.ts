// frontend/src/lib/tourSteps.test.ts
import { describe, expect, it } from "vitest";
import { TOUR_STEPS } from "./tourSteps";
import { APP_INTRO, TAB_GUIDE, AXIS_GUIDE } from "./helpContent";

const FORBIDDEN = ["오른다", "사라", "팔아라"];

describe("tour + help content", () => {
  it("has 6 tour steps each with id/title/body", () => {
    expect(TOUR_STEPS.length).toBe(6);
    for (const s of TOUR_STEPS) {
      expect(s.id && s.title && s.body).toBeTruthy();
    }
  });
  it("help content covers 3 tabs and 4 axes", () => {
    expect(APP_INTRO.length).toBeGreaterThan(10);
    expect(TAB_GUIDE.length).toBe(3);
    expect(AXIS_GUIDE.length).toBe(4);
  });
  it("contains no prediction / buy-sell language", () => {
    const all = [
      APP_INTRO,
      ...TOUR_STEPS.flatMap((s) => [s.title, s.body]),
      ...TAB_GUIDE.map((t) => t.text),
      ...AXIS_GUIDE.map((a) => a.text),
    ].join(" ");
    for (const bad of FORBIDDEN) expect(all).not.toContain(bad);
  });
  it("AI step mentions Ollama running requirement", () => {
    const aiStep = TOUR_STEPS.find((s) => s.id === "ai");
    expect(aiStep?.body).toContain("로컬 AI(Ollama)가 켜져 있으면");
  });
});
