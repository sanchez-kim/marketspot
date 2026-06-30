import type { PositionValuation } from "../api/types";
import { changeClass, formatPct, num, qtyFmt, signed } from "../lib/format";
import { DataStatusBadge } from "./DataStatusBadge";

/**
 * 폰 포트폴리오의 한 종목 카드. 데스크톱 9열 표를 대신한다(동일 데이터·동일 정직 표기).
 */
export function PositionCard({
  p,
  onOpen,
}: {
  p: PositionValuation;
  onOpen: (s: string) => void;
}) {
  return (
    <div className="pos-card">
      <div className="pos-card-head">
        <button className="pos-sym" onClick={() => onOpen(p.symbol)}>
          {p.symbol}
        </button>
        <span className="pos-mv">{num(p.marketValue)}</span>
      </div>
      <div className="pos-grid">
        <span className="pos-k">통화</span>
        <span className="pos-v">{p.currency ?? "—"}</span>
        <span className="pos-k">수량</span>
        <span className="pos-v">{qtyFmt(p.quantity)}</span>
        <span className="pos-k">평단</span>
        <span className="pos-v">{num(p.avgCost)}</span>
        <span className="pos-k">현재가</span>
        <span className="pos-v">
          {p.price == null ? <DataStatusBadge status={p.status} /> : num(p.price)}
        </span>
        <span className="pos-k">평가액</span>
        <span className="pos-v">{num(p.marketValue)}</span>
        <span className="pos-k">미실현손익</span>
        <span className={`pos-v ${changeClass(p.unrealizedPnl)}`}>
          {p.unrealizedPnl == null
            ? "—"
            : `${signed(p.unrealizedPnl)} (${formatPct(p.unrealizedPnlPct)})`}
        </span>
        <span className="pos-k">실현손익</span>
        <span className={`pos-v ${changeClass(p.realizedPnl)}`}>
          {signed(p.realizedPnl)}
        </span>
        <span className="pos-k">비중</span>
        <span className="pos-v">
          {p.weight == null ? "—" : `${p.weight.toFixed(1)}%`}
        </span>
      </div>
    </div>
  );
}
