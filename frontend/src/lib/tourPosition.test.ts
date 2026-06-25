import { describe, expect, it } from "vitest";
import { placeBubble } from "./tourPosition";

const VW = 1440;
const VH = 813;
const BW = 360;
const BH = 200;

function fullyOnScreen(top: number, left: number) {
  return top >= 0 && left >= 0 && top + BH <= VH && left + BW <= VW;
}

describe("placeBubble", () => {
  it("places the bubble below a small top-anchored target, on screen", () => {
    const { top, left } = placeBubble(
      { top: 60, bottom: 100, left: 40, width: 300 },
      BW,
      BH,
      VW,
      VH,
    );
    expect(top).toBe(112); // bottom + 12
    expect(fullyOnScreen(top, left)).toBe(true);
  });

  it("keeps the bubble on screen for a tall target that reaches past the viewport (the disappearing bug)", () => {
    // home-grid style: spans almost the whole page, bottom well below the fold
    const { top, left } = placeBubble(
      { top: 120, bottom: 1140, left: 200, width: 700 },
      BW,
      BH,
      VW,
      VH,
    );
    expect(fullyOnScreen(top, left)).toBe(true); // must NOT land at 1152
    expect(top).toBeLessThanOrEqual(VH - BH);
  });

  it("flips above when there's no room below but room above", () => {
    const { top } = placeBubble(
      { top: 700, bottom: 760, left: 600, width: 120 },
      BW,
      BH,
      VW,
      VH,
    );
    // below (772) + 200 + 16 > 813 → flip above (700 - 200 - 12 = 488)
    expect(top).toBe(488);
  });

  it("clamps horizontal position within the viewport", () => {
    const right = placeBubble(
      { top: 60, bottom: 100, left: 1400, width: 30 },
      BW,
      BH,
      VW,
      VH,
    );
    expect(right.left).toBe(VW - BW - 16);
    const leftEdge = placeBubble(
      { top: 60, bottom: 100, left: -50, width: 30 },
      BW,
      BH,
      VW,
      VH,
    );
    expect(leftEdge.left).toBe(16);
  });
});
