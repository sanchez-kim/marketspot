import type {
  DataStatus,
  DrawdownContext,
  MacroConditions,
  PortfolioRisk,
  ValuationContext,
} from "../api/types";

const HAS_DATA = new Set<DataStatus>(["LIVE", "DELAYED", "STALE"]);
const signed = (v: number) => `${v >= 0 ? "+" : ""}${v.toFixed(1)}%`;

interface Evidence {
  valuation?: ValuationContext | null;
  drawdown?: DrawdownContext | null;
  macro?: MacroConditions | null;
  risk?: PortfolioRisk | null;
}

/**
 * AI 도우미용 근거 컨텍스트 — 현재 종목의 *실제 수치*를 한 블록으로 정리해
 * 모델이 지어내지 않고 근거 기반으로 설명하게 한다(grounding). 데이터가 없거나
 * 상태가 정상이 아니면 그 항목을 정직하게 생략한다(가짜 ❌).
 */
export function buildEvidenceContext(symbol: string, ev: Evidence): string {
  const lines: string[] = [];

  const val = ev.valuation;
  if (val && HAS_DATA.has(val.status)) {
    const parts: string[] = [];
    if (val.peRatio != null) {
      let per = `PER ${val.peRatio.toFixed(1)}`;
      if (val.peVs5YAvgPct != null)
        per += ` (5년평균 대비 ${signed(val.peVs5YAvgPct)})`;
      parts.push(per);
    }
    if (val.dividendYield != null)
      parts.push(`배당수익률 ${val.dividendYield.toFixed(2)}%`);
    if (val.week52PositionPct != null)
      parts.push(`52주 위치 ${val.week52PositionPct.toFixed(1)}%`);
    if (val.vsMa200Pct != null) parts.push(`200일선 대비 ${signed(val.vsMa200Pct)}`);
    if (parts.length) lines.push(`밸류: ${parts.join(", ")}`);
  }

  const dd = ev.drawdown;
  if (dd && HAS_DATA.has(dd.status)) {
    const parts: string[] = [];
    if (dd.currentDrawdownPct != null)
      parts.push(`고점 대비 ${dd.currentDrawdownPct.toFixed(1)}%`);
    if (dd.comparableCount > 0 && dd.historyYears != null)
      parts.push(
        `지난 ${dd.historyYears.toFixed(0)}년 ${dd.thresholdPct?.toFixed(0) ?? "?"}%↑ ` +
          `조정 ${dd.comparableCount}번 중 ${dd.recoveredCount}번 회복`,
      );
    if (dd.worstDrawdownPct != null)
      parts.push(`역대 최악 ${dd.worstDrawdownPct.toFixed(0)}%`);
    if (parts.length) lines.push(`하락맥락: ${parts.join(", ")}`);
  }

  const macro = ev.macro;
  if (macro) {
    const parts: string[] = [];
    if (HAS_DATA.has(macro.rate.status) && macro.rate.value != null)
      parts.push(`기준금리 ${macro.rate.value.toFixed(2)}%`);
    if (HAS_DATA.has(macro.cpi.status) && macro.cpi.value != null)
      parts.push(`CPI ${macro.cpi.value.toFixed(1)}%`);
    for (const ix of macro.indices) {
      if (HAS_DATA.has(ix.status) && ix.vsMa200Pct != null)
        parts.push(`${ix.label} 200일선 ${signed(ix.vsMa200Pct)}`);
    }
    if (parts.length) lines.push(`거시: ${parts.join(", ")}`);
  }

  const risk = ev.risk;
  if (risk && HAS_DATA.has(risk.status)) {
    const parts: string[] = [];
    if (risk.concentrationHhi != null)
      parts.push(`집중도(HHI) ${risk.concentrationHhi.toFixed(2)}`);
    if (risk.topSymbol && risk.topWeight != null)
      parts.push(`최대비중 ${risk.topSymbol} ${risk.topWeight.toFixed(1)}%`);
    if (risk.avgCorrelation != null)
      parts.push(`평균 상관 ${risk.avgCorrelation.toFixed(2)}`);
    if (parts.length) lines.push(`포트폴리오: ${parts.join(", ")}`);
  }

  if (!lines.length) return "";
  return [`[현재 종목 근거 — ${symbol}]`, ...lines].join("\n");
}
