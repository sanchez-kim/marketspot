import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import type { DrawdownContext } from "../api/types";
import { changeClass, formatPct, formatPrice, staleAge } from "../lib/format";
import { useSettings, useUpdateSettings } from "../hooks/useSettings";
import { useUIStore } from "../store/uiStore";
import { DataStatusBadge } from "./DataStatusBadge";
import { Sparkline } from "./Sparkline";
import { SymbolSearch } from "./SymbolSearch";

// 차분한 상태 라벨 — 불안을 키우지 않는 표현
function calmStatus(dd: number | null): { label: string; cls: string } {
  if (dd == null) return { label: "—", cls: "muted" };
  if (dd > -5) return { label: "안정", cls: "up" };
  if (dd > -15) return { label: "조정 중", cls: "flat" };
  return { label: "깊은 조정", cls: "down" };
}

export function HomeWatchlist() {
  const { setSymbol, setTab } = useUIStore();
  const settings = useSettings();
  const update = useUpdateSettings();
  const watchlist = settings.data?.watchlist ?? [];

  const quotes = useQuery({
    queryKey: ["quotes", watchlist],
    queryFn: () => api.quotes(watchlist),
    refetchInterval: 30_000,
    enabled: watchlist.length > 0,
  });
  const contexts = useQuery({
    queryKey: ["contexts", watchlist],
    queryFn: () => api.contexts(watchlist),
    enabled: watchlist.length > 0,
  });
  const spark = useQuery({
    queryKey: ["spark", watchlist],
    queryFn: () => api.spark(watchlist),
    enabled: watchlist.length > 0,
    staleTime: 5 * 60 * 1000,
  });

  const ctxBySymbol = useMemo(() => {
    const m = new Map<string, DrawdownContext>();
    contexts.data?.forEach((c) => m.set(c.symbol.toUpperCase(), c));
    return m;
  }, [contexts.data]);

  const add = (raw: string) => {
    const sym = raw.trim().toUpperCase();
    if (!sym || watchlist.includes(sym)) return;
    update.mutate({ watchlist: [...watchlist, sym] });
  };
  const remove = (sym: string) =>
    update.mutate({ watchlist: watchlist.filter((s) => s !== sym) });

  const open = (sym: string) => {
    setSymbol(sym);
    setTab("symbol");
  };

  return (
    <div className="hw">
      <div className="hw-head">
        <span className="hw-title">관심종목</span>
        <div className="hw-add">
          <SymbolSearch onSelect={add} placeholder="종목 추가 (예: SCHD)" />
        </div>
      </div>

      {watchlist.length === 0 && (
        <div className="muted hw-empty">위에서 종목을 검색해 담아보세요.</div>
      )}

      {watchlist.map((sym) => {
        const env = quotes.data?.[sym];
        const q = env?.data;
        const ctx = ctxBySymbol.get(sym);
        const dd = ctx?.currentDrawdownPct ?? null;
        const st = calmStatus(dd);
        return (
          <div className="hw-row" key={sym}>
            <span className="hw-sym" onClick={() => open(sym)}>
              {sym}
            </span>
            <span className="hw-px" onClick={() => open(sym)}>
              {q ? (
                <>
                  <span>{formatPrice(q.price)}</span>
                  {env.status === "STALE" ? (
                    <span className="quote-stale">
                      <DataStatusBadge status={env.status} source={env.source} />
                      <span className="muted q-age">
                        {staleAge(env.asOf, env.delayMinutes)}
                      </span>
                    </span>
                  ) : (
                    <span className={changeClass(q.changePct)}>
                      {formatPct(q.changePct)}
                    </span>
                  )}
                </>
              ) : env ? (
                <DataStatusBadge status={env.status} />
              ) : (
                <span className="muted">…</span>
              )}
            </span>
            <span className="hw-spark" onClick={() => open(sym)}>
              <Sparkline data={spark.data?.[sym] ?? []} />
            </span>
            <span className="hw-dd muted" onClick={() => open(sym)}>
              {dd == null ? "" : `고점 대비 ${dd.toFixed(1)}%`}
            </span>
            <span className={`hw-status ${st.cls}`} onClick={() => open(sym)}>
              {st.label}
            </span>
            <button
              className="wl-del"
              title={`${sym} 삭제`}
              onClick={() => remove(sym)}
            >
              ×
            </button>
          </div>
        );
      })}
    </div>
  );
}
