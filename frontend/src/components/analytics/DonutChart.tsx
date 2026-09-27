interface Slice {
  label: string;
  value: number; // percentage or raw count — arcs are normalised to the total
  color: string;
}

interface Props {
  slices: Slice[];
  size?: number;
  // Text shown in the donut hole (e.g. a total or the group's member count).
  centerLabel?: string;
  centerSub?: string;
}

// Inline-SVG donut using stroke-dasharray/dashoffset arcs. Handles an arbitrary
// number of categories. Identity is carried by the legend (never colour alone),
// which also satisfies the categorical palette's contrast-relief rule.
export function DonutChart({ slices, size = 180, centerLabel, centerSub }: Props) {
  const total = slices.reduce((sum, s) => sum + s.value, 0);
  const stroke = 22;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const cx = size / 2;
  const cy = size / 2;

  let offset = 0;

  return (
    <div className="flex items-center gap-6">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} role="img">
        <g transform={`rotate(-90 ${cx} ${cy})`}>
          {total > 0 &&
            slices.map((s) => {
              const frac = s.value / total;
              const dash = frac * circumference;
              const circle = (
                <circle
                  key={s.label}
                  cx={cx}
                  cy={cy}
                  r={radius}
                  fill="none"
                  stroke={s.color}
                  strokeWidth={stroke}
                  strokeDasharray={`${Math.max(dash - 2, 0)} ${circumference - Math.max(dash - 2, 0)}`}
                  strokeDashoffset={-offset}
                />
              );
              offset += dash;
              return circle;
            })}
        </g>
        {centerLabel && (
          <text
            x={cx}
            y={cy - 2}
            textAnchor="middle"
            className="fill-gray-900"
            style={{ fontSize: 22, fontWeight: 700 }}
          >
            {centerLabel}
          </text>
        )}
        {centerSub && (
          <text
            x={cx}
            y={cy + 16}
            textAnchor="middle"
            className="fill-gray-400"
            style={{ fontSize: 11 }}
          >
            {centerSub}
          </text>
        )}
      </svg>
      <ul className="space-y-1.5">
        {slices.map((s) => (
          <li key={s.label} className="flex items-center gap-2 text-sm">
            <span
              className="inline-block w-3 h-3 rounded-sm shrink-0"
              style={{ backgroundColor: s.color }}
            />
            <span className="text-gray-700 capitalize">{s.label}</span>
            <span className="text-gray-400 tabular-nums ml-1">
              {total > 0 ? ((s.value / total) * 100).toFixed(0) : 0}%
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
