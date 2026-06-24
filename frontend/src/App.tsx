import { useEffect, useRef } from "react";
import { TopBar } from "./components/TopBar";
import { IndexStrip } from "./components/IndexStrip";
import { HomeTab } from "./components/HomeTab";
import { SymbolTab } from "./components/SymbolTab";
import { PortfolioTab } from "./components/PortfolioTab";
import { AISidebar } from "./components/AISidebar";
import { useSettings } from "./hooks/useSettings";
import { useUIStore } from "./store/uiStore";

export default function App() {
  const {
    activeTab,
    upColor,
    density,
    setUpColor,
    setDensity,
    setBaseCurrency,
    setSymbol,
  } = useUIStore();
  const settings = useSettings();
  const hydratedSymbol = useRef(false);

  // 저장된 UI 설정을 런타임 스토어로 하이드레이트(새로고침해도 유지).
  useEffect(() => {
    const ui = settings.data?.ui;
    if (!ui) return;
    if (ui.upColor === "green" || ui.upColor === "red") setUpColor(ui.upColor);
    if (
      ui.density === "comfortable" ||
      ui.density === "normal" ||
      ui.density === "compact"
    ) {
      setDensity(ui.density);
    }
    if (ui.baseCurrency === "KRW" || ui.baseCurrency === "USD")
      setBaseCurrency(ui.baseCurrency);
  }, [settings.data?.ui, setUpColor, setDensity, setBaseCurrency]);

  // 기본 종목은 최초 1회만 반영(이후 사용자 네비게이션을 덮어쓰지 않게).
  useEffect(() => {
    const sym = settings.data?.defaultSymbol;
    if (sym && !hydratedSymbol.current) {
      hydratedSymbol.current = true;
      setSymbol(sym);
    }
  }, [settings.data?.defaultSymbol, setSymbol]);

  // 상승/하락 색상 규칙·밀도를 CSS 변수로 반영
  useEffect(() => {
    document.documentElement.dataset.upcolor = upColor;
    document.documentElement.dataset.density = density;
  }, [upColor, density]);

  return (
    <div className="app">
      <TopBar />
      <IndexStrip />
      <div className="app-main">
        <div className="app-body">
          {activeTab === "home" && <HomeTab />}
          {activeTab === "symbol" && <SymbolTab />}
          {activeTab === "portfolio" && <PortfolioTab />}
        </div>
        <AISidebar />
      </div>
    </div>
  );
}
