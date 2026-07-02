import { api } from "../api/client";
import type { PortfolioSummary, Transaction } from "../api/types";

interface Props {
  transactions: Transaction[];
  onDeleted: (summary: PortfolioSummary) => void;
}

function fmtPrice(price: number, currency: string): string {
  return (
    price.toLocaleString("ko-KR", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }) +
    " " +
    currency
  );
}

function fmtQty(quantity: number): string {
  return quantity.toLocaleString("ko-KR", { maximumFractionDigits: 4 });
}

function sourceLabel(source: string | undefined): string {
  if (source === "toss") return "토스";
  if (source === "toss-baseline") return "기초";
  return "수동";
}

/**
 * 거래내역 리스트.
 * 각 행: 날짜(없으면 "기초 보유") · 유형(매수/매도) · 종목 · 수량 · 가격+통화 · × 삭제
 */
export function TransactionList({ transactions, onDeleted }: Props) {
  if (transactions.length === 0) {
    return <div className="empty-state muted">거래내역이 없습니다.</div>;
  }

  const handleDelete = async (id: string) => {
    try {
      const summary = await api.deleteTransaction(id);
      onDeleted(summary);
    } catch (err) {
      // 삭제 실패 시 콘솔만 기록 — UI 재시도는 사용자 몫
      console.error("거래 삭제 실패:", err instanceof Error ? err.message : err);
    }
  };

  return (
    <table className="pf-table txn-table">
      <thead>
        <tr>
          <th>날짜</th>
          <th>유형</th>
          <th>출처</th>
          <th>종목</th>
          <th className="r">수량</th>
          <th className="r">가격</th>
          <th />
        </tr>
      </thead>
      <tbody>
        {transactions.map((t) => (
          <tr key={t.id}>
            <td className="txn-date">{t.date ?? "기초 보유"}</td>
            <td className={`txn-type ${t.type === "buy" ? "buy" : "sell"}`}>
              {t.type === "buy" ? "매수" : "매도"}
            </td>
            <td className="pf-ccy">{sourceLabel(t.source)}</td>
            <td className="pf-sym">{t.symbol}</td>
            <td className="r">{fmtQty(t.quantity)}</td>
            <td className="r">{fmtPrice(t.price, t.currency)}</td>
            <td className="r">
              <button
                className="wl-del"
                title={`${t.symbol} 거래 삭제`}
                onClick={() => void handleDelete(t.id)}
              >
                ×
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
