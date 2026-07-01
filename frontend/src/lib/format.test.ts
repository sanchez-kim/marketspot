import { describe, expect, it } from "vitest";
import {
  changeClass,
  formatPct,
  formLabel,
  staleAge,
  statusHint,
  statusMeta,
} from "./format";

describe("statusMeta", () => {
  it("지연은 분 수를 라벨에 포함", () => {
    expect(statusMeta("DELAYED", 15).label).toBe("15분 지연");
  });

  it("실시간은 ok 톤", () => {
    expect(statusMeta("LIVE").tone).toBe("ok");
  });

  it("키 필요는 warn, 데이터없음은 muted", () => {
    expect(statusMeta("NEEDS_KEY").tone).toBe("warn");
    expect(statusMeta("NO_DATA").tone).toBe("muted");
    expect(statusMeta("ERROR").tone).toBe("error");
  });
});

describe("statusHint", () => {
  it("STALE은 마지막으로 받은 값이라는 뜻을 설명한다(실패라고 단정하지 않음)", () => {
    expect(statusHint("STALE")).toMatch(/마지막으로 받은 값/);
    expect(statusHint("STALE")).not.toBe("실패");
  });
  it("각 상태마다 서로 다른 뜻 문장을 준다(소스 문자열이 아니라 뜻)", () => {
    const statuses = [
      "LIVE",
      "DELAYED",
      "STALE",
      "NO_DATA",
      "NEEDS_KEY",
      "RATE_LIMITED",
      "ERROR",
    ] as const;
    const hints = statuses.map((s) => statusHint(s));
    expect(new Set(hints).size).toBe(statuses.length);
    hints.forEach((h) => expect(h.length).toBeGreaterThan(0));
  });
  it("NEEDS_KEY는 설정에서 키를 넣으라는 안내를 준다", () => {
    expect(statusHint("NEEDS_KEY")).toMatch(/설정/);
  });
});

describe("formatPct", () => {
  it("양수는 +부호", () => expect(formatPct(1.42)).toBe("+1.42%"));
  it("음수는 그대로", () => expect(formatPct(-0.87)).toBe("-0.87%"));
  it("null 은 대시", () => expect(formatPct(null)).toBe("—"));
});

describe("formLabel", () => {
  it("알려진 SEC 서식은 한국어 설명", () => {
    expect(formLabel("10-K")).toBe("연차보고서(실적)");
    expect(formLabel("NPORT-P")).toBe("펀드 보유내역");
  });
  it("대소문자 무시", () => expect(formLabel("8-k")).toBe("수시공시(주요사건)"));
  it("모르는 서식은 코드 그대로(가짜 라벨 ❌)", () =>
    expect(formLabel("X-99")).toBe("X-99"));
});

describe("changeClass", () => {
  it("부호별 클래스", () => {
    expect(changeClass(1)).toBe("up");
    expect(changeClass(-1)).toBe("down");
    expect(changeClass(0)).toBe("flat");
    expect(changeClass(null)).toBe("flat");
  });
});

describe("staleAge", () => {
  it("includes delay so it does not understate true age", () => {
    const asOf = "2026-06-30T00:00:00Z";
    const now = Date.parse("2026-06-30T00:02:00Z"); // fetch 2분 전
    // 2분 경과 + 15분 지연 = 약 17분
    expect(staleAge(asOf, 15, now)).toMatch(/17분/);
  });
  it("returns null when asOf is missing", () => {
    expect(staleAge(null, 15, Date.now())).toBeNull();
  });
});
