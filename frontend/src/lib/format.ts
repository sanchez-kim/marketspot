import type { DataStatus, Importance, Sentiment } from "../api/types";

// ── 데이터 상태 표시 (가짜 데이터 금지의 핵심) ─────────────────────
export interface StatusMeta {
  label: string;
  tone: "ok" | "warn" | "muted" | "error";
}

const STATUS_META: Record<DataStatus, StatusMeta> = {
  LIVE: { label: "실시간", tone: "ok" },
  DELAYED: { label: "지연", tone: "warn" },
  STALE: { label: "갱신지연", tone: "warn" },
  NO_DATA: { label: "데이터 없음", tone: "muted" },
  NEEDS_KEY: { label: "API 키 필요", tone: "warn" },
  RATE_LIMITED: { label: "호출 제한", tone: "warn" },
  ERROR: { label: "오류", tone: "error" },
};

export function statusMeta(
  status: DataStatus,
  delayMinutes?: number | null,
): StatusMeta {
  const base = STATUS_META[status];
  if (status === "DELAYED" && delayMinutes) {
    return { ...base, label: `${delayMinutes}분 지연` };
  }
  return base;
}

// ── 공유 포트폴리오 포맷터 ────────────────────────────────────────
// PortfolioTab(데스크톱 표)과 PositionCard(폰 카드)가 공유한다.
// 가짜 숫자 금지: null → "—", 부호 표기 포함.

export function num(v: number | null, digits = 2): string {
  return v == null
    ? "—"
    : v.toLocaleString("ko-KR", {
        minimumFractionDigits: digits,
        maximumFractionDigits: digits,
      });
}

export function qtyFmt(v: number): string {
  return v.toLocaleString("ko-KR", { maximumFractionDigits: 4 });
}

export function signed(v: number | null): string {
  if (v == null) return "—";
  return `${v > 0 ? "+" : ""}${num(v)}`;
}

// ── 숫자 포맷 ──────────────────────────────────────────────────────
export function formatPrice(value: number): string {
  return value.toLocaleString("ko-KR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function formatPct(value: number | null): string {
  if (value === null) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}%`;
}

export function formatChange(value: number | null): string {
  if (value === null) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${formatPrice(value)}`;
}

// 상승/하락 색상 클래스 (upColor 설정에 따라 의미가 바뀜)
export function changeClass(value: number | null): "up" | "down" | "flat" {
  if (value === null || value === 0) return "flat";
  return value > 0 ? "up" : "down";
}

// ── 뉴스 감성/중요도/AI 백엔드 표시 ────────────────────────────────
export function sentimentMeta(s: Sentiment): { label: string; cls: string } {
  switch (s) {
    case "POSITIVE":
      return { label: "강세", cls: "up" };
    case "NEGATIVE":
      return { label: "약세", cls: "down" };
    default:
      return { label: "중립", cls: "flat" };
  }
}

export function importanceLabel(i: Importance): string {
  return i === "HIGH" ? "중요" : i === "MEDIUM" ? "보통" : "낮음";
}

// ── 공시(SEC) 서식 설명 ────────────────────────────────────────────
// 표준 SEC 서식 분류의 한국어 설명(번역이 아니라 용도 안내). 초보 투자자가
// 서식 코드만 보고도 무슨 공시인지 알 수 있게 돕는다. 매핑에 없으면 코드 그대로.
const FORM_GLOSS: Record<string, string> = {
  "10-K": "연차보고서(실적)",
  "10-Q": "분기보고서(실적)",
  "8-K": "수시공시(주요사건)",
  "4": "내부자 거래",
  "3": "내부자 지분 신고",
  "144": "내부자 매도 예고",
  SD: "분쟁광물 보고",
  "DEF 14A": "주주총회 안내",
  "S-1": "신규 상장 신고",
  "NPORT-P": "펀드 보유내역",
  "N-CSR": "펀드 연차보고",
  "497": "투자설명서",
  "497K": "투자설명서 요약",
  "485BPOS": "펀드 등록 갱신",
  "13F-HR": "기관 보유 현황",
};

export function formLabel(form: string): string {
  return FORM_GLOSS[form.toUpperCase()] ?? FORM_GLOSS[form] ?? form;
}

/**
 * STALE/지연 데이터의 나이를 "약 N분 전"으로. 데이터 실제 시각(asOf)에
 * 지연(delayMinutes)을 더해 과소표기하지 않는다(§0). asOf 없으면 null.
 */
export function staleAge(
  asOf: string | null,
  delayMinutes: number | null,
  nowMs: number = Date.now(),
): string | null {
  if (!asOf) return null;
  const elapsedMin = Math.max(0, (nowMs - Date.parse(asOf)) / 60000);
  const total = Math.round(elapsedMin + (delayMinutes ?? 0));
  if (total < 60) return `약 ${total}분 전`;
  const h = Math.floor(total / 60);
  return `약 ${h}시간 전`;
}

// AI 백엔드 라벨 — 어떤 엔진이 답했는지 정직하게 표시
export function backendLabel(backend: string): string {
  switch (backend) {
    case "ollama":
      return "Ollama 로컬 AI";
    case "gemini":
      return "Gemini";
    case "rule":
      return "규칙기반 (번역 아님)";
    default:
      return "없음";
  }
}
