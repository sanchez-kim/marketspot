import { useEffect, useState } from "react";
import { TOUR_STEPS } from "../lib/tourSteps";
import { useUIStore } from "../store/uiStore";

interface TourProps {
  onFinish: () => void;
}

export function Tour({ onFinish }: TourProps) {
  const { tourOpen, endTour, setTab } = useUIStore();
  const [step, setStep] = useState(0);
  const s = TOUR_STEPS[step];

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

  if (!tourOpen || !s) return null;

  const last = step === TOUR_STEPS.length - 1;

  // Best-effort highlight positioning via selector
  let bubbleStyle: React.CSSProperties = {};
  if (s.selector) {
    const el = document.querySelector(s.selector);
    if (el) {
      const rect = el.getBoundingClientRect();
      if (rect.width > 0 || rect.height > 0) {
        // Position bubble below the target element, horizontally centred
        const bubbleW = 340;
        const left = Math.min(
          Math.max(rect.left + rect.width / 2 - bubbleW / 2, 16),
          window.innerWidth - bubbleW - 16,
        );
        bubbleStyle = {
          position: "fixed",
          top: rect.bottom + 12,
          left,
          transform: "none",
        };
      }
    }
  }

  const finish = () => {
    endTour();
    onFinish();
  };

  const skip = () => endTour();

  return (
    <div className="tour-overlay" role="dialog" aria-label="시작 안내">
      <div className="tour-bubble" style={bubbleStyle}>
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
