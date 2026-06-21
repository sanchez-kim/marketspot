import { useUIStore, type TabId } from "../store/uiStore";
import { useUpdateSettings } from "../hooks/useSettings";
import { Logo } from "./Logo";

const TABS: { id: TabId; label: string }[] = [
  { id: "home", label: "홈" },
  { id: "symbol", label: "종목" },
  { id: "portfolio", label: "포트폴리오" },
];

export function TopBar() {
  const { activeTab, setTab, upColor, setUpColor, aiOpen, toggleAi } = useUIStore();
  const update = useUpdateSettings();

  const toggleUpColor = () => {
    const next = upColor === "green" ? "red" : "green";
    setUpColor(next); // 즉시 UI 반영
    update.mutate({ ui: { upColor: next } }); // 영속화
  };

  return (
    <header className="topbar">
      <span className="brand">
        <Logo size={22} />
        <span className="brand-name">
          Market<span className="brand-spot">Spot</span>
        </span>
      </span>
      <nav>
        {TABS.map((t) => (
          <button
            key={t.id}
            className={`tab-btn ${activeTab === t.id ? "active" : ""}`}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </nav>
      <span className="spacer" />
      <button
        className="icon-btn"
        title="상승/하락 색상 전환 (저장됨)"
        onClick={toggleUpColor}
      >
        {upColor === "green" ? "🟢 미국식" : "🔴 한국식"}
      </button>
      <button
        className={`icon-btn ${aiOpen ? "active" : ""}`}
        title="AI 어시스턴트 열기/닫기"
        onClick={toggleAi}
      >
        ✦ AI
      </button>
    </header>
  );
}
