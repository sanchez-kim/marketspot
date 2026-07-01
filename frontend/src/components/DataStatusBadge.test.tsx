import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DataStatusBadge } from "./DataStatusBadge";

describe("DataStatusBadge", () => {
  it("title은 소스 문자열이 아니라 상태의 뜻을 담는다", () => {
    render(<DataStatusBadge status="STALE" source="yfinance" />);
    const badge = screen.getByText("갱신지연");
    expect(badge).toHaveAttribute("title");
    const title = badge.getAttribute("title") ?? "";
    expect(title).not.toBe("yfinance");
    // STALE은 실패로 오해되지 않게 "마지막으로 받은 값"이라는 뜻을 전달
    expect(title).toMatch(/마지막으로 받은 값/);
  });

  it("visible 라벨(statusMeta)은 그대로 유지된다", () => {
    render(<DataStatusBadge status="NEEDS_KEY" />);
    expect(screen.getByText("API 키 필요")).toBeInTheDocument();
  });

  it("source가 없어도 뜻이 담긴 title을 보여준다", () => {
    render(<DataStatusBadge status="RATE_LIMITED" />);
    const badge = screen.getByText("호출 제한");
    expect(badge.getAttribute("title")).toBeTruthy();
  });
});
