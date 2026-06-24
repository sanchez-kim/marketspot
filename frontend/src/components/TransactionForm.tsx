import { useState } from "react";
import { api } from "../api/client";
import type { PortfolioSummary } from "../api/types";
import { SymbolSearch } from "./SymbolSearch";

interface Props {
  onAdded: (summary: PortfolioSummary) => void;
}

/** 심볼에서 표시 통화 추론 (서버사이드 결정, 여기선 힌트 표시용) */
function inferCurrency(symbol: string): string {
  return symbol.endsWith(".KS") || symbol.endsWith(".KQ") ? "KRW" : "USD";
}

/**
 * 거래 입력 폼 (매수/매도).
 *
 * 테스트 시임(seam): SymbolSearch는 비동기 드롭다운이라 테스트를 결정적으로
 * 만들기 어렵다. 그래서 `data-testid="txn-symbol"` 인 숨김 텍스트 입력을 통해
 * 테스트에서 직접 symbol 상태를 주입할 수 있도록 한다. 프로덕션에서는
 * SymbolSearch 가 이 값을 설정하며, 숨김 입력은 시각적으로 보이지 않는다.
 */
export function TransactionForm({ onAdded }: Props) {
  const [txnType, setTxnType] = useState<"buy" | "sell">("buy");
  const [symbol, setSymbol] = useState("");
  const [date, setDate] = useState("");
  const [quantity, setQuantity] = useState("");
  const [price, setPrice] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const currency = symbol ? inferCurrency(symbol) : "USD";

  const reset = () => {
    setSymbol("");
    setDate("");
    setQuantity("");
    setPrice("");
    setError(null);
  };

  const submit = async () => {
    const q = Number(quantity);
    const p = Number(price);
    if (
      !symbol.trim() ||
      !Number.isFinite(q) ||
      q <= 0 ||
      !Number.isFinite(p) ||
      p < 0
    ) {
      setError("종목·수량·가격을 올바르게 입력하세요.");
      return;
    }
    setError(null);
    setPending(true);
    try {
      const summary = await api.addTransaction({
        type: txnType,
        symbol: symbol.trim().toUpperCase(),
        quantity: q,
        price: p,
        date: date.trim() || null,
      });
      onAdded(summary);
      reset();
    } catch (err) {
      setError(err instanceof Error ? err.message : "거래 추가 실패");
    } finally {
      setPending(false);
    }
  };

  return (
    <div className="txn-form">
      {/* 매수/매도 토글 */}
      <div className="txn-toggle">
        <button
          className={`txn-type-btn${txnType === "buy" ? " active buy" : ""}`}
          onClick={() => setTxnType("buy")}
        >
          매수
        </button>
        <button
          className={`txn-type-btn${txnType === "sell" ? " active sell" : ""}`}
          onClick={() => setTxnType("sell")}
        >
          매도
        </button>
      </div>

      {/* 종목 선택 — 선택 후 chip 표시 / 미선택 시 SymbolSearch */}
      {symbol ? (
        <span className="pf-chip">
          {symbol}
          <button className="pf-chip-x" title="종목 변경" onClick={() => setSymbol("")}>
            ×
          </button>
        </span>
      ) : (
        <div className="pf-search">
          <SymbolSearch onSelect={(s) => setSymbol(s)} placeholder="종목 검색" />
        </div>
      )}

      {/*
        테스트 시임: 숨김 입력으로 symbol 상태를 직접 주입.
        실제 UI에서는 SymbolSearch 가 symbol을 설정하므로 이 입력은 보이지 않는다.
      */}
      <input
        data-testid="txn-symbol"
        type="text"
        aria-hidden="true"
        tabIndex={-1}
        value={symbol}
        onChange={(e) => setSymbol(e.target.value)}
        style={{
          position: "absolute",
          opacity: 0,
          pointerEvents: "none",
          width: 0,
          height: 0,
        }}
      />

      {/* 날짜 */}
      <input
        className="wl-input"
        type="date"
        aria-label="날짜"
        value={date}
        onChange={(e) => setDate(e.target.value)}
      />

      {/* 수량 */}
      <input
        className="wl-input"
        type="number"
        aria-label="수량"
        placeholder="수량"
        inputMode="decimal"
        min="0"
        value={quantity}
        onChange={(e) => setQuantity(e.target.value)}
      />

      {/* 가격 (통화 힌트 포함) */}
      <div className="txn-price-wrap">
        <input
          className="wl-input"
          type="number"
          aria-label="가격"
          placeholder="가격"
          inputMode="decimal"
          min="0"
          value={price}
          onChange={(e) => setPrice(e.target.value)}
        />
        <span className="txn-currency muted">{currency}</span>
      </div>

      {/* 제출 */}
      <button
        className="icon-btn"
        data-testid="txn-submit"
        onClick={() => void submit()}
        disabled={pending}
      >
        {txnType === "buy" ? "매수" : "매도"} 추가
      </button>

      {/* 서버 에러 인라인 표시 */}
      {error && <div className="txn-error">{error}</div>}
    </div>
  );
}
