import { APP_INTRO, AXIS_GUIDE, STATUS_GUIDE, TAB_GUIDE } from "../lib/helpContent";
import { GLOSSARY, GLOSSARY_LABELS } from "../lib/glossary";
import { useUIStore } from "../store/uiStore";

export function HelpPanel() {
  const helpOpen = useUIStore((s) => s.helpOpen);
  const closeHelp = useUIStore((s) => s.closeHelp);
  const startTour = useUIStore((s) => s.startTour);

  if (!helpOpen) return null;

  function handleRestartTour() {
    closeHelp();
    startTour();
  }

  return (
    <div className="help-overlay" role="presentation" onClick={closeHelp}>
      <div
        className="help-card"
        role="dialog"
        aria-modal="true"
        aria-label="도움말"
        onClick={(e) => e.stopPropagation()}
      >
        {/* 헤더 */}
        <div className="help-card-head">
          <span className="help-card-title">시작하기 / 도움말</span>
          <button className="help-close" aria-label="닫기" onClick={closeHelp}>
            ✕
          </button>
        </div>

        {/* 스크롤 본문 — 헤더/푸터는 고정, 가운데만 스크롤(투어 버튼 항상 노출) */}
        <div className="help-body">
          {/* 앱 소개 */}
          <section className="help-section">
            <p className="help-intro">{APP_INTRO}</p>
          </section>

          {/* 탭 안내 */}
          <section className="help-section">
            <h3 className="help-section-title">탭 안내</h3>
            <ul className="help-tab-list">
              {TAB_GUIDE.map(({ tab, text }) => (
                <li key={tab} className="help-tab-item">
                  <span className="help-tab-name">{tab}</span>
                  <span className="help-tab-text">{text}</span>
                </li>
              ))}
            </ul>
          </section>

          {/* 근거 4축 */}
          <section className="help-section">
            <h3 className="help-section-title">근거 4축</h3>
            <ul className="help-axis-list">
              {AXIS_GUIDE.map(({ title, text }) => (
                <li key={title} className="help-axis-item">
                  <span className="help-axis-title">{title}</span>
                  <span className="help-axis-text">{text}</span>
                </li>
              ))}
            </ul>
          </section>

          {/* 데이터 상태 표시 */}
          <section className="help-section">
            <h3 className="help-section-title">데이터 상태 표시</h3>
            <ul className="help-status-list">
              {STATUS_GUIDE.map(({ label, text }) => (
                <li key={label} className="help-status-item">
                  <span className="help-status-label">{label}</span>
                  <span className="help-status-text">{text}</span>
                </li>
              ))}
            </ul>
          </section>

          {/* 용어 미니 사전 */}
          <section className="help-section">
            <h3 className="help-section-title">용어 풀이</h3>
            <dl className="help-glossary">
              {Object.entries(GLOSSARY).map(([term, definition]) => (
                <div key={term} className="help-gloss-item">
                  <dt className="help-gloss-term">{GLOSSARY_LABELS[term] ?? term}</dt>
                  <dd className="help-gloss-def">{definition}</dd>
                </div>
              ))}
            </dl>
          </section>
        </div>

        {/* 액션 */}
        <div className="help-card-foot">
          <button className="help-tour-btn" onClick={handleRestartTour}>
            투어 다시 보기
          </button>
        </div>
      </div>
    </div>
  );
}
