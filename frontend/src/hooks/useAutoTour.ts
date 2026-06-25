import { useEffect, useRef } from "react";
import { useUIStore } from "../store/uiStore";

/**
 * 최초 방문 자동 투어 트리거.
 * onboarded === false 일 때 startTour() 를 세션당 1회만 호출한다.
 * onboarded 가 undefined(로딩 중)이면 아무것도 하지 않는다.
 */
export function useAutoTour(onboarded: boolean | undefined) {
  const startTour = useUIStore((s) => s.startTour);
  const triggered = useRef(false);

  useEffect(() => {
    if (onboarded === false && !triggered.current) {
      triggered.current = true;
      startTour();
    }
  }, [onboarded, startTour]);
}
