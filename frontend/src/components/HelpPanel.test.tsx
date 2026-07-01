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

  it("explains all 7 DataStatus badge meanings (honesty backbone)", () => {
    act(() => useUIStore.setState({ helpOpen: true, tourOpen: false }));
    render(<HelpPanel />);
    expect(screen.getByText("데이터 상태 표시")).toBeInTheDocument();
    // 라벨 7개 모두 노출
    [
      "실시간",
      "지연",
      "갱신지연",
      "데이터 없음",
      "API 키 필요",
      "호출 제한",
      "오류",
    ].forEach((label) => expect(screen.getByText(label)).toBeInTheDocument());
    // STALE(갱신지연)은 "실패"가 아니라 마지막으로 받은 값이라는 정직한 설명
    expect(screen.getByText(/마지막으로 받은 값/)).toBeInTheDocument();
  });
});
