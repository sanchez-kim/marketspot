import { useState } from "react";
import { useSettings, useUpdateSettings } from "../hooks/useSettings";
import { useUIStore } from "../store/uiStore";

/**
 * 설정 오버레이 — API 키 입력. 키 값은 마스킹(서버가 boolean 으로만 돌려줌)되어
 * 현재 "설정됨/미설정" 상태만 보여주고, 새 값 입력 시에만 갱신한다(빈칸=유지).
 */
export function SettingsPanel() {
  const settingsOpen = useUIStore((s) => s.settingsOpen);
  const closeSettings = useUIStore((s) => s.closeSettings);
  const settings = useSettings();
  const update = useUpdateSettings();
  const [fred, setFred] = useState("");
  const [dart, setDart] = useState("");
  const [saved, setSaved] = useState(false);

  if (!settingsOpen) return null;

  const keys = settings.data?.apiKeys ?? {};
  const status = (set: boolean) =>
    set ? (
      <span className="key-set">● 설정됨</span>
    ) : (
      <span className="key-unset">미설정</span>
    );

  const save = () => {
    const patch: Record<string, string> = {};
    if (fred.trim()) patch.fred = fred.trim();
    if (dart.trim()) patch.dart = dart.trim();
    if (Object.keys(patch).length === 0) return;
    update.mutate(
      { apiKeys: patch },
      {
        onSuccess: () => {
          setFred("");
          setDart("");
          setSaved(true);
        },
      },
    );
  };

  return (
    <div className="help-overlay" role="presentation" onClick={closeSettings}>
      <div
        className="settings-card"
        role="dialog"
        aria-modal="true"
        aria-label="설정"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="help-card-head">
          <span className="help-card-title">설정 · API 키</span>
          <button className="help-close" aria-label="닫기" onClick={closeSettings}>
            ✕
          </button>
        </div>

        <p className="settings-intro">
          일부 근거는 무료 API 키가 있어야 보여요. 키는 이 기기에만 저장되고 화면엔
          노출되지 않아요. 입력 후 저장하면 바로 반영돼요(빈칸은 그대로 유지).
        </p>

        <div className="settings-field">
          <label htmlFor="fred-key">
            FRED 키 <span className="settings-hint">거시 환경(금리·물가)</span>{" "}
            {status(!!keys.fred)}
          </label>
          <input
            id="fred-key"
            type="password"
            aria-label="FRED 키"
            placeholder={keys.fred ? "새 키 입력 (비우면 유지)" : "FRED API 키 입력"}
            value={fred}
            onChange={(e) => {
              setFred(e.target.value);
              setSaved(false);
            }}
          />
          <span className="settings-link">
            무료 발급: fredaccount.stlouisfed.org/apikeys
          </span>
        </div>

        <div className="settings-field">
          <label htmlFor="dart-key">
            DART 키 <span className="settings-hint">한국 종목 공시</span>{" "}
            {status(!!keys.dart)}
          </label>
          <input
            id="dart-key"
            type="password"
            aria-label="DART 키"
            placeholder={keys.dart ? "새 키 입력 (비우면 유지)" : "DART API 키 입력"}
            value={dart}
            onChange={(e) => {
              setDart(e.target.value);
              setSaved(false);
            }}
          />
          <span className="settings-link">무료 발급: opendart.fss.or.kr</span>
        </div>

        <p className="settings-note">
          AI 도우미(Ollama) 주소는 환경변수 <code>OLLAMA_HOST</code> 로 설정해요(기본
          http://localhost:11434).
        </p>

        <div className="settings-foot">
          {saved && <span className="settings-saved">저장됐어요 ✓</span>}
          <button
            className="settings-save"
            onClick={save}
            disabled={update.isPending || (!fred.trim() && !dart.trim())}
          >
            {update.isPending ? "저장 중…" : "저장"}
          </button>
        </div>
      </div>
    </div>
  );
}
