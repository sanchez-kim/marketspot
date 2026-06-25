import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { TOUR_STEPS } from "../lib/tourSteps";
import { placeBubble } from "../lib/tourPosition";
import { useUIStore } from "../store/uiStore";

interface TourProps {
  onFinish: () => void;
}

export function Tour({ onFinish }: TourProps) {
  const { tourOpen, endTour, setTab } = useUIStore();
  const [step, setStep] = useState(0);
  const s = TOUR_STEPS[step];
  const bubbleRef = useRef<HTMLDivElement>(null);
  const [pos, setPos] = useState<{ top: number; left: number } | null>(null);

  // Switch tab when step specifies one
  useEffect(() => {
    if (tourOpen && s?.tab) setTab(s.tab);
  }, [tourOpen, step, s, setTab]);

  // Reset step index when tour closes
  useEffect(() => {
    if (!tourOpen) setStep(0);
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

  // Position the bubble near its target, always kept on screen. Measured after
  // render (useLayoutEffect → before paint, no flicker). No selector → centered.
  useLayoutEffect(() => {
    if (!tourOpen) return;
    const sel = TOUR_STEPS[step]?.selector;
    const bubble = bubbleRef.current;
    if (!sel || !bubble) {
      setPos(null);
      return;
    }
    const el = document.querySelector(sel);
    if (!el) {
      setPos(null);
      return;
    }
    const rect = el.getBoundingClientRect();
    if (rect.width === 0 && rect.height === 0) {
      setPos(null);
      return;
    }
    setPos(
      placeBubble(
        rect,
        bubble.offsetWidth,
        bubble.offsetHeight,
        window.innerWidth,
        window.innerHeight,
      ),
    );
  }, [tourOpen, step]);

  if (!tourOpen || !s) return null;

  const last = step === TOUR_STEPS.length - 1;

  const finish = () => {
    endTour();
    onFinish();
  };

  const skip = () => endTour();

  return (
    <div className="tour-overlay" role="dialog" aria-label="시작 안내">
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
