import { useEffect, useRef, useState } from "react";

interface Props {
  value: number | null;
  caption: string;
  // Decimal places for the displayed value (default 0).
  decimals?: number;
  suffix?: string;
  loading?: boolean;
}

// Count-up animation via requestAnimationFrame (one of the four agreed motions).
function useCountUp(target: number | null, decimals: number): number {
  const [display, setDisplay] = useState(0);
  const fromRef = useRef(0);

  useEffect(() => {
    if (target === null) return;
    const from = fromRef.current;
    const to = target;
    const duration = 500;
    let raf = 0;
    let start = 0;
    const factor = 10 ** decimals;

    function tick(ts: number) {
      if (!start) start = ts;
      const t = Math.min((ts - start) / duration, 1);
      const eased = 1 - (1 - t) ** 3; // ease-out cubic
      setDisplay(Math.round((from + (to - from) * eased) * factor) / factor);
      if (t < 1) raf = requestAnimationFrame(tick);
      else fromRef.current = to;
    }
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, decimals]);

  return display;
}

export function StatTile({ value, caption, decimals = 0, suffix, loading }: Props) {
  const display = useCountUp(value, decimals);
  return (
    <div className="flex flex-col">
      <span className="text-3xl font-bold text-gray-900 tabular-nums">
        {loading || value === null ? "—" : display.toFixed(decimals)}
        {!loading && value !== null && suffix ? (
          <span className="text-lg font-semibold text-gray-500 ml-0.5">{suffix}</span>
        ) : null}
      </span>
      <span className="text-xs text-gray-500 mt-1">{caption}</span>
    </div>
  );
}
