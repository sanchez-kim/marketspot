import { useUIStore } from "../store/uiStore";

/**
 * 홈 포트폴리오 슬롯의 빈 상태 — 보유/거래가 없을 때 행동을 안내한다.
 * `.pf-card` 클래스를 그대로 써서 레이아웃·온보딩 투어 앵커(.pf-card)가 항상 존재하게 한다.
 */
export function EmptyPortfolioCta() {
  const setTab = useUIStore((s) => s.setTab);
  return (
    <div className="pf-card pf-card-empty">
      <div className="pf-card-head">
        <span className="pf-card-title">내 포트폴리오</span>
      </div>
      <p className="pf-empty-msg">
        아직 거래가 없어요. 포트폴리오 탭에서 첫 매수를 기록하면 평단·손익·비중을
        자동으로 정리해 드려요.
      </p>
      <button className="pf-empty-cta" onClick={() => setTab("portfolio")}>
        포트폴리오로 가기 →
      </button>
    </div>
  );
}
