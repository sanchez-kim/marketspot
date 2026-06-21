interface Props {
  data: number[];
  width?: number;
  height?: number;
}

/** 가벼운 SVG 스파크라인 — 추세를 한눈에(상승=초록/하락=빨강, upColor 규칙 따름). */
export function Sparkline({ data, width = 60, height = 20 }: Props) {
  if (data.length < 2) return <span className="spark-empty" />;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const pts = data
    .map((v, i) => {
      const x = (i / (data.length - 1)) * width;
      const y = height - ((v - min) / range) * height;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  const cls = data[data.length - 1] >= data[0] ? "up" : "down";
  return (
    <svg className={`spark ${cls}`} width={width} height={height} aria-hidden="true">
      <polyline points={pts} fill="none" strokeWidth={1.3} />
    </svg>
  );
}
