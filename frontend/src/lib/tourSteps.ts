export interface TourStep {
  id: string;
  title: string;
  body: string;
  selector?: string; // 하이라이트 대상; 없으면 중앙 말풍선 폴백
  tab?: "home" | "symbol" | "portfolio";
}

export const TOUR_STEPS: TourStep[] = [
  {
    id: "welcome",
    title: "MarketSpot에 오신 걸 환영해요 👋",
    body:
      "예측이나 매수·매도 권유 없이, 판단에 필요한 근거만 차분하게 차려주는 앱이에요. " +
      "처음이시니 1분만 어디에 뭐가 있는지 함께 둘러볼까요? (오른쪽 아래 '건너뛰기'로 언제든 닫을 수 있어요.)",
  },
  {
    id: "home",
    title: "① 홈",
    body: "내 포트폴리오·관심종목·오늘 시장을 여기 홈에서 한눈에 봐요.",
    tab: "home",
    selector: ".pf-card",
  },
  {
    id: "explore",
    title: "② 살펴보기",
    body: "한 종목을 깊이 보고 싶을 땐 이 '살펴보기' 탭에서 '근거 4축'으로 차근차근 살펴봐요.",
    tab: "symbol",
    selector: "[data-tour='tab-explore']",
  },
  {
    id: "axes",
    title: "③ 근거 4축",
    body: "밸류·기저율·거시·포트폴리오 영향, 이 네 가지를 봐요. 예측이 아니라 '사실'을 차려드려요.",
    tab: "symbol",
    selector: ".ev-grid",
  },
  {
    id: "ai",
    title: "④ AI 도우미",
    body: "모르는 용어나 숫자가 나오면 여기서 물어보세요. 로컬 AI(Ollama)가 켜져 있으면 더 자세히 풀어드려요.",
    selector: ".ai-toggle, [data-tour='ai']",
  },
  {
    id: "done",
    title: "이제 준비됐어요 🎉",
    body: "천천히 둘러보세요. 다시 보고 싶으면 언제든 상단 '?' 버튼을 누르면 돼요.",
  },
];
