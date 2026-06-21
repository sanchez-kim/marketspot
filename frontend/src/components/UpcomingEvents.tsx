import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { useSettings } from "../hooks/useSettings";
import { useUIStore } from "../store/uiStore";

const TYPE_LABEL: Record<string, string> = {
  earnings: "실적 발표",
  exDividend: "배당락",
};

function dateLabel(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("ko-KR", { month: "long", day: "numeric" });
}

/** 다가오는 일정 — 내 종목 실적·배당락. '놀랄 일 없게'. */
export function UpcomingEvents() {
  const { setSymbol, setTab } = useUIStore();
  const settings = useSettings();
  const watchlist = settings.data?.watchlist ?? [];

  const events = useQuery({
    queryKey: ["calendar", watchlist],
    queryFn: () => api.calendar(watchlist, 6),
    enabled: watchlist.length > 0,
    staleTime: 30 * 60 * 1000,
  });

  if (watchlist.length === 0) return null;
  const list = events.data ?? [];

  return (
    <div className="events">
      <div className="events-title">다가오는 일정</div>
      {events.isLoading && <div className="muted">불러오는 중…</div>}
      {events.data && list.length === 0 && (
        <div className="muted">예정된 실적·배당 일정이 없어요.</div>
      )}
      {list.map((e, i) => (
        <div className="event-row" key={`${e.symbol}-${e.type}-${i}`}>
          <button
            className="event-sym"
            onClick={() => {
              setSymbol(e.symbol);
              setTab("symbol");
            }}
          >
            {e.symbol}
          </button>
          <span className="event-type">{TYPE_LABEL[e.type] ?? e.type}</span>
          <span className="event-date muted">{dateLabel(e.date)}</span>
        </div>
      ))}
    </div>
  );
}
