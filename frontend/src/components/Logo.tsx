/** MarketSpot 로고 마크 — 차분한 상승 추세선 끝의 스팟(현물가+시장 흐름 포착). */
export function Logo({ size = 22 }: { size?: number }) {
  return (
    <svg
      className="logo-mark"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <polyline
        points="2.5,16.5 8.5,12 13.5,14 20,6.8"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.9"
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity="0.5"
      />
      <circle cx="20" cy="6.8" r="3" fill="currentColor" />
    </svg>
  );
}
