import { useCallback, useEffect, useRef, useState } from "react";

const MIN_WIDTH = 280;
const MAX_WIDTH = 720;
const DEFAULT_WIDTH = 384; // matches the old fixed w-96
const STORAGE_KEY = "govgraph.panelWidth";

function clamp(width: number) {
  return Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, width));
}

function initialWidth() {
  const stored = Number(localStorage.getItem(STORAGE_KEY));
  return stored ? clamp(stored) : DEFAULT_WIDTH;
}

/**
 * Right-hand detail panel with a drag handle on its left border.
 *
 * The graph beside it is `flex-1 min-w-0`, so it absorbs whatever width is left
 * over. The chosen width persists, since re-dragging it on every visit would be
 * tedious for anyone who prefers a wider panel.
 */
export function ResizablePanel({ children }: { children: React.ReactNode }) {
  const [width, setWidth] = useState(initialWidth);
  const [dragging, setDragging] = useState(false);
  const panelRef = useRef<HTMLElement>(null);

  const onPointerMove = useCallback((e: PointerEvent) => {
    const right = panelRef.current?.getBoundingClientRect().right ?? window.innerWidth;
    // Measure from the panel's right edge so the handle tracks the cursor
    // regardless of where the page is scrolled.
    setWidth(clamp(right - e.clientX));
  }, []);

  const stopDragging = useCallback(() => setDragging(false), []);

  useEffect(() => {
    if (!dragging) return;
    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", stopDragging);
    // Suppress text selection and cursor flicker while dragging over the graph.
    const previousUserSelect = document.body.style.userSelect;
    const previousCursor = document.body.style.cursor;
    document.body.style.userSelect = "none";
    document.body.style.cursor = "col-resize";

    return () => {
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerup", stopDragging);
      document.body.style.userSelect = previousUserSelect;
      document.body.style.cursor = previousCursor;
    };
  }, [dragging, onPointerMove, stopDragging]);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, String(width));
  }, [width]);

  return (
    <aside
      ref={panelRef}
      style={{ width }}
      className="relative flex shrink-0 flex-col overflow-hidden border-l border-gray-200 bg-white"
    >
      <div
        role="separator"
        aria-label="Resize panel"
        aria-orientation="vertical"
        tabIndex={0}
        onPointerDown={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        // Keyboard users get the same control, in 24px steps.
        onKeyDown={(e) => {
          if (e.key === "ArrowLeft") setWidth((w) => clamp(w + 24));
          if (e.key === "ArrowRight") setWidth((w) => clamp(w - 24));
        }}
        className={`absolute inset-y-0 left-0 z-10 w-1.5 cursor-col-resize hover:bg-blue-200 ${
          dragging ? "bg-blue-300" : ""
        }`}
      />
      {children}
    </aside>
  );
}
