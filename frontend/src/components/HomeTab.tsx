import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  DndContext,
  PointerSensor,
  closestCorners,
  useDroppable,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragOverEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  arrayMove,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { api } from "../api/client";
import type { DashboardLayout } from "../api/types";
import { useSettings, useUpdateSettings } from "../hooks/useSettings";
import { DrawdownCard } from "./DrawdownCard";
import { HomeWatchlist } from "./HomeWatchlist";
import { HomeNews } from "./HomeNews";
import { PortfolioSummaryCard } from "./PortfolioSummaryCard";
import { PlanCard } from "./PlanCard";
import { MarketMood } from "./MarketMood";
import { UpcomingEvents } from "./UpcomingEvents";
import { LearnCard } from "./LearnCard";
import { SortableCard } from "./SortableCard";

const TONE_CLASS: Record<string, string> = {
  ON_TRACK: "v-ok",
  NORMAL_DIP: "v-calm",
  UNUSUAL: "v-warn",
  NO_HOLDINGS: "v-muted",
};
const TONE_ICON: Record<string, string> = {
  ON_TRACK: "✓",
  NORMAL_DIP: "≈",
  UNUSUAL: "!",
  NO_HOLDINGS: "+",
};

// 카드 레지스트리 — id → 라벨·요소·기본 열
type Col = "left" | "right";
const CARD_DEFS: { id: string; label: string; el: ReactNode; col: Col }[] = [
  { id: "plan", label: "투자원칙", el: <PlanCard />, col: "left" },
  {
    id: "portfolio",
    label: "포트폴리오 요약",
    el: <PortfolioSummaryCard />,
    col: "left",
  },
  { id: "watchlist", label: "관심종목", el: <HomeWatchlist />, col: "left" },
  { id: "mood", label: "시장 분위기", el: <MarketMood />, col: "right" },
  { id: "news", label: "오늘 눈여겨볼 뉴스", el: <HomeNews />, col: "right" },
  { id: "events", label: "다가오는 일정", el: <UpcomingEvents />, col: "right" },
  { id: "learn", label: "오늘의 배움", el: <LearnCard />, col: "right" },
];
const CARD_MAP = Object.fromEntries(CARD_DEFS.map((c) => [c.id, c]));

interface Cols {
  left: string[];
  right: string[];
}

// 저장된 레이아웃을 레지스트리와 맞춘다(모르는 id 제거, 누락 카드는 기본 열에 추가).
function reconcile(saved: DashboardLayout | undefined): {
  cols: Cols;
  hidden: string[];
} {
  const known = new Set(CARD_DEFS.map((c) => c.id));
  const left = (saved?.left ?? []).filter((id) => known.has(id));
  const right = (saved?.right ?? []).filter((id) => known.has(id));
  const hidden = (saved?.hidden ?? []).filter((id) => known.has(id));
  const placed = new Set([...left, ...right, ...hidden]);
  for (const c of CARD_DEFS) {
    if (!placed.has(c.id)) (c.col === "left" ? left : right).push(c.id);
  }
  return { cols: { left, right }, hidden };
}

function Column({
  id,
  ids,
  editMode,
  onHide,
}: {
  id: Col;
  ids: string[];
  editMode: boolean;
  onHide: (id: string) => void;
}) {
  const { setNodeRef } = useDroppable({ id });
  return (
    <div ref={setNodeRef} className="home-col">
      <SortableContext items={ids} strategy={verticalListSortingStrategy}>
        {ids.map((cid) => (
          <SortableCard
            key={cid}
            id={cid}
            label={CARD_MAP[cid].label}
            editMode={editMode}
            onHide={onHide}
          >
            {CARD_MAP[cid].el}
          </SortableCard>
        ))}
      </SortableContext>
    </div>
  );
}

export function HomeTab() {
  const home = useQuery({
    queryKey: ["home"],
    queryFn: api.home,
    refetchInterval: 60_000,
  });
  const settings = useSettings();
  const update = useUpdateSettings();

  const [cols, setCols] = useState<Cols>({ left: [], right: [] });
  const [hidden, setHidden] = useState<string[]>([]);
  const [editMode, setEditMode] = useState(false);
  const [activeId, setActiveId] = useState<string | null>(null);
  const initialized = useRef(false);
  const dirty = useRef(false);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
  );

  // 저장된 레이아웃 로드(최초 1회)
  useEffect(() => {
    if (initialized.current || !settings.data) return;
    const { cols: c, hidden: h } = reconcile(settings.data.dashboard);
    setCols(c);
    setHidden(h);
    initialized.current = true;
  }, [settings.data]);

  // 변경 사항 저장(드래그 중이 아닐 때만)
  useEffect(() => {
    if (!initialized.current || activeId || !dirty.current) return;
    dirty.current = false;
    update.mutate({ dashboard: { left: cols.left, right: cols.right, hidden } });
  }, [cols, hidden, activeId, update]);

  const findCol = (id: string): Col | null => {
    if (cols.left.includes(id)) return "left";
    if (cols.right.includes(id)) return "right";
    if (id === "left" || id === "right") return id;
    return null;
  };

  const onDragStart = (e: DragStartEvent) => setActiveId(String(e.active.id));

  const onDragOver = (e: DragOverEvent) => {
    const { active, over } = e;
    if (!over) return;
    const from = findCol(String(active.id));
    const to = findCol(String(over.id));
    if (!from || !to || from === to) return;
    setCols((prev) => {
      const fromItems = prev[from].filter((i) => i !== active.id);
      const toItems = prev[to].slice();
      const overIdx = toItems.indexOf(String(over.id));
      const insertAt = overIdx >= 0 ? overIdx : toItems.length;
      toItems.splice(insertAt, 0, String(active.id));
      return { ...prev, [from]: fromItems, [to]: toItems };
    });
  };

  const onDragEnd = (e: DragEndEvent) => {
    const { active, over } = e;
    setActiveId(null);
    dirty.current = true;
    if (!over) return;
    const from = findCol(String(active.id));
    const to = findCol(String(over.id));
    if (from && to && from === to) {
      const items = cols[from];
      const oldI = items.indexOf(String(active.id));
      const newI = items.indexOf(String(over.id));
      if (oldI !== newI && newI >= 0) {
        setCols((prev) => ({ ...prev, [from]: arrayMove(prev[from], oldI, newI) }));
      }
    }
  };

  const hide = (id: string) => {
    dirty.current = true;
    setCols((prev) => ({
      left: prev.left.filter((i) => i !== id),
      right: prev.right.filter((i) => i !== id),
    }));
    setHidden((prev) => [...prev, id]);
  };
  const show = (id: string) => {
    dirty.current = true;
    setHidden((prev) => prev.filter((i) => i !== id));
    const col = CARD_MAP[id].col;
    setCols((prev) => ({ ...prev, [col]: [...prev[col], id] }));
  };

  const v = home.data;

  return (
    <div className="home">
      <div className="home-topbar">
        <button
          className={`icon-btn ${editMode ? "active" : ""}`}
          onClick={() => setEditMode((e) => !e)}
        >
          {editMode ? "✓ 완료" : "✎ 편집"}
        </button>
      </div>

      {v && (
        <>
          <div className={`verdict ${TONE_CLASS[v.tone] ?? "v-muted"}`}>
            <div className="verdict-icon">{TONE_ICON[v.tone] ?? "•"}</div>
            <div className="verdict-text">
              <div className="verdict-head">{v.headline}</div>
              <div className="verdict-sub">{v.subline}</div>
              <div className="verdict-todo">{v.todo}</div>
            </div>
          </div>
          {v.context && <DrawdownCard ctx={v.context} />}
        </>
      )}

      {editMode && hidden.length > 0 && (
        <div className="dash-hidden">
          <span className="muted">숨긴 카드:</span>
          {hidden.map((id) => (
            <button key={id} className="chip" onClick={() => show(id)}>
              + {CARD_MAP[id].label}
            </button>
          ))}
        </div>
      )}

      <DndContext
        sensors={sensors}
        collisionDetection={closestCorners}
        onDragStart={onDragStart}
        onDragOver={onDragOver}
        onDragEnd={onDragEnd}
      >
        <div className="home-grid">
          <Column id="left" ids={cols.left} editMode={editMode} onHide={hide} />
          <Column id="right" ids={cols.right} editMode={editMode} onHide={hide} />
        </div>
      </DndContext>
    </div>
  );
}
