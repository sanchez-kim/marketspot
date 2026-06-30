import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { changeClass, formatPct } from "../lib/format";
import { useIsMobile } from "../hooks/useIsMobile";
import { useSettings, useUpdateSettings } from "../hooks/useSettings";
import { useUIStore } from "../store/uiStore";
import {
  useMacroConditions,
  usePortfolioRisk,
  useValuation,
} from "../hooks/useEvidence";
import { ChartPanel } from "./ChartPanel";
import { DrawdownCard } from "./DrawdownCard";
import { FilingsTab } from "./FilingsTab";
import { FundamentalsCard } from "./FundamentalsCard";
import { MacroPanel } from "./MacroPanel";
import { NewsTab } from "./NewsTab";
import { RiskPanel } from "./RiskPanel";
import { SymbolSearch } from "./SymbolSearch";
import { ValuationPanel } from "./ValuationPanel";

type Section = "info" | "chart" | "news" | "filings";
const SECTIONS: { id: Section; label: string }[] = [
  { id: "info", label: "기본정보" },
  { id: "chart", label: "차트" },
  { id: "news", label: "뉴스" },
  { id: "filings", label: "공시" },
];

/**
 * 종목 상세 — 한 종목에 대한 모든 것: 살펴보기(근거 4축) + 차트 + 뉴스 + 공시.
 * 좌측 관심종목 레일에서 바로 클릭해 전환하거나, 검색으로 다른 종목을 본다.
 */
export function SymbolTab() {
  const { symbol, setSymbol, reviewMode, setReviewMode, askAi } = useUIStore();
  const isMobile = useIsMobile();
  const [section, setSection] = useState<Section>("info");
  const settings = useSettings();
  const update = useUpdateSettings();
  const watchlist = settings.data?.watchlist ?? [];
  const isWatched = watchlist.includes(symbol.toUpperCase());

  const toggleWatch = () => {
    const sym = symbol.toUpperCase();
    update.mutate({
      watchlist: isWatched ? watchlist.filter((s) => s !== sym) : [...watchlist, sym],
    });
  };

  const quotes = useQuery({
    queryKey: ["quotes", watchlist],
    queryFn: () => api.quotes(watchlist),
    refetchInterval: 30_000,
    enabled: watchlist.length > 0,
  });
  const ctx = useQuery({
    queryKey: ["context", symbol],
    queryFn: () => api.context(symbol),
  });

  // 근거 축 훅
  const val = useValuation(symbol);
  const macro = useMacroConditions();
  const risk = usePortfolioRisk();

  return (
    <div className="symbol">
      {isMobile ? (
        <div className="rail-chips">
          <SymbolSearch onSelect={setSymbol} placeholder="종목 검색" />
          {watchlist.length === 0 && (
            <p className="muted">검색으로 종목을 추가해보세요.</p>
          )}
          {watchlist.length > 0 && (
            <div className="chip-row">
              {watchlist.map((s) => {
                const q = quotes.data?.[s]?.data;
                return (
                  <button
                    key={s}
                    className={`wl-chip ${s === symbol ? "active" : ""}`}
                    onClick={() => setSymbol(s)}
                  >
                    <span className="wl-chip-sym">{s}</span>
                    {q && (
                      <span className={changeClass(q.changePct)}>
                        {formatPct(q.changePct)}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          )}
        </div>
      ) : (
        <aside className="symbol-rail">
          <SymbolSearch onSelect={setSymbol} placeholder="종목 검색" />
          <div className="rail-list">
            {watchlist.length === 0 ? (
              <p className="muted">검색으로 종목을 추가해보세요.</p>
            ) : (
              watchlist.map((s) => {
                const q = quotes.data?.[s]?.data;
                return (
                  <button
                    key={s}
                    className={`rail-row ${s === symbol ? "active" : ""}`}
                    onClick={() => setSymbol(s)}
                  >
                    <span className="rail-sym">{s}</span>
                    {q && (
                      <span className={changeClass(q.changePct)}>
                        {formatPct(q.changePct)}
                      </span>
                    )}
                  </button>
                );
              })
            )}
          </div>
        </aside>
      )}

      <div className="symbol-detail">
        <div className="symbol-detail-head">
          <span className="symbol-name">{symbol}</span>
          <button
            className={`watch-toggle ${isWatched ? "on" : ""}`}
            onClick={toggleWatch}
            disabled={update.isPending}
          >
            {isWatched ? "★ 관심종목" : "☆ 관심종목 추가"}
          </button>
        </div>

        {/* ── 살펴보기 ──────────────────────────────────────────── */}
        <div className="briefing">
          <div className="briefing-head">
            <span className="briefing-title">살펴보기 · {symbol}</span>
            <div className="review-toggle" role="group" aria-label="검토 모드">
              {(
                [
                  ["add", "추가매수"],
                  ["hold", "보유점검"],
                  ["new", "신규편입"],
                ] as const
              ).map(([m, label]) => (
                <button
                  key={m}
                  className={reviewMode === m ? "rt on" : "rt"}
                  onClick={() => setReviewMode(m)}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
          <div className="ev-grid">
            <ValuationPanel data={val.data ?? null} />
            <DrawdownCard ctx={ctx.data ?? null} />
            {/* ② 기저율 — 기존 컴포넌트 재사용 */}
            <MacroPanel data={macro.data ?? null} />
            <RiskPanel data={risk.data ?? null} mode={reviewMode} />
          </div>
          <div className="briefing-foot">
            <span>여기까지가 사실, 판단은 당신 몫이에요.</span>
            <button
              className="ai-explain"
              onClick={() =>
                askAi(
                  `${symbol}의 근거 4축(밸류·기저율·거시·포트폴리오)을 초보자에게 쉽게 설명해줘. 예측·매수매도 말고 사실 위주로.`,
                )
              }
            >
              ✦ AI에게 물어보기
            </button>
          </div>
        </div>

        {/* ── 보조 근거: 차트 · 뉴스 · 공시 ─────────────────────── */}
        <div className="seg sym-seg">
          {SECTIONS.map((s) => (
            <button
              key={s.id}
              className={s.id === section ? "active" : ""}
              onClick={() => setSection(s.id)}
            >
              {s.label}
            </button>
          ))}
        </div>
        <div className="symbol-content">
          {section === "info" && (
            <div className="fund-scroll">
              <FundamentalsCard />
            </div>
          )}
          {section === "chart" && <ChartPanel />}
          {section === "news" && <NewsTab />}
          {section === "filings" && <FilingsTab />}
        </div>
      </div>
    </div>
  );
}
