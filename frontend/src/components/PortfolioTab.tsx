import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import type { Position } from "../api/types";
import { changeClass, formatPct } from "../lib/format";
import { useUIStore } from "../store/uiStore";
import { DataStatusBadge } from "./DataStatusBadge";
import { Panel } from "./Panel";
import { SymbolSearch } from "./SymbolSearch";

function num(v: number | null, digits = 2): string {
  return v == null
    ? "—"
    : v.toLocaleString("ko-KR", {
        minimumFractionDigits: digits,
        maximumFractionDigits: digits,
      });
}

function qtyFmt(v: number): string {
  return v.toLocaleString("ko-KR", { maximumFractionDigits: 4 });
}

function signed(v: number | null): string {
  if (v == null) return "—";
  return `${v >= 0 ? "+" : ""}${num(v)}`;
}

export function PortfolioTab() {
  const { setSymbol, setTab } = useUIStore();
  const qc = useQueryClient();

  const portfolio = useQuery({
    queryKey: ["portfolio"],
    queryFn: api.portfolio,
    refetchInterval: 30_000, // 시세 반영 주기
  });
  const mutate = useMutation({
    mutationFn: api.updatePortfolio,
    onSuccess: (data) => qc.setQueryData(["portfolio"], data),
  });

  const [sym, setSym] = useState("");
  const [qty, setQty] = useState("");
  const [cost, setCost] = useState("");

  const summary = portfolio.data;
  const positions: Position[] =
    summary?.positions.map((p) => ({
      symbol: p.symbol,
      quantity: p.quantity,
      avgCost: p.avgCost,
    })) ?? [];

  const add = () => {
    const s = sym.trim().toUpperCase();
    const q = Number(qty);
    const c = Number(cost);
    if (!s || !Number.isFinite(q) || q <= 0 || !Number.isFinite(c) || c < 0) return;
    // 같은 종목을 다시 추가하면 덮어쓴다(= 수정).
    const next = positions.filter((p) => p.symbol !== s);
    next.push({ symbol: s, quantity: q, avgCost: c });
    mutate.mutate(next);
    setSym("");
    setQty("");
    setCost("");
  };

  const canAdd =
    !!sym && Number(qty) > 0 && Number.isFinite(Number(cost)) && Number(cost) >= 0;

  const remove = (s: string) => mutate.mutate(positions.filter((p) => p.symbol !== s));

  const openChart = (s: string) => {
    setSymbol(s);
    setTab("symbol");
  };

  const hasPositions = !!summary && summary.positions.length > 0;

  return (
    <div style={{ height: "100%", padding: 12 }}>
      <Panel
        title="포트폴리오"
        right={
          hasPositions ? (
            <span className="pf-summary">
              <span className="k">평가액 </span>
              {num(summary!.totalValue)}
              <span className="k"> · 손익 </span>
              <span className={changeClass(summary!.totalPnl)}>
                {signed(summary!.totalPnl)} ({formatPct(summary!.totalPnlPct)})
              </span>
            </span>
          ) : undefined
        }
      >
        <div className="pf-add">
          {sym ? (
            <span className="pf-chip">
              {sym}
              <button
                className="pf-chip-x"
                title="종목 변경"
                onClick={() => setSym("")}
              >
                ×
              </button>
            </span>
          ) : (
            <div className="pf-search">
              <SymbolSearch onSelect={(s) => setSym(s)} placeholder="종목 검색" />
            </div>
          )}
          <input
            className="wl-input"
            placeholder="수량"
            inputMode="decimal"
            value={qty}
            onChange={(e) => setQty(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && add()}
          />
          <input
            className="wl-input"
            placeholder="평단"
            inputMode="decimal"
            value={cost}
            onChange={(e) => setCost(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && add()}
          />
          <button
            className="icon-btn"
            onClick={add}
            disabled={!canAdd || mutate.isPending}
          >
            ＋ 추가
          </button>
        </div>
        <div className="pf-hint muted">
          종목을 검색해 선택한 뒤 수량·평단을 입력하세요. 같은 종목 재추가 시
          수정됩니다.
        </div>

        {summary && summary.unvaluedCount > 0 && (
          <div className="ai-note">
            시세를 못 가져온 종목 {summary.unvaluedCount}개는 평가액·합계에서
            제외했습니다(가짜값 ❌).
          </div>
        )}

        {portfolio.isLoading && <div className="muted">불러오는 중…</div>}

        {summary && summary.positions.length === 0 && (
          <div className="empty-state">
            <span className="big">보유 종목이 없습니다</span>
            <span>위에서 종목·수량·평단을 입력해 추가하세요.</span>
          </div>
        )}

        {hasPositions && (
          <table className="pf-table">
            <thead>
              <tr>
                <th>종목</th>
                <th className="r">수량</th>
                <th className="r">평단</th>
                <th className="r">현재가</th>
                <th className="r">평가액</th>
                <th className="r">손익</th>
                <th className="r">비중</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {summary!.positions.map((p) => (
                <tr key={p.symbol}>
                  <td className="pf-sym" onClick={() => openChart(p.symbol)}>
                    {p.symbol}
                  </td>
                  <td className="r">{qtyFmt(p.quantity)}</td>
                  <td className="r">{num(p.avgCost)}</td>
                  <td className="r">
                    {p.price == null ? (
                      <DataStatusBadge status={p.status} />
                    ) : (
                      num(p.price)
                    )}
                  </td>
                  <td className="r">{num(p.marketValue)}</td>
                  <td className={`r ${changeClass(p.unrealizedPnl)}`}>
                    {p.unrealizedPnl == null
                      ? "—"
                      : `${signed(p.unrealizedPnl)} (${formatPct(p.unrealizedPnlPct)})`}
                  </td>
                  <td className="r">
                    {p.weight == null ? "—" : `${p.weight.toFixed(1)}%`}
                  </td>
                  <td className="r">
                    <button
                      className="wl-del"
                      title={`${p.symbol} 삭제`}
                      onClick={() => remove(p.symbol)}
                    >
                      ×
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Panel>
    </div>
  );
}
