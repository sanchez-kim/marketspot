import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { changeClass, formatPct, formatPrice } from "../lib/format";
import { DataStatusBadge } from "./DataStatusBadge";

export function IndexStrip() {
  const { data, isLoading } = useQuery({
    queryKey: ["strip"],
    queryFn: api.strip,
    refetchInterval: 15_000, // 근실시간 갱신
  });

  if (isLoading || !data) {
    return (
      <div className="strip">
        <div className="strip-item">
          <span className="label">지수</span>
          <span className="value muted">불러오는 중…</span>
        </div>
      </div>
    );
  }

  return (
    <div className="strip">
      {data.map((item) => {
        const q = item.quote.data;
        return (
          <div className="strip-item" key={item.symbol}>
            <span className="label">{item.label}</span>
            {q ? (
              <span className={`value ${changeClass(q.changePct)}`}>
                {formatPrice(q.price)} {formatPct(q.changePct)}
              </span>
            ) : (
              <span className="value">
                <DataStatusBadge
                  status={item.quote.status}
                  delayMinutes={item.quote.delayMinutes}
                  source={item.quote.source}
                />
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}
