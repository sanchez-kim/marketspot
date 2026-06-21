import type { ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { useUIStore } from "../store/uiStore";
import { Term } from "./Term";

const HAS_DATA = ["LIVE", "DELAYED", "STALE"];

function bigUsd(v: number | null): string {
  if (v == null) return "—";
  if (v >= 1e12) return `${(v / 1e12).toFixed(2)}조 달러`;
  if (v >= 1e8) return `${(v / 1e8).toFixed(0)}억 달러`;
  return `$${v.toLocaleString("ko-KR")}`;
}
function pct(v: number | null): string {
  return v == null ? "—" : `${v.toFixed(2)}%`;
}
function num(v: number | null, d = 2): string {
  return v == null ? "—" : v.toLocaleString("ko-KR", { maximumFractionDigits: d });
}

function Metric({ label, value }: { label: ReactNode; value: string }) {
  return (
    <div className="fund-metric">
      <span className="k">{label}</span>
      <b>{value}</b>
    </div>
  );
}

/** '내가 산 게 뭔지' — 종목 기본정보(섹터·시총·PER·배당·ETF 보유). */
export function FundamentalsCard() {
  const { symbol, askAi } = useUIStore();
  const q = useQuery({
    queryKey: ["fundamentals", symbol],
    queryFn: () => api.fundamentals(symbol),
  });

  const f = q.data;
  if (q.isLoading) return <div className="muted">기본정보 불러오는 중…</div>;
  if (!f || !HAS_DATA.includes(f.status)) {
    return <div className="muted">{f?.message ?? "기본정보가 없습니다."}</div>;
  }

  const isEtf = f.type === "ETF";
  const subtitle = isEtf
    ? f.category
    : [f.sector, f.industry].filter(Boolean).join(" · ");
  const maxW = f.topHoldings[0]?.weight ?? 1;

  return (
    <div className="fund">
      <div className="fund-head">
        <div className="fund-title-wrap">
          <span className="fund-name">{f.name ?? f.symbol}</span>
          {f.type && <span className="fund-type">{isEtf ? "ETF" : "주식"}</span>}
          {subtitle && <span className="muted fund-sub">· {subtitle}</span>}
        </div>
        <button
          className="icon-btn"
          onClick={() =>
            askAi(
              `${f.name ?? symbol}(${symbol})은 어떤 ${isEtf ? "ETF" : "회사"}인지 초보도 알기 쉽게 한국어로 설명해줘.`,
            )
          }
        >
          ✦ 쉽게 설명
        </button>
      </div>

      {f.summary && (
        <div className="fund-summary">
          <span className="muted">사업 요약(원문)</span>
          <p>{f.summary}</p>
        </div>
      )}

      <div className="fund-metrics">
        {isEtf ? (
          <Metric label={<Term k="aum">순자산</Term>} value={bigUsd(f.totalAssets)} />
        ) : (
          <Metric label={<Term k="mcap">시가총액</Term>} value={bigUsd(f.marketCap)} />
        )}
        <Metric label={<Term k="per">PER</Term>} value={num(f.peRatio, 1)} />
        <Metric label={<Term k="div">배당수익률</Term>} value={pct(f.dividendYield)} />
        {f.beta != null && (
          <Metric label={<Term k="beta">베타</Term>} value={num(f.beta, 2)} />
        )}
        <Metric
          label={<Term k="w52">52주 범위</Term>}
          value={`${num(f.week52Low, 0)} ~ ${num(f.week52High, 0)}`}
        />
      </div>

      {f.topHoldings.length > 0 && (
        <div className="fund-holdings">
          <div className="muted fund-hold-title">
            <Term k="holdings">주요 보유종목</Term>
          </div>
          {f.topHoldings.slice(0, 8).map((h) => (
            <div className="alloc-row" key={h.name}>
              <span className="alloc-sym">{h.symbol ?? ""}</span>
              <span className="hold-name">{h.name}</span>
              <span className="alloc-bar">
                <span style={{ width: `${(h.weight / maxW) * 100}%` }} />
              </span>
              <span className="alloc-w">{h.weight.toFixed(1)}%</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
