import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { formLabel } from "../lib/format";
import { useUIStore } from "../store/uiStore";
import { DataStatusBadge } from "./DataStatusBadge";
import { Panel } from "./Panel";

function dateLabel(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleDateString("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
}

export function FilingsTab() {
  const { symbol } = useUIStore();

  const filings = useQuery({
    queryKey: ["filings", symbol],
    queryFn: () => api.filings(symbol, 30),
  });

  const env = filings.data;
  const list = env?.data;
  const items = list?.filings ?? [];

  return (
    <div style={{ height: "100%", padding: 12 }}>
      <Panel
        title={`공시 · ${symbol}`}
        right={
          env ? (
            <DataStatusBadge
              status={env.status}
              delayMinutes={env.delayMinutes}
              source={env.source}
            />
          ) : undefined
        }
      >
        {list && (
          <div className="ai-note">
            제출 주체: <b>{list.entity}</b>
            {list.cik && ` · CIK ${list.cik}`}
            {list.market === "US" && " · 출처 SEC EDGAR"}
          </div>
        )}

        {filings.isLoading && <div className="muted">불러오는 중…</div>}

        {env && items.length === 0 && (
          <div className="empty-state">
            <DataStatusBadge status={env.status} source={env.source} />
            <span>{env.message ?? "공시가 없습니다"}</span>
            {env.status === "NEEDS_KEY" && (
              <span className="muted">
                한국 공시(DART)는 설정에서 API 키를 입력해야 표시됩니다.
              </span>
            )}
          </div>
        )}

        {items.map((f) => (
          <div className="filing-item" key={f.accession || f.url}>
            <div className="filing-head">
              <span className="form-badge" title={f.form}>
                {formLabel(f.form)}
              </span>
              <a href={f.url} target="_blank" rel="noreferrer">
                {f.title}
              </a>
            </div>
            <div className="filing-meta">
              <span className="form-code">{f.form}</span>
              {" · 접수 "}
              {dateLabel(f.filed)}
              {f.reportDate && ` · 기준 ${dateLabel(f.reportDate)}`}
            </div>
          </div>
        ))}
      </Panel>
    </div>
  );
}
