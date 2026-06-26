import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { TOUR_STEPS } from "../lib/tourSteps";
import { placeBubble } from "../lib/tourPosition";
import { useUIStore } from "../store/uiStore";

interface TourProps {
  onFinish: () => void;
}

interface TargetRect {
  top: number;
  left: number;
  width: number;
  height: number;
}

export function Tour({ onFinish }: TourProps) {
  const { tourOpen, endTour, setTab, activeTab } = useUIStore();
  const [step, setStep] = useState(0);
  const s = TOUR_STEPS[step];
  const bubbleRef = useRef<HTMLDivElement>(null);
  const [pos, setPos] = useState<{ top: number; left: number } | null>(null);
  const [rect, setRect] = useState<TargetRect | null>(null);

  // Reset when the tour closes
  useEffect(() => {
    if (!tourOpen) {
      setStep(0);
      setRect(null);
      setPos(null);
    }
  }, [tourOpen]);

  // Esc key = skip
  useEffect(() => {
    if (!tourOpen) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") endTour();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [tourOpen, endTour]);

  // Switch tab if the step needs it, then highlight the target + place the
  // bubble (always kept on screen). Runs before paint (no flicker). Depends on
  // activeTab so it re-runs AFTER a tab switch, when the target is in the DOM.
  useLayoutEffect(() => {
    if (!tourOpen) return;
    const st = TOUR_STEPS[step];
    if (!st) return;
    if (st.tab && st.tab !== activeTab) {
      setTab(st.tab); // effect re-runs when activeTab updates
      return;
    }
    const bubble = bubbleRef.current;
    const el = st.selector ? document.querySelector(st.selector) : null;
    if (!el || !bubble) {
      setRect(null);
      setPos(null);
      return;
    }
    const r = el.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) {
      setRect(null);
      setPos(null);
      return;
    }
    setRect({ top: r.top, left: r.left, width: r.width, height: r.height });
    setPos(
      placeBubble(
        { top: r.top, bottom: r.bottom, left: r.left, width: r.width },
        bubble.offsetWidth,
        bubble.offsetHeight,
        window.innerWidth,
        window.innerHeight,
      ),
    );
  }, [tourOpen, step, activeTab, setTab]);

  if (!tourOpen || !s) return null;

  const last = step === TOUR_STEPS.length - 1;
  const finish = () => {
    endTour();
    onFinish();
  };
  const skip = () => endTour();

  const PAD = 6;

  return (
    <div className="tour-overlay" role="dialog" aria-label="시작 안내">
      {rect ? (
        // 스포트라이트: 대상에 링 + 큰 box-shadow 로 주변만 어둡게(대상은 또렷).
        <div
          className="tour-spotlight"
          style={{
            top: rect.top - PAD,
            left: rect.left - PAD,
            width: rect.width + PAD * 2,
            height: rect.height + PAD * 2,
          }}
        />
      ) : (
        // 대상이 없는 단계(환영/마무리)는 전체를 살짝 어둡게.
        <div className="tour-dim" />
      )}
      <div
        className="tour-bubble"
        ref={bubbleRef}
        style={
          pos
            ? { position: "fixed", top: pos.top, left: pos.left, transform: "none" }
            : undefined
        }
      >
        <div className="tour-title">{s.title}</div>
        <p className="tour-body">{s.body}</p>
        <div className="tour-foot">
          <span className="tour-progress">
            {step + 1}/{TOUR_STEPS.length}
          </span>
          <span className="tour-actions">
            <button className="tour-skip" onClick={skip}>
              건너뛰기
            </button>
            {step > 0 && <button onClick={() => setStep(step - 1)}>이전</button>}
            {last ? (
              <button onClick={finish}>완료</button>
            ) : (
              <button onClick={() => setStep(step + 1)}>다음</button>
            )}
          </span>
        </div>
      </div>
    </div>
  );
}
