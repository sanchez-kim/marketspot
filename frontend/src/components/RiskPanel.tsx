import type { PortfolioRisk } from "../api/types";
import { DataStatusBadge } from "./DataStatusBadge";
import { Term } from "./Term";
import { AXIS_GUIDE } from "../lib/helpContent";

const HAS_DATA = new Set(["LIVE", "DELAYED", "STALE"]);
const EMPH: Record<"add" | "hold" | "new", string> = {
  add: "추가 시 이 종목 비중·집중도가 올라갑니다 — 쏠림을 확인하세요.",
  hold: "현재 비중과 보유 구성 기준입니다 — 한 종목 쏠림이 큰지 보세요.",
  new: "기존 보유와의 상관(분산 기여)을 보세요 — 같이 움직이면 분산 효과가 작습니다.",
};

/** 근거 ④ 포트폴리오 영향 — 집중도·상관(사실). 검토모드는 강조점만 바꾼다. */
export function RiskPanel({
  data,
  mode,
}: {
  data: PortfolioRisk | null;
  mode: "add" | "hold" | "new";
}) {
  if (!data || !HAS_DATA.has(data.status)) {
    return (
      <div className="ev-panel">
        <div className="ev-head">
          <span className="ev-title">포트폴리오 영향</span>
          {data && <DataStatusBadge status={data.status} />}
        </div>
        <div className="ev-empty">
          {data?.message ??
            (data?.status === "NO_DATA"
              ? "보유 종목이 없어 아직 볼 게 없어요 — 포트폴리오 탭에서 첫 거래를 기록하면 이 축이 채워져요."
              : "근거를 불러오지 못했습니다")}
        </div>
      </div>
    );
  }
  return (
    <div className="ev-panel">
      <div className="ev-head">
        <span className="ev-title">
          포트폴리오 영향
          <span
            className="gloss"
            title={AXIS_GUIDE.find((g) => g.title === "포트폴리오 영향")?.text}
          >
            <sup className="gloss-i">ⓘ</sup>
          </span>
        </span>
        <DataStatusBadge status={data.status} />
      </div>
      <div className="ev-rows">
        <div className="ev-row">
          <span>최대 비중</span>
          <b>
            {data.topSymbol}{" "}
            {data.topWeight === null ? "—" : `${data.topWeight.toFixed(1)}%`}
          </b>
        </div>
        <div className="ev-row">
          <span>
            <Term k="hhi">집중도(HHI)</Term>
          </span>
          <b>
            {data.concentrationHhi === null ? "—" : data.concentrationHhi.toFixed(2)}
          </b>
        </div>
        <div className="ev-row">
          <span>
            <Term k="corr">평균 상관</Term>
          </span>
          <b>{data.avgCorrelation === null ? "—" : data.avgCorrelation.toFixed(2)}</b>
        </div>
        {data.excluded.length > 0 && (
          <div className="ev-row">
            <span>제외(이력 없음)</span>
            <b>{data.excluded.join(", ")}</b>
          </div>
        )}
      </div>
      <p className="ev-note ev-emph">{EMPH[mode]}</p>
    </div>
  );
}
