import { useLayoutEffect, useRef, useState } from "react";

interface Props {
  text: string;
  lines?: number;
}

/**
 * Long prose truncated to a few lines, with "View all" to expand.
 *
 * The toggle only appears when the text actually overflows — measured after
 * layout rather than guessed from character count, since wrapping depends on
 * the panel width, which the user can drag.
 */
export function ClampedText({ text, lines = 3 }: Props) {
  const [expanded, setExpanded] = useState(false);
  const [overflowing, setOverflowing] = useState(false);
  const ref = useRef<HTMLParagraphElement>(null);

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;

    function measure() {
      if (!el) return;
      setOverflowing(el.scrollHeight > el.clientHeight + 1);
    }

    // Re-measure when the panel is resized, or the clamp could be stale.
    const observer = new ResizeObserver(measure);
    observer.observe(el);
    measure();
    return () => observer.disconnect();
  }, [text, lines, expanded]);

  return (
    <div>
      <p
        ref={ref}
        className="whitespace-pre-line text-sm leading-relaxed text-gray-700"
        style={
          expanded
            ? undefined
            : {
                display: "-webkit-box",
                WebkitBoxOrient: "vertical",
                WebkitLineClamp: lines,
                overflow: "hidden",
              }
        }
      >
        {text}
      </p>
      {(overflowing || expanded) && (
        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          className="mt-1 text-xs text-blue-600 hover:underline"
        >
          {expanded ? "Show less" : "View all"}
        </button>
      )}
    </div>
  );
}
