export interface TourStep {
  id: string;
  title: string;
  body: string;
  selector?: string; // 하이라이트 대상; 없으면 중앙 말풍선 폴백
  tab?: "home" | "symbol" | "portfolio";
}

export const TOUR_STEPS: TourStep[] = [
  {
    id: "home",
    title: "홈",
    body: "관심종목과 오늘 시장을 한눈에 봅니다.",
    tab: "home",
    selector: ".pf-card, .home-grid",
  },
  {
    id: "explore",
    title: "살펴보기",
    body: "한 종목을 깊이 볼 땐 여기서 '근거 4축'으로 살펴봐요.",
    tab: "symbol",
    selector: ".sym-tabbar, nav",
  },
  {
    id: "axes",
    title: "근거 4축",
    body: "밸류·기저율·거시·포트폴리오 영향. 예측이 아니라 사실을 차려줍니다.",
    tab: "symbol",
    selector: ".ev-grid",
  },
  {
    id: "ai",
    title: "AI 도우미",
    body: "모르는 용어나 수치는 여기서 편하게 물어보세요.",
    selector: ".ai-toggle, [data-tour='ai']",
  },
  {
    id: "done",
    title: "준비 끝",
    body: "언제든 상단 '?' 버튼으로 이 안내를 다시 볼 수 있어요.",
  },
];
