import { useUpdateSettings } from "../hooks/useSettings";
import { changeClass, formatPct } from "../lib/format";
import { useUIStore } from "../store/uiStore";
import type { PortfolioSummary } from "../api/types";
import { DataStatusBadge } from "./DataStatusBadge";

function num(v: number): string {
  return v.toLocaleString("ko-KR", { maximumFractionDigits: 0 });
}

/** 통화별 금액 포맷 — null이면 "—". signed면 손익 부호(+/−)를 기호 앞에 붙인다. */
function fmtCurrency(
  v: number | null,
  currency: "KRW" | "USD",
  signed = false,
): string {
  if (v === null) return "—";
  const symbol = currency === "KRW" ? "₩" : "$";
  if (signed) {
    const sign = v > 0 ? "+" : v < 0 ? "−" : "";
    return `${sign}${symbol}${num(Math.abs(v))}`;
  }
  return `${symbol}${num(v)}`;
}

interface Props {
  summary: PortfolioSummary;
}

/**
 * 포트폴리오 요약 카드 — 홈 대시보드 + 포트폴리오 탭 공용 presentational 컴포넌트.
 * 보유가 없으면 렌더하지 않는다. 시세 없는 종목은 합계/비중에서 제외(정직).
 * KRW/USD 토글: useUIStore.baseCurrency 를 읽고, 변경 시 영속화한다.
 */
export function PortfolioSummaryCard({ summary: s }: Props) {
  const { setTab, baseCurrency, setBaseCurrency } = useUIStore();
  const update = useUpdateSettings();

  if (!s || s.positions.length === 0) return null;

  const valued = s.positions
    .filter((p) => p.weight != null)
    .sort((a, b) => (b.weight ?? 0) - (a.weight ?? 0));

  // 통화 전환 — UI 즉시 반영 + 영속화 (TopBar.tsx의 upColor 패턴과 동일)
  const handleCurrencyToggle = (c: "KRW" | "USD") => {
    setBaseCurrency(c);
    update.mutate({ ui: { baseCurrency: c } });
  };

  // 선택된 통화에 따라 KPI 값 선택
  const valueDisplay =
    baseCurrency === "KRW"
      ? fmtCurrency(s.valueKrw, "KRW")
      : fmtCurrency(s.valueUsd, "USD");

  const unrealizedDisplay =
    baseCurrency === "KRW"
      ? fmtCurrency(s.unrealizedKrw, "KRW", true)
      : fmtCurrency(s.unrealizedUsd, "USD", true);

  const realizedDisplay =
    baseCurrency === "KRW"
      ? fmtCurrency(s.realizedKrw, "KRW", true)
      : fmtCurrency(s.realizedUsd, "USD", true);

  const staleCount = s.positions.filter((p) => p.status === "STALE").length;

  // fx 없을 때 보여줄 배지: 선택 통화가 KRW이고 valueKrw === null 이면 fxStatus 배지 노출
  const fxUnavailable =
    (baseCurrency === "KRW" && s.valueKrw === null) ||
    (baseCurrency === "USD" && s.valueUsd === null);

  // 평가손익 부호 — KRW/USD 중 사용 가능한 값 기준
  const unrealizedNum = baseCurrency === "KRW" ? s.unrealizedKrw : s.unrealizedUsd;

  return (
    <div className="pf-card">
      <div className="pf-card-head">
        <span className="pf-card-title">내 포트폴리오</span>
        <span className="pf-currency-toggle">
          <button
            className={`chip${baseCurrency === "KRW" ? " active" : ""}`}
            onClick={() => handleCurrencyToggle("KRW")}
          >
            ₩ KRW
          </button>
          <button
            className={`chip${baseCurrency === "USD" ? " active" : ""}`}
            onClick={() => handleCurrencyToggle("USD")}
          >
            $ USD
          </button>
        </span>
        <button className="pf-card-link" onClick={() => setTab("portfolio")}>
          관리 →
        </button>
      </div>

      <div className="pf-kpis">
        <div className="pf-kpi">
          <span className="k">평가액</span>
          <b>{valueDisplay}</b>
          {fxUnavailable && <DataStatusBadge status={s.fxStatus} />}
        </div>
        <div className="pf-kpi">
          <span className="k">평가손익</span>
          <b className={changeClass(unrealizedNum)}>
            {unrealizedDisplay}
            {s.totalPnlPct !== null && ` (${formatPct(s.totalPnlPct)})`}
          </b>
          {fxUnavailable && <DataStatusBadge status={s.fxStatus} />}
        </div>
        <div className="pf-kpi">
          <span className="k">실현손익</span>
          <b
            className={changeClass(
              baseCurrency === "KRW" ? s.realizedKrw : s.realizedUsd,
            )}
          >
            {realizedDisplay}
          </b>
          {fxUnavailable && <DataStatusBadge status={s.fxStatus} />}
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

      {staleCount > 0 && (
        <p className="pf-stale-note muted">
          {staleCount}개 종목은 마지막 정상 시세 기준이에요(실시간 조회 실패).
        </p>
      )}
    </div>
  );
}
