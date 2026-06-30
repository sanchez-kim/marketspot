import { useEffect, useState } from "react";

const QUERY = "(max-width: 640px)";

/**
 * 화면이 폰 너비(≤640px)인지 구독한다. 미디어쿼리 변경 시 리렌더.
 * 로컬 SPA라 SSR 고려는 불필요(초기값을 matchMedia 로 직접 읽음).
 */
export function useIsMobile(): boolean {
  const [isMobile, setIsMobile] = useState(() => window.matchMedia(QUERY).matches);

  useEffect(() => {
    const mql = window.matchMedia(QUERY);
    const onChange = (e: MediaQueryListEvent) => setIsMobile(e.matches);
    mql.addEventListener("change", onChange);
    // 마운트와 첫 effect 사이에 바뀌었을 수도 있으니 동기화.
    setIsMobile(mql.matches);
    return () => mql.removeEventListener("change", onChange);
  }, []);

  return isMobile;
}
