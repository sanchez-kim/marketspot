// 오늘의 배움 — 초보 투자 한 줄. 매일 하나씩 보여준다(가벼운 학습 레이어).
export interface Tip {
  term: string;
  body: string;
}

export const TIPS: Tip[] = [
  {
    term: "적립식(DCA)",
    body: "정해진 금액을 일정 간격으로 꾸준히 사는 방법. 타이밍을 안 재도 평균 매입가가 분산돼요.",
  },
  {
    term: "분산투자",
    body: "한 종목에 몰지 않고 여러 곳에 나눠 담는 것. ETF는 그 자체로 수백 종목에 분산돼 있어요.",
  },
  {
    term: "복리",
    body: "수익이 다시 수익을 낳는 효과. 장기 투자에서 가장 강력한 친구예요.",
  },
  {
    term: "변동성",
    body: "가격이 위아래로 출렁이는 정도. 단기 변동은 장기 계획에 큰 영향이 없어요.",
  },
  {
    term: "보수율(ETF)",
    body: "ETF 운용에 드는 연 수수료. 낮을수록 장기적으로 내 수익이 더 남아요.",
  },
  {
    term: "PER",
    body: "주가가 회사 1년 이익의 몇 배인지. 높을수록 기대가 많이 반영된 비싼 가격이에요.",
  },
  {
    term: "배당",
    body: "회사가 이익 일부를 주주에게 나눠주는 돈. 적립하면 배당도 함께 쌓여요.",
  },
  {
    term: "고점 대비 낙폭(Drawdown)",
    body: "역대 최고가 대비 현재 얼마나 내렸는지. 조정은 흔하고 대부분 회복돼 왔어요.",
  },
  {
    term: "리밸런싱",
    body: "비중이 틀어진 자산을 원래 계획대로 되돌리는 것. 1년에 한 번 정도면 충분해요.",
  },
  {
    term: "장기투자",
    body: "짧은 등락에 흔들리지 않고 오래 보유하는 것. 시간이 변동성을 줄여줘요.",
  },
];

/** 날짜 기준으로 오늘의 팁을 고른다(하루 동안 고정). */
export function tipOfTheDay(now: Date = new Date()): Tip {
  const start = new Date(now.getFullYear(), 0, 0);
  const day = Math.floor((now.getTime() - start.getTime()) / 86_400_000);
  return TIPS[day % TIPS.length];
}
