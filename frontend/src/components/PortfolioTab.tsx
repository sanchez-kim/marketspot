import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import type { PortfolioSummary } from "../api/types";
import { useIsMobile } from "../hooks/useIsMobile";
import { changeClass, formatPct, num, qtyFmt, signed } from "../lib/format";
import { useUIStore } from "../store/uiStore";
import { DataStatusBadge } from "./DataStatusBadge";
import { Panel } from "./Panel";
import { PortfolioSummaryCard } from "./PortfolioSummaryCard";
import { PositionCard } from "./PositionCard";
import { TossCard } from "./TossCard";
import { TransactionForm } from "./TransactionForm";
import { TransactionList } from "./TransactionList";

export function PortfolioTab() {
  const { setSymbol, setTab } = useUIStore();
  const isMobile = useIsMobile();
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
            <span className="big">아직 거래가 없어요.</span>
            <span>위 &#39;매수 추가&#39;로 첫 거래를 기록해보세요.</span>
          </div>
        )}

        {hasPositions &&
          (isMobile ? (
            <div className="pos-cards">
              {summary!.positions.map((p) => (
                <PositionCard key={p.symbol} p={p} onOpen={openChart} />
              ))}
            </div>
          ) : (
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
          ))}
      </Panel>

      <TossCard />

      <Panel title="거래내역">
        <TransactionList transactions={txns.data ?? []} onDeleted={applySummary} />
      </Panel>
    </div>
  );
}
