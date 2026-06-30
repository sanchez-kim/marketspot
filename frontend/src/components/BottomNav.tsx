import { useUIStore, type TabId } from "../store/uiStore";

const TABS: { id: TabId; label: string; icon: string }[] = [
  { id: "home", label: "홈", icon: "🏠" },
  { id: "symbol", label: "살펴보기", icon: "🔍" },
  { id: "portfolio", label: "포트폴리오", icon: "📊" },
];

/**
 * 폰 하단 고정 탭바. App 에서 useIsMobile 일 때만 렌더한다.
 * 데스크톱 상단 탭(TopBar nav)과 동일한 setTab 을 쓴다.
 */
export function BottomNav() {
  const activeTab = useUIStore((s) => s.activeTab);
  const setTab = useUIStore((s) => s.setTab);
  return (
    <nav className="bottom-nav" aria-label="주 메뉴">
      {TABS.map((t) => (
        <button
          key={t.id}
          data-tab={t.id}
          className={`bn-item ${activeTab === t.id ? "active" : ""}`}
          onClick={() => setTab(t.id)}
        >
          <span className="bn-icon" aria-hidden="true">
            {t.icon}
          </span>
          <span className="bn-label">{t.label}</span>
        </button>
      ))}
    </nav>
  );
}
