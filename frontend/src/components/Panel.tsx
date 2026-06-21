import type { ReactNode } from "react";

interface Props {
  title: string;
  right?: ReactNode;
  children: ReactNode;
}

export function Panel({ title, right, children }: Props) {
  return (
    <div className="panel">
      <div className="panel-header">
        <span className="panel-title">{title}</span>
        {right}
      </div>
      <div className="panel-body">{children}</div>
    </div>
  );
}
