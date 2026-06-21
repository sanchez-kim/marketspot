import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { INTERVALS, PERIODS } from "../api/types";
import { useUIStore } from "../store/uiStore";
import { CandleChart } from "./CandleChart";
import { DataStatusBadge } from "./DataStatusBadge";

function lastDefined(arr: (number | null)[]): number | null {
  for (let i = arr.length - 1; i >= 0; i--) {
    if (arr[i] != null) return arr[i];
  }
  return null;
}

function fmt(v: number | null, digits = 1): string {
  return v == null ? "—" : v.toFixed(digits);
}

export function ChartPanel() {
  const {
    symbol,
    period,
    interval,
    setPeriod,
    setInterval,
    upColor,
    exploreMode,
    toggleExplore,
  } = useUIStore();

  // ★ queryKey 에 period/interval 포함 → 변경 시 실제로 새 데이터 로드
  const { data, isLoading, isError } = useQuery({
    queryKey: ["chart", symbol, period, interval],
    queryFn: () => api.chart(symbol, period, interval),
  });

  const chart = data?.data ?? null;
  const ind = chart?.indicators;

  return (
    <div className="panel" style={{ height: "100%" }}>
      <div className="panel-header">
        <span className="panel-title">
          {symbol}{" "}
          {data && (
            <DataStatusBadge
              status={data.status}
              delayMinutes={data.delayMinutes}
              source={data.source}
            />
          )}
        </span>
        <div className="chart-controls">
          <div className="seg">
            {PERIODS.map((p) => (
              <button
                key={p}
                className={p === period ? "active" : ""}
                onClick={() => setPeriod(p)}
              >
                {p}
              </button>
            ))}
          </div>
          <div className="seg">
            {INTERVALS.map((iv) => (
              <button
                key={iv}
                className={iv === interval ? "active" : ""}
                onClick={() => setInterval(iv)}
              >
                {iv}
              </button>
            ))}
          </div>
          <button
            className={`icon-btn ${exploreMode ? "active" : ""}`}
            title="RSI/MACD 등 보조지표 보기"
            onClick={toggleExplore}
          >
            {exploreMode ? "차분히 보기" : "🔬 탐구 모드"}
          </button>
        </div>
      </div>
      <div className="panel-body" style={{ display: "flex", flexDirection: "column" }}>
        {ind && (
          <div className="metric-row" style={{ marginBottom: 8 }}>
            <span>
              <span className="k">MA20 </span>
              {fmt(lastDefined(ind.ma["20"] ?? []), 2)}
            </span>
            <span>
              <span className="k">MA50 </span>
              {fmt(lastDefined(ind.ma["50"] ?? []), 2)}
            </span>
            {exploreMode && (
              <>
                <span>
                  <span className="k">RSI(14) </span>
                  {fmt(lastDefined(ind.rsi))}
                </span>
                <span>
                  <span className="k">MACD </span>
                  {fmt(lastDefined(ind.macd), 2)}
                </span>
              </>
            )}
          </div>
        )}
        <div style={{ flex: 1, minHeight: 0 }}>
          {isLoading && <div className="empty-state">불러오는 중…</div>}
          {isError && (
            <div className="empty-state">
              <span className="big">차트를 불러오지 못했습니다</span>
            </div>
          )}
          {!isLoading && !isError && !chart && data && (
            <div className="empty-state">
              <DataStatusBadge status={data.status} source={data.source} />
              <span>{data.message ?? "데이터가 없습니다"}</span>
            </div>
          )}
          {chart && (
            <CandleChart chart={chart} upColor={upColor} showIndicators={exploreMode} />
          )}
        </div>
      </div>
    </div>
  );
}
