import type { DataStatus } from "../api/types";
import { statusHint, statusMeta } from "../lib/format";

interface Props {
  status: DataStatus;
  delayMinutes?: number | null;
  source?: string;
}

/**
 * 모든 데이터 표시 지점에 붙는 상태 뱃지.
 * 가짜 데이터 금지 원칙을 UI 에서 강제한다(REQUIREMENTS §3).
 * title 은 소스 문자열이 아니라 "무슨 뜻인지"를 보여준다(§0 정직성) —
 * 초보자가 "호출 제한"/"오류"/"갱신지연"만 보고 앱이 고장났다고 오해하지 않도록.
 */
export function DataStatusBadge({ status, delayMinutes, source }: Props) {
  const meta = statusMeta(status, delayMinutes);
  const hint = statusHint(status);
  const title = source ? `${hint} (출처: ${source})` : hint;
  return (
    <span className={`status-badge tone-${meta.tone}`} title={title}>
      {meta.label}
    </span>
  );
}
