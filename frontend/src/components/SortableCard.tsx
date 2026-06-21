import type { ReactNode } from "react";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";

interface Props {
  id: string;
  label: string;
  editMode: boolean;
  onHide: (id: string) => void;
  children: ReactNode;
}

/** 편집 모드에서 드래그 핸들 + 숨기기 바를 붙인 카드 래퍼. */
export function SortableCard({ id, label, editMode, onHide, children }: Props) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id, disabled: !editMode });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div ref={setNodeRef} style={style} className="dash-card">
      {editMode && (
        <div className="dash-bar">
          <span className="dash-handle" {...attributes} {...listeners}>
            ⠿ {label}
          </span>
          <button className="dash-hide" onClick={() => onHide(id)}>
            숨기기
          </button>
        </div>
      )}
      {children}
    </div>
  );
}
