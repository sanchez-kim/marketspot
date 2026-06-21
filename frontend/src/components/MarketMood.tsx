import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { changeClass, formatPct } from "../lib/format";

/** 시장 분위기 — 주요 지수 + 차분한 한 줄 해석(상단 스트립 보강). */
export function MarketMood() {
  const strip = useQuery({
    queryKey: ["strip"],
    queryFn: api.strip,
    refetchInterval: 60_000,
  });
  const items = strip.data ?? [];
  const valued = items.filter((s) => s.quote.data?.changePct != null);
  if (valued.length === 0) return null;

  const ups = valued.filter((s) => (s.quote.data?.changePct ?? 0) > 0).length;
  const ratio = ups / valued.length;
  const mood =
    ratio >= 0.6
      ? "대체로 상승세예요"
      : ratio <= 0.4
        ? "대체로 약세예요"
        : "혼조세예요";

  return (
    <div className="mood">
      <div className="mood-head">
        <span className="mood-title">오늘 시장</span>
        <span className="muted">{mood}</span>
      </div>
      <div className="mood-row">
        {valued.map((s) => {
          const pct = s.quote.data?.changePct ?? null;
          return (
            <span className="mood-item" key={s.symbol}>
              <span className="muted">{s.label}</span>
              <span className={changeClass(pct)}>{formatPct(pct)}</span>
            </span>
          );
        })}
      </div>
      <div className="mood-note muted">단기 등락은 장기 계획에 큰 영향이 없어요.</div>
    </div>
  );
}
