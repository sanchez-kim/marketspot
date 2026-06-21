import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { importanceLabel, sentimentMeta } from "../lib/format";
import { useSettings } from "../hooks/useSettings";
import { useUIStore } from "../store/uiStore";

/**
 * 홈 "오늘 눈여겨볼 뉴스" — 관심종목 뉴스 중 중요한 것만 골라 AI 한국어 요약.
 * 스크롤 피드가 아니라 큐레이션된 인사이트(노이즈·불안 비증폭).
 */
export function HomeNews() {
  const { setSymbol, setTab } = useUIStore();
  const settings = useSettings();
  const watchlist = settings.data?.watchlist ?? [];

  const digest = useQuery({
    queryKey: ["newsDigest", watchlist],
    queryFn: () => api.newsDigest(watchlist, 6),
    enabled: watchlist.length > 0,
    staleTime: 10 * 60 * 1000,
  });

  if (watchlist.length === 0) return null;

  const items = digest.data?.items ?? [];

  const openSymbol = (ticker: string) => {
    setSymbol(ticker.toUpperCase());
    setTab("symbol");
  };

  return (
    <div className="digest">
      <div className="digest-head">
        <span className="digest-title">오늘 눈여겨볼 뉴스</span>
        {digest.data?.backend === "rule" && (
          <span className="muted digest-backend">규칙기반 (요약 아님)</span>
        )}
      </div>

      {digest.isLoading && <div className="muted">중요 뉴스 고르는 중…</div>}
      {digest.data && items.length === 0 && (
        <div className="muted">지금 눈여겨볼 만한 뉴스가 없어요.</div>
      )}

      {items.map((a) => {
        const sm = sentimentMeta(a.analysis.sentiment);
        return (
          <div className="digest-item" key={a.item.id}>
            <div className="digest-row">
              <span className={`sent-badge ${sm.cls}`}>
                {sm.label}·{importanceLabel(a.analysis.importance)}
              </span>
              <a href={a.item.link ?? "#"} target="_blank" rel="noreferrer">
                {a.item.title}
              </a>
            </div>
            <div className="digest-kr">{a.analysis.koreanSummary}</div>
            {a.analysis.tickers.length > 0 && (
              <div className="digest-tickers">
                {a.analysis.tickers.slice(0, 4).map((t) => (
                  <button key={t} className="ticker-chip" onClick={() => openSymbol(t)}>
                    {t}
                  </button>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
