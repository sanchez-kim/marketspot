import { useEffect, useRef } from "react";
import {
  ColorType,
  createChart,
  LineStyle,
  type IChartApi,
  type ISeriesApi,
  type Time,
} from "lightweight-charts";
import type { Bar, ChartData } from "../api/types";

interface Props {
  chart: ChartData;
  upColor: "green" | "red";
  showIndicators: boolean; // 탐구 모드: RSI/MACD 서브패널 표시
}

const COLORS = {
  green: { up: "#16c784", down: "#ea3943" },
  red: { up: "#ea3943", down: "#2196f3" },
};
const MA_COLORS: Record<string, string> = {
  "20": "#3b82f6",
  "50": "#e3a008",
  "200": "#a855f7",
};
const SCALE_WIDTH = 64; // 차트들의 가격축 폭을 맞춰 시간축을 정렬

function toTime(iso: string): Time {
  return iso.slice(0, 10) as Time;
}

type LinePoint = { time: Time; value: number };
type HistPoint = { time: Time; value: number; color: string };

function linePoints(bars: Bar[], series: (number | null)[]): LinePoint[] {
  const out: LinePoint[] = [];
  bars.forEach((b, i) => {
    const v = series[i];
    if (v != null) out.push({ time: toTime(b.time), value: v });
  });
  return out;
}

function histPoints(
  bars: Bar[],
  series: (number | null)[],
  pos: string,
  neg: string,
): HistPoint[] {
  const out: HistPoint[] = [];
  bars.forEach((b, i) => {
    const v = series[i];
    if (v != null) {
      out.push({ time: toTime(b.time), value: v, color: v >= 0 ? pos : neg });
    }
  });
  return out;
}

function baseOptions(showTimeAxis: boolean) {
  return {
    layout: {
      background: { type: ColorType.Solid, color: "#161b22" },
      textColor: "#9aa6b2",
    },
    grid: {
      vertLines: { color: "#22272e" },
      horzLines: { color: "#22272e" },
    },
    rightPriceScale: { borderColor: "#2a3038", minimumWidth: SCALE_WIDTH },
    timeScale: { borderColor: "#2a3038", visible: showTimeAxis },
    autoSize: true,
  };
}

interface ChartRefs {
  charts: IChartApi[];
  candle?: ISeriesApi<"Candlestick">;
  volume?: ISeriesApi<"Histogram">;
  price?: IChartApi;
  mas: ISeriesApi<"Line">[];
  rsiLine?: ISeriesApi<"Line">;
  macdHist?: ISeriesApi<"Histogram">;
  macdLine?: ISeriesApi<"Line">;
  macdSignal?: ISeriesApi<"Line">;
}

/**
 * 차분 모드: 가격(캔들+거래량+MA)만. 탐구 모드: + RSI/MACD 서브패널(시간축 동기화).
 * lightweight-charts v4 는 멀티 페인이 없어 차트 인스턴스를 세로로 쌓는다.
 */
export function CandleChart({ chart, upColor, showIndicators }: Props) {
  const priceHost = useRef<HTMLDivElement | null>(null);
  const rsiHost = useRef<HTMLDivElement | null>(null);
  const macdHost = useRef<HTMLDivElement | null>(null);
  const refs = useRef<ChartRefs>({ charts: [], mas: [] });

  // 차트 인스턴스 생성 + (탐구 모드면) 시간축 동기화. 모드 변경 시 재생성.
  useEffect(() => {
    const ph = priceHost.current;
    if (!ph) return;

    // 차분 모드면 가격 차트가 날짜축을 가진다(맨 아래). 탐구 모드면 MACD 가 가진다.
    const price = createChart(ph, baseOptions(!showIndicators));
    const candle = price.addCandlestickSeries();
    const volume = price.addHistogramSeries({
      priceScaleId: "vol",
      priceFormat: { type: "volume" },
    });
    price.priceScale("vol").applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });

    const newRefs: ChartRefs = { charts: [price], candle, volume, price, mas: [] };

    const rh = rsiHost.current;
    const mh = macdHost.current;
    if (showIndicators && rh && mh) {
      const rsi = createChart(rh, baseOptions(false));
      const macd = createChart(mh, baseOptions(true));

      const rsiLine = rsi.addLineSeries({
        color: "#a855f7",
        lineWidth: 1,
        priceLineVisible: false,
        autoscaleInfoProvider: () => ({ priceRange: { minValue: 0, maxValue: 100 } }),
      });
      rsiLine.createPriceLine({
        price: 70,
        color: "#ea394366",
        lineWidth: 1,
        lineStyle: LineStyle.Dashed,
        axisLabelVisible: true,
        title: "과매수 70",
      });
      rsiLine.createPriceLine({
        price: 30,
        color: "#16c78466",
        lineWidth: 1,
        lineStyle: LineStyle.Dashed,
        axisLabelVisible: true,
        title: "과매도 30",
      });
      rsi.priceScale("right").applyOptions({ scaleMargins: { top: 0.1, bottom: 0.1 } });
      macd
        .priceScale("right")
        .applyOptions({ scaleMargins: { top: 0.15, bottom: 0.15 } });

      newRefs.rsiLine = rsiLine;
      newRefs.macdHist = macd.addHistogramSeries({
        priceLineVisible: false,
        lastValueVisible: false,
      });
      newRefs.macdLine = macd.addLineSeries({
        color: "#3b82f6",
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
      });
      newRefs.macdSignal = macd.addLineSeries({
        color: "#e3a008",
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
      });
      newRefs.charts.push(rsi, macd);
    }

    refs.current = newRefs;

    // 시간축 동기화(차트가 2개 이상일 때만 의미)
    const charts = newRefs.charts;
    let syncing = false;
    for (const src of charts) {
      src.timeScale().subscribeVisibleLogicalRangeChange((range) => {
        if (syncing || !range) return;
        syncing = true;
        for (const tgt of charts) {
          if (tgt !== src) tgt.timeScale().setVisibleLogicalRange(range);
        }
        syncing = false;
      });
    }

    return () => {
      for (const c of charts) c.remove();
      refs.current = { charts: [], mas: [] };
    };
  }, [showIndicators]);

  // 데이터 변경(또는 모드 변경 후 재생성) 시 시리즈 갱신
  useEffect(() => {
    const r = refs.current;
    if (!r.price || !r.candle || !r.volume) return;
    const pal = COLORS[upColor];
    const ind = chart.indicators;

    r.candle.applyOptions({
      upColor: pal.up,
      downColor: pal.down,
      wickUpColor: pal.up,
      wickDownColor: pal.down,
      borderVisible: false,
    });
    r.candle.setData(
      chart.bars.map((b) => ({
        time: toTime(b.time),
        open: b.open,
        high: b.high,
        low: b.low,
        close: b.close,
      })),
    );
    r.volume.setData(
      chart.bars.map((b) => ({
        time: toTime(b.time),
        value: b.volume ?? 0,
        color: b.close >= b.open ? `${pal.up}55` : `${pal.down}55`,
      })),
    );

    for (const s of r.mas) r.price.removeSeries(s);
    r.mas = [];
    for (const [period, series] of Object.entries(ind.ma)) {
      const line = r.price.addLineSeries({
        color: MA_COLORS[period] ?? "#888",
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
      });
      line.setData(linePoints(chart.bars, series));
      r.mas.push(line);
    }

    if (r.rsiLine) r.rsiLine.setData(linePoints(chart.bars, ind.rsi));
    if (r.macdHist && r.macdLine && r.macdSignal) {
      r.macdHist.setData(
        histPoints(chart.bars, ind.macdHist, `${pal.up}99`, `${pal.down}99`),
      );
      r.macdLine.setData(linePoints(chart.bars, ind.macd));
      r.macdSignal.setData(linePoints(chart.bars, ind.macdSignal));
    }

    r.price.timeScale().fitContent();
  }, [chart, upColor, showIndicators]);

  return (
    <div className="chart-stack">
      <div className="chart-host price" ref={priceHost} />
      {showIndicators && (
        <>
          <div className="chart-sub">
            <span className="sub-label">RSI(14)</span>
            <div className="chart-host" ref={rsiHost} />
          </div>
          <div className="chart-sub">
            <span className="sub-label">MACD (12·26·9)</span>
            <div className="chart-host" ref={macdHost} />
          </div>
        </>
      )}
    </div>
  );
}
