import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";

interface Props {
  onSelect: (symbol: string) => void;
  placeholder?: string;
  autoFocus?: boolean;
}

/**
 * 심볼 검색 자동완성. 입력하면 연관 종목이 드롭다운으로 나오고, 클릭 또는
 * ↑/↓ + Enter 로 선택한다. 잘못된 코드를 직접 추가하지 못하도록 **목록에서
 * 고른 종목만** onSelect 된다(빈 결과면 추가 불가).
 */
export function SymbolSearch({ onSelect, placeholder, autoFocus }: Props) {
  const [text, setText] = useState("");
  const [debounced, setDebounced] = useState("");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const boxRef = useRef<HTMLDivElement | null>(null);

  // 입력 디바운스(250ms) — 타이핑 중 매 글자 요청 방지
  useEffect(() => {
    const t = setTimeout(() => setDebounced(text.trim()), 250);
    return () => clearTimeout(t);
  }, [text]);

  const results = useQuery({
    queryKey: ["search", debounced],
    queryFn: () => api.search(debounced, 8),
    enabled: debounced.length >= 1,
    staleTime: 60_000,
  });
  const items = results.data ?? [];

  // 바깥 클릭 시 닫기
  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  const choose = (symbol: string) => {
    onSelect(symbol);
    setText("");
    setDebounced("");
    setOpen(false);
    setActive(0);
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!open || items.length === 0) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((a) => Math.min(a + 1, items.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((a) => Math.max(a - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      const m = items[active];
      if (m) choose(m.symbol);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  };

  const showList = open && debounced.length >= 1 && items.length > 0;

  return (
    <div className="symsearch" ref={boxRef}>
      <input
        className="wl-input"
        placeholder={placeholder ?? "종목 검색 (예: PLTR)"}
        value={text}
        autoFocus={autoFocus}
        onChange={(e) => {
          setText(e.target.value);
          setOpen(true);
          setActive(0);
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={onKeyDown}
      />
      {showList && (
        <ul className="symsearch-list">
          {items.map((m, i) => (
            <li
              key={m.symbol}
              className={i === active ? "active" : ""}
              onMouseEnter={() => setActive(i)}
              // mousedown + preventDefault: input blur 보다 먼저 선택 처리
              onMouseDown={(e) => {
                e.preventDefault();
                choose(m.symbol);
              }}
            >
              <span className="ss-sym">{m.symbol}</span>
              <span className="ss-name">{m.name}</span>
              <span className="ss-meta">
                {m.type === "ETF" ? "ETF" : ""} {m.exchange ?? ""}
              </span>
            </li>
          ))}
        </ul>
      )}
      {open && debounced.length >= 1 && !results.isFetching && items.length === 0 && (
        <ul className="symsearch-list">
          <li className="ss-empty">검색 결과가 없습니다</li>
        </ul>
      )}
    </div>
  );
}
