import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import { useUIStore } from "../store/uiStore";

/**
 * 토스증권 연동 카드 — 미연동 시 설정 유도(기존 NEEDS_KEY 패턴), 연동 시
 * 계좌 선택·마지막 동기화·"지금 동기화" 버튼. 동기화 결과와 드리프트
 * 경고를 있는 그대로 보여준다(§0 정직성 — 숨기지 않음).
 */
export function TossCard() {
  const openSettings = useUIStore((s) => s.openSettings);
  const qc = useQueryClient();
  const [syncMessage, setSyncMessage] = useState<string | null>(null);

  const status = useQuery({
    queryKey: ["toss-status"],
    queryFn: api.tossStatus,
  });

  const setAccount = useMutation({
    mutationFn: api.setTossAccount,
    onSuccess: (env) => {
      qc.setQueryData(["toss-status"], env);
    },
  });

  const sync = useMutation({
    mutationFn: api.tossSync,
    onError: () => {
      // 네트워크 단절 등 트랜스포트 실패는 DataEnvelope 없이 예외로 온다 —
      // 조용히 버튼만 재활성화하지 않고 정직하게 실패를 알린다.
      setSyncMessage("동기화 요청에 실패했어요. 잠시 후 다시 시도하세요.");
    },
    onSuccess: (env) => {
      void qc.invalidateQueries({ queryKey: ["toss-status"] });
      void qc.invalidateQueries({ queryKey: ["portfolio"] });
      void qc.invalidateQueries({ queryKey: ["transactions"] });
      if (env.data) {
        const modeLabel = env.data.mode === "bootstrap" ? "최초 연동" : "증분";
        setSyncMessage(
          `${modeLabel} 동기화 완료 — 거래 ${env.data.added}건 추가${
            env.data.skippedUnpriced > 0
              ? ` (체결가 없어 ${env.data.skippedUnpriced}건 제외)`
              : ""
          }${env.message ? ` · ${env.message}` : ""}`,
        );
      } else {
        setSyncMessage(env.message ?? "동기화에 실패했어요.");
      }
    },
  });

  const data = status.data?.data;
  const envelope = status.data;

  if (status.isLoading) {
    return null;
  }

  if (!data) {
    return (
      <div className="pf-card">
        <div className="pf-card-head">
          <span className="pf-card-title">토스증권 연동</span>
        </div>
        {envelope?.status === "NEEDS_KEY" ? (
          <p className="ev-note ev-needskey">
            토스증권 계좌를 연동하면 보유 종목·거래내역이 자동으로 동기화돼요.{" "}
            <button className="link-inline" onClick={openSettings}>
              ⚙ 설정
            </button>
            에서 앱 키를 입력하세요.
          </p>
        ) : (
          <p className="ev-note">
            {envelope?.message ?? "토스 연동 상태를 불러오지 못했어요."}
          </p>
        )}
      </div>
    );
  }

  const drift = sync.data?.data?.drift ?? [];

  return (
    <div className="pf-card">
      <div className="pf-card-head">
        <span className="pf-card-title">토스증권 연동</span>
      </div>
      <div className="settings-field">
        <label htmlFor="toss-account-select">계좌</label>
        <select
          id="toss-account-select"
          value={data.selectedAccountSeq ?? ""}
          onChange={(e) => setAccount.mutate(e.target.value)}
        >
          <option value="" disabled>
            계좌 선택
          </option>
          {data.accounts.map((acc) => (
            <option key={acc.accountSeq} value={acc.accountSeq}>
              {acc.label}
            </option>
          ))}
        </select>
      </div>
      <p className="muted">
        마지막 동기화: {data.lastSync ?? "아직 동기화하지 않았어요"}
      </p>
      <button
        className="settings-save"
        disabled={!data.selectedAccountSeq || sync.isPending}
        onClick={() => sync.mutate()}
      >
        {sync.isPending ? "동기화 중…" : "지금 동기화"}
      </button>
      {syncMessage && <p className="ev-note">{syncMessage}</p>}
      {drift.length > 0 && (
        <div className="ev-note ev-needskey">
          <strong>잔고 불일치가 있어요(정직하게 표시):</strong>
          <ul>
            {drift.map((d) => (
              <li key={d.symbol}>
                {d.symbol}: 앱 {d.appQty}주 vs 토스 {d.tossQty}주
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
