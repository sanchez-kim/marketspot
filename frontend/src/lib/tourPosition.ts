export interface Rect {
  top: number;
  bottom: number;
  left: number;
  width: number;
}

export interface BubblePlacement {
  top: number;
  left: number;
}

const MARGIN = 16;
const GAP = 12;

/**
 * 코치마크 말풍선을 대상 요소 근처에 두되 **항상 화면 안에** 들어오도록 위치를 정한다.
 * - 기본은 대상 아래. 아래 공간이 부족하면 대상 위로.
 * - 그래도 넘치면 top/left 를 뷰포트 안으로 클램프(말풍선이 잘리거나 화면 밖으로
 *   나가 버튼을 못 누르는 버그 방지).
 */
export function placeBubble(
  rect: Rect,
  bubbleW: number,
  bubbleH: number,
  vw: number,
  vh: number,
): BubblePlacement {
  // 가로: 대상 중앙 정렬 후 좌우 여백 클램프
  const left = Math.min(
    Math.max(rect.left + rect.width / 2 - bubbleW / 2, MARGIN),
    Math.max(vw - bubbleW - MARGIN, MARGIN),
  );

  // 세로: 아래 우선, 공간 없으면 위, 둘 다 부족하면 클램프
  const below = rect.bottom + GAP;
  const above = rect.top - bubbleH - GAP;
  let top: number;
  if (below + bubbleH + MARGIN <= vh) {
    top = below; // 아래 공간 충분
  } else if (above >= MARGIN) {
    top = above; // 위로
  } else {
    top = below; // 둘 다 빠듯 → 일단 아래로 두고 아래에서 클램프
  }
  top = Math.min(Math.max(top, MARGIN), Math.max(vh - bubbleH - MARGIN, MARGIN));
  return { top, left };
}
