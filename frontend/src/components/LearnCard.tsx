import { tipOfTheDay } from "../lib/learn";
import { useUIStore } from "../store/uiStore";

/** 오늘의 배움 — 초보 용어/원칙 한 줄 + AI 로 더 알아보기. */
export function LearnCard() {
  const { askAi } = useUIStore();
  const tip = tipOfTheDay();
  return (
    <div className="learn">
      <div className="learn-head">
        <span className="learn-kicker">오늘의 배움</span>
        <button
          className="learn-more"
          onClick={() => askAi(`${tip.term}이(가) 뭔지 초보도 알기 쉽게 설명해줘.`)}
        >
          ✦ 더 알아보기
        </button>
      </div>
      <div className="learn-term">{tip.term}</div>
      <div className="learn-body">{tip.body}</div>
    </div>
  );
}
