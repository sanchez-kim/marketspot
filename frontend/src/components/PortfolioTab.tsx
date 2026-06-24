import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import type { PortfolioSummary } from "../api/types";
import { changeClass, formatPct } from "../lib/format";
import { useUIStore } from "../store/uiStore";
import { DataStatusBadge } from "./DataStatusBadge";
import { Panel } from "./Panel";
import { PortfolioSummaryCard } from "./PortfolioSummaryCard";
import { TransactionForm } from "./TransactionForm";
import { TransactionList } from "./TransactionList";

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
  const txns = useQuery({
    queryKey: ["transactions"],
    queryFn: api.transactions,
  });

  // 거래 추가/삭제는 권위 있는 요약(summary)을 돌려준다. 포트폴리오 캐시는
  // 그 값으로 직접 갱신하고, 거래내역은 invalidate 하여 다시 가져온다.
  const applySummary = (summary: PortfolioSummary) => {
    qc.setQueryData(["portfolio"], summary);
    void qc.invalidateQueries({ queryKey: ["transactions"] });
  };

  const openChart = (s: string) => {
    setSymbol(s);
    setTab("symbol");
  };

  const summary = portfolio.data;
  const hasPositions = !!summary && summary.positions.length > 0;
  const hasTxns = (txns.data?.length ?? 0) > 0;

  return (
    <div style={{ height: "100%", padding: 12, overflow: "auto" }}>
      <Panel title="포트폴리오">
        {summary && <PortfolioSummaryCard summary={summary} />}

        {/* 거래 입력 — 포지션은 거래로부터 파생된다(직접 추가/삭제 ❌). */}
        <TransactionForm onAdded={applySummary} />

        {portfolio.isLoading && <div className="muted">불러오는 중…</div>}

        {summary && summary.unvaluedCount > 0 && (
          <div className="ai-note">
            시세를 못 가져온 종목 {summary.unvaluedCount}개는 평가액·합계에서
            제외했습니다(가짜값 ❌).
          </div>
        )}

        {!portfolio.isLoading && !hasPositions && !hasTxns && (
          <div className="empty-state">
            <span className="big">보유 종목이 없습니다</span>
            <span>아래에서 매수 거래를 추가해 포트폴리오를 시작하세요.</span>
          </div>
        )}

        {hasPositions && (
          <table className="pf-table">
            <thead>
              <tr>
                <th>종목</th>
                <th>통화</th>
                <th className="r">수량</th>
                <th className="r">평단</th>
                <th className="r">현재가</th>
                <th className="r">평가액</th>
                <th className="r">미실현손익</th>
                <th className="r">실현손익</th>
                <th className="r">비중</th>
              </tr>
            </thead>
            <tbody>
              {summary!.positions.map((p) => (
                <tr key={p.symbol}>
                  <td className="pf-sym" onClick={() => openChart(p.symbol)}>
                    {p.symbol}
                  </td>
                  <td>
                    <span className="pf-ccy">{p.currency ?? "—"}</span>
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
                  <td className={`r ${changeClass(p.realizedPnl)}`}>
                    {signed(p.realizedPnl)}
                  </td>
                  <td className="r">
                    {p.weight == null ? "—" : `${p.weight.toFixed(1)}%`}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Panel>

      <Panel title="거래내역">
        <TransactionList transactions={txns.data ?? []} onDeleted={applySummary} />
      </Panel>
    </div>
  );
}
