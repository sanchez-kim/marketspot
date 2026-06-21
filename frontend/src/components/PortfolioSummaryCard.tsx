import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { changeClass, formatPct } from "../lib/format";
import { useUIStore } from "../store/uiStore";

function num(v: number): string {
  return v.toLocaleString("ko-KR", { maximumFractionDigits: 0 });
}

/**
 * 홈 대시보드 위젯 — 내 포트폴리오 한눈에: 총 평가액·손익 + 보유 비중 막대.
 * 보유가 없으면 렌더하지 않는다. 시세 없는 종목은 합계/비중에서 제외(정직).
 */
export function PortfolioSummaryCard() {
  const { setTab } = useUIStore();
  const pf = useQuery({
    queryKey: ["portfolio"],
    queryFn: api.portfolio,
    refetchInterval: 60_000,
  });

  const s = pf.data;
  if (!s || s.positions.length === 0) return null;

  const valued = s.positions
    .filter((p) => p.weight != null)
    .sort((a, b) => (b.weight ?? 0) - (a.weight ?? 0));

  return (
    <div className="pf-card">
      <div className="pf-card-head">
        <span className="pf-card-title">내 포트폴리오</span>
        <button className="pf-card-link" onClick={() => setTab("portfolio")}>
          관리 →
        </button>
      </div>

      <div className="pf-kpis">
        <div className="pf-kpi">
          <span className="k">평가액</span>
          <b>{num(s.totalValue)}</b>
        </div>
        <div className="pf-kpi">
          <span className="k">평가손익</span>
          <b className={changeClass(s.totalPnl)}>
            {s.totalPnl >= 0 ? "+" : ""}
            {num(s.totalPnl)} ({formatPct(s.totalPnlPct)})
          </b>
        </div>
        <div className="pf-kpi">
          <span className="k">보유</span>
          <b>{s.valuedCount}종목</b>
        </div>
      </div>

      <div className="pf-alloc">
        {valued.map((p) => (
          <div className="alloc-row" key={p.symbol}>
            <span className="alloc-sym">{p.symbol}</span>
            <span className="alloc-bar">
              <span style={{ width: `${Math.max(p.weight ?? 0, 1)}%` }} />
            </span>
            <span className="alloc-w">{(p.weight ?? 0).toFixed(0)}%</span>
            <span className={`alloc-pnl ${changeClass(p.unrealizedPnl)}`}>
              {formatPct(p.unrealizedPnlPct)}
            </span>
          </div>
        ))}
      </div>

      {s.unvaluedCount > 0 && (
        <div className="muted pf-card-note">
          시세 못 받은 {s.unvaluedCount}종목은 합계에서 제외했어요.
        </div>
      )}
    </div>
  );
}
