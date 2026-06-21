import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useSettings, useUpdateSettings } from "../hooks/useSettings";

// 백엔드 RULE_LABELS 와 키를 맞춘다.
const RULES: { key: string; label: string }[] = [
  { key: "buy_monthly", label: "매달 적립한다" },
  { key: "no_sell_on_dip", label: "하락해도 팔지 않는다" },
  { key: "ignore_timing", label: "타이밍을 재지 않는다" },
  { key: "long_term", label: "장기 보유한다" },
];
const LABEL: Record<string, string> = Object.fromEntries(
  RULES.map((r) => [r.key, r.label]),
);

/**
 * 투자원칙 카드 — 한 번 선언하면 홈 평결이 *내 계획 기준*으로 말한다.
 * (DESIGN §0: Meadows 규칙 레버리지 — 흔들릴 때 자기 약속을 되비춤.)
 */
export function PlanCard() {
  const settings = useSettings();
  const update = useUpdateSettings();
  const qc = useQueryClient();
  const plan = settings.data?.plan;

  const [editing, setEditing] = useState(false);
  const [rules, setRules] = useState<string[]>([]);
  const [monthly, setMonthly] = useState("");

  if (!plan) return null;

  const startEdit = () => {
    setRules(plan.rules);
    setMonthly(plan.monthlyContribution ? String(plan.monthlyContribution) : "");
    setEditing(true);
  };

  const toggleRule = (key: string) =>
    setRules((rs) => (rs.includes(key) ? rs.filter((r) => r !== key) : [...rs, key]));

  const save = () => {
    update.mutate(
      { plan: { rules, monthlyContribution: Number(monthly) || 0 } },
      { onSuccess: () => qc.invalidateQueries({ queryKey: ["home"] }) },
    );
    setEditing(false);
  };

  if (editing) {
    return (
      <div className="plan-card">
        <div className="plan-head">
          <span className="plan-title">투자원칙 정하기</span>
        </div>
        <div className="plan-rules">
          {RULES.map((r) => (
            <label key={r.key} className="plan-check">
              <input
                type="checkbox"
                checked={rules.includes(r.key)}
                onChange={() => toggleRule(r.key)}
              />
              {r.label}
            </label>
          ))}
        </div>
        <div className="plan-monthly">
          월 적립액(선택)
          <input
            className="wl-input"
            inputMode="decimal"
            placeholder="예: 500000"
            value={monthly}
            onChange={(e) => setMonthly(e.target.value)}
          />
        </div>
        <div className="plan-actions">
          <button className="icon-btn" onClick={save} disabled={update.isPending}>
            저장
          </button>
          <button className="plan-cancel" onClick={() => setEditing(false)}>
            취소
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="plan-card">
      <div className="plan-head">
        <span className="plan-title">내 투자원칙</span>
        <button className="plan-edit" onClick={startEdit}>
          {plan.rules.length > 0 ? "✎ 수정" : "정하기"}
        </button>
      </div>
      {plan.rules.length === 0 ? (
        <div className="muted">
          원칙을 정하면 평결이 당신 계획 기준으로 말해줘요 (예: "하락에도 팔지 않기").
        </div>
      ) : (
        <div className="plan-chips">
          {plan.rules.map((k) => (
            <span key={k} className="plan-chip">
              {LABEL[k] ?? k}
            </span>
          ))}
          {plan.monthlyContribution > 0 && (
            <span className="plan-chip">
              월 {plan.monthlyContribution.toLocaleString("ko-KR")} 적립
            </span>
          )}
        </div>
      )}
    </div>
  );
}
