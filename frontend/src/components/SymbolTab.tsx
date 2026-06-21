import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { changeClass, formatPct } from "../lib/format";
import { useSettings, useUpdateSettings } from "../hooks/useSettings";
import { useUIStore } from "../store/uiStore";
import { ChartPanel } from "./ChartPanel";
import { DrawdownCard } from "./DrawdownCard";
import { FilingsTab } from "./FilingsTab";
import { FundamentalsCard } from "./FundamentalsCard";
import { NewsTab } from "./NewsTab";
import { SymbolSearch } from "./SymbolSearch";

type Section = "info" | "chart" | "news" | "filings";
const SECTIONS: { id: Section; label: string }[] = [
  { id: "info", label: "기본정보" },
  { id: "chart", label: "차트" },
  { id: "news", label: "뉴스" },
  { id: "filings", label: "공시" },
];

/**
 * 종목 상세 — 한 종목에 대한 모든 것: 하락 맥락 + 차트 + 뉴스 + 공시.
 * 좌측 관심종목 레일에서 바로 클릭해 전환하거나, 검색으로 다른 종목을 본다.
 */
export function SymbolTab() {
  const { symbol, setSymbol } = useUIStore();
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

  return (
    <div className="symbol">
      <aside className="symbol-rail">
        <SymbolSearch onSelect={setSymbol} placeholder="종목 검색" />
        <div className="rail-list">
          {watchlist.map((s) => {
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
          })}
        </div>
      </aside>

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
        <DrawdownCard ctx={ctx.data ?? null} />
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
