import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import type { AnalyzedNews, Importance } from "../api/types";
import { importanceLabel, sentimentMeta } from "../lib/format";
import { useUIStore } from "../store/uiStore";
import { DataStatusBadge } from "./DataStatusBadge";
import { Panel } from "./Panel";

const RANK: Record<Importance, number> = { HIGH: 0, MEDIUM: 1, LOW: 2 };

function timeLabel(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleString("ko-KR", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function NewsTab() {
  const { symbol } = useUIStore();

  const news = useQuery({
    queryKey: ["news", symbol],
    queryFn: () => api.news(symbol, 20),
    staleTime: 5 * 60 * 1000,
  });
  const env = news.data;
  const items = useMemo(() => env?.data ?? [], [env]);

  // ★ AI 요약을 자동 실행(버튼 없이) — 결과는 캐시되어 탭 전환에도 유지.
  const summarize = useQuery({
    queryKey: ["newsSummary", symbol],
    queryFn: () => api.summarizeNews(symbol, 12),
    enabled: items.length > 0,
    staleTime: 30 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
  });

  const analysisById = useMemo(() => {
    const map = new Map<string, AnalyzedNews>();
    summarize.data?.items.forEach((a) => map.set(a.item.id, a));
    return map;
  }, [summarize.data]);

  // 중요도순 정렬(HIGH 먼저). 요약 전/요약 안 된 항목은 뒤로(원래 순서 유지).
  const sorted = useMemo(() => {
    const rankOf = (id: string) => {
      const imp = analysisById.get(id)?.analysis.importance;
      return imp ? RANK[imp] : 3;
    };
    return [...items].sort((a, b) => rankOf(a.id) - rankOf(b.id));
  }, [items, analysisById]);

  return (
    <div style={{ height: "100%", padding: 12 }}>
      <Panel
        title={`뉴스 · ${symbol}`}
        right={
          summarize.isFetching ? (
            <span className="muted">AI 요약 중…</span>
          ) : summarize.data?.backend === "rule" ? (
            <span className="muted">규칙기반 (번역 아님)</span>
          ) : undefined
        }
      >
        {news.isLoading && <div className="muted">불러오는 중…</div>}
        {env && items.length === 0 && (
          <div className="empty-state">
            <DataStatusBadge status={env.status} source={env.source} />
            <span>{env.message ?? "뉴스가 없습니다"}</span>
          </div>
        )}

        {sorted.map((it) => {
          const analyzed = analysisById.get(it.id);
          const sm = analyzed ? sentimentMeta(analyzed.analysis.sentiment) : null;
          return (
            <div className="news-item" key={it.id}>
              <div className="news-head">
                {sm && (
                  <span className={`sent-badge ${sm.cls}`}>
                    {sm.label}·{importanceLabel(analyzed!.analysis.importance)}
                  </span>
                )}
                <a href={it.link ?? "#"} target="_blank" rel="noreferrer">
                  {it.title}
                </a>
              </div>
              <div className="news-meta">
                {it.publisher} · {timeLabel(it.published)}
              </div>
              {analyzed && (
                <div className="news-kr">{analyzed.analysis.koreanSummary}</div>
              )}
            </div>
          );
        })}
      </Panel>
    </div>
  );
}
