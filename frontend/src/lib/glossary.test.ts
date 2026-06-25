// frontend/src/lib/glossary.test.ts
import { describe, expect, it } from "vitest";
import { GLOSSARY } from "./glossary";

const NEW_KEYS = ["hhi", "corr", "overheat", "ma200", "baserate", "cpi", "rate"];
const FORBIDDEN = ["오른다", "사라", "팔아라", "급등", "급락"];

describe("glossary evidence terms", () => {
  it("defines all new evidence-axis terms with non-empty beginner text", () => {
    for (const k of NEW_KEYS) {
      expect(GLOSSARY[k], k).toBeTruthy();
      expect(GLOSSARY[k].length).toBeGreaterThan(10);
    }
  });
  it("contains no prediction / buy-sell language", () => {
    for (const v of Object.values(GLOSSARY)) {
      for (const bad of FORBIDDEN) expect(v).not.toContain(bad);
    }
  });
});
