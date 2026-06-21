import type { ValuationContext } from "../api/types";
import { DataStatusBadge } from "./DataStatusBadge";

const HAS_DATA = new Set(["LIVE", "DELAYED", "STALE"]);
const num = (v: number | null, suffix = "") =>
  v === null || Number.isNaN(v) ? "—" : `${v.toFixed(1)}${suffix}`;

/** 근거 ① 밸류·과열도 — 사실만. 판단(싸다/비싸다)은 사용자. */
export function ValuationPanel({ data }: { data: ValuationContext | null }) {
  if (!data || !HAS_DATA.has(data.status)) {
    return (
      <div className="ev-panel">
        <div className="ev-head">
          <span className="ev-title">밸류·과열도</span>
          {data && <DataStatusBadge status={data.status} />}
        </div>
        <div className="ev-empty">{data?.message ?? "근거를 불러오지 못했습니다"}</div>
      </div>
    );
  }
  return (
    <div className="ev-panel">
      <div className="ev-head">
        <span className="ev-title">밸류·과열도</span>
        <DataStatusBadge status={data.status} />
      </div>
      <div className="ev-rows">
        <div className="ev-row">
          <span>현재 PER</span>
          <b>{num(data.peRatio)}</b>
        </div>
        <div className="ev-row">
          <span>배당수익률</span>
          <b>{num(data.dividendYield, "%")}</b>
        </div>
        <div className="ev-row">
          <span>52주 밴드 내 위치</span>
          <b>{num(data.week52PositionPct, "%")}</b>
        </div>
        <div className="ev-row">
          <span>200일선 대비</span>
          <b>{num(data.vsMa200Pct, "%")}</b>
        </div>
      </div>
      <p className="ev-note">
        {data.note ??
          "사실이지 판단이 아님 — 비싸도 더 갈 수 있고 싸도 더 빠질 수 있음."}
      </p>
    </div>
  );
}
