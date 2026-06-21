import type { DataStatus } from "../api/types";
import { statusMeta } from "../lib/format";

interface Props {
  status: DataStatus;
  delayMinutes?: number | null;
  source?: string;
}

/**
 * 모든 데이터 표시 지점에 붙는 상태 뱃지.
 * 가짜 데이터 금지 원칙을 UI 에서 강제한다(REQUIREMENTS §3).
 */
export function DataStatusBadge({ status, delayMinutes, source }: Props) {
  const meta = statusMeta(status, delayMinutes);
  return (
    <span className={`status-badge tone-${meta.tone}`} title={source ?? undefined}>
      {meta.label}
    </span>
  );
}
