import { APP_INTRO, AXIS_GUIDE, TAB_GUIDE } from "../lib/helpContent";
import { GLOSSARY } from "../lib/glossary";
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

        {/* 용어 미니 사전 */}
        <section className="help-section">
          <h3 className="help-section-title">용어 풀이</h3>
          <dl className="help-glossary">
            {Object.entries(GLOSSARY).map(([term, definition]) => (
              <div key={term} className="help-gloss-item">
                <dt className="help-gloss-term">{term}</dt>
                <dd className="help-gloss-def">{definition}</dd>
              </div>
            ))}
          </dl>
        </section>

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
