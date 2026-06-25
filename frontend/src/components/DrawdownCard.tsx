import type { DrawdownContext } from "../api/types";
import { Term } from "./Term";
import { AXIS_GUIDE } from "../lib/helpContent";

function recoveryLabel(days: number | null): string {
  if (days == null) return "—";
  if (days < 45) return `${days}일`;
  return `약 ${Math.round(days / 30)}개월`;
}

interface Props {
  ctx: DrawdownContext | null;
}

/**
 * 하락 맥락 카드 — 고점 대비 낙폭 + 과거 조정의 정직한 기저율.
 * 예측이 아니라 역사적 사실만, 데이터 부족이면 그렇게 표기한다.
 */
export function DrawdownCard({ ctx }: Props) {
  if (!ctx || !["LIVE", "DELAYED", "STALE"].includes(ctx.status)) {
    return (
      <div className="dd-card muted">
        {ctx?.message ?? "하락 맥락 데이터를 불러오지 못했어요."}
      </div>
    );
  }

  const dd = ctx.currentDrawdownPct;
  const allRecovered =
    ctx.comparableCount > 0 && ctx.recoveredCount === ctx.comparableCount;

  return (
    <div className="dd-card">
      <div className="dd-head">
        <span className="dd-sym">
          {ctx.symbol}
          <span
            className="gloss"
            title={AXIS_GUIDE.find((g) => g.title === "기저율")?.text}
          >
            <sup className="gloss-i">ⓘ</sup>
          </span>
        </span>
        <span className="dd-dd">
          고점 대비 {dd == null ? "—" : `${dd.toFixed(1)}%`}
        </span>
      </div>

      {ctx.limitedHistory || ctx.comparableCount === 0 ? (
        <div className="dd-body muted">
          이력이 짧아({ctx.historyYears ?? "?"}년) 과거 비교는 참고만 하세요. 거짓
          안심은 드리지 않을게요.
        </div>
      ) : (
        <div className="dd-body">
          지난 <b>{ctx.historyYears?.toFixed(0)}년</b> 동안{" "}
          {ctx.thresholdPct?.toFixed(0)}% 이상 조정이 <b>{ctx.comparableCount}번</b>{" "}
          있었고,{" "}
          <b className={allRecovered ? "up" : ""}>{ctx.recoveredCount}번 회복</b>
          했어요{ctx.comparableCount > ctx.recoveredCount && " (1건은 진행 중)"}.
          <div className="dd-stats">
            <span>
              <Term k="baserate">
                <span className="k">회복 소요</span>
              </Term>{" "}
              {recoveryLabel(ctx.medianRecoveryDays)}
              {ctx.maxRecoveryDays != null && (
                <span className="muted">
                  {" "}
                  (최대 {recoveryLabel(ctx.maxRecoveryDays)})
                </span>
              )}
            </span>
            <span>
              <span className="k">역대 최악</span> {ctx.worstDrawdownPct?.toFixed(0)}%
            </span>
          </div>
        </div>
      )}

      {ctx.note && <div className="dd-note">⚠ {ctx.note}</div>}
      <div className="dd-disclaimer">과거 기록이지 미래 보장이 아닙니다.</div>
    </div>
  );
}
