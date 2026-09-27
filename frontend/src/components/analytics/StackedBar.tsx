interface Segment {
  label: string;
  value: number; // percentage (segments should sum to ~100)
  color: string;
}

interface Props {
  segments: Segment[];
  showLegend?: boolean;
}

// 100% stacked bar from flex divs + legend. A 2px surface gap sits between
// segments (matching the mark-spec spacer rule) via a thin white border.
export function StackedBar({ segments, showLegend = true }: Props) {
  const total = segments.reduce((sum, s) => sum + s.value, 0) || 1;
  return (
    <div>
      <div className="flex w-full h-6 rounded-md overflow-hidden bg-gray-100">
        {segments.map((s) =>
          s.value > 0 ? (
            <div
              key={s.label}
              className="h-full border-r-2 border-white last:border-r-0"
              style={{ width: `${(s.value / total) * 100}%`, backgroundColor: s.color }}
              title={`${s.label}: ${s.value.toFixed(0)}%`}
            />
          ) : null,
        )}
      </div>
      {showLegend && (
        <ul className="flex flex-wrap gap-x-4 gap-y-1 mt-3">
          {segments.map((s) => (
            <li key={s.label} className="flex items-center gap-2 text-sm">
              <span
                className="inline-block w-3 h-3 rounded-sm shrink-0"
                style={{ backgroundColor: s.color }}
              />
              <span className="text-gray-700 capitalize">{s.label}</span>
              <span className="text-gray-400 tabular-nums">{s.value.toFixed(0)}%</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
