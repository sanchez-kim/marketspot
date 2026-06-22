import type { MacroConditions, MacroMetric } from "../api/types";
import { DataStatusBadge } from "./DataStatusBadge";

const HAS_DATA = new Set(["LIVE", "DELAYED", "STALE"]);
const fmt = (m: MacroMetric) =>
  m.value === null
    ? "—"
    : `${m.value.toFixed(m.label.includes("CPI") ? 1 : 2)}${m.unit ?? ""}`;
const arrow = (c: number | null) => (c === null || c === 0 ? "" : c > 0 ? " ↑" : " ↓");

/** 근거 ③ 거시 환경 — 발표값·방향·이동평균선 대비. 예측 없음. */
export function MacroPanel({ data }: { data: MacroConditions | null }) {
  if (!data) {
    return (
      <div className="ev-panel">
        <div className="ev-head">
          <span className="ev-title">거시 환경</span>
        </div>
        <div className="ev-empty">근거를 불러오지 못했습니다</div>
      </div>
    );
  }
  const metric = (m: MacroMetric) => (
    <div className="ev-metric" key={m.label}>
      <div className="ev-row">
        <span>{m.label}</span>
        <b>
          {fmt(m)}
          {arrow(m.change)}
          {!HAS_DATA.has(m.status) && <DataStatusBadge status={m.status} />}
        </b>
      </div>
      {m.note && <p className="ev-subnote">{m.note}</p>}
    </div>
  );
  return (
    <div className="ev-panel">
      <div className="ev-head">
        <span className="ev-title">거시 환경</span>
      </div>
      <div className="ev-rows">
        {metric(data.rate)}
        {metric(data.cpi)}
        {data.indices.map((ix) => (
          <div className="ev-row" key={ix.symbol}>
            <span>{ix.label} · 200일선</span>
            <b>{ix.vsMa200Pct === null ? "—" : `${ix.vsMa200Pct.toFixed(1)}%`}</b>
          </div>
        ))}
      </div>
      <p className="ev-note">
        금리·물가·지수의 방향까지만 — "그래서 오른다"는 예측은 하지 않음.
      </p>
    </div>
  );
}
