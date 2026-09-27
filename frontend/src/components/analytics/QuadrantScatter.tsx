import { AXIS, GRIDLINE, INK_MUTED, PRIMARY } from "./palette";

export interface ScatterPoint {
  uuid: string;
  name: string;
  x: number;
  y: number;
}

interface Props {
  points: ScatterPoint[];
  xLabel: string;
  yLabel: string;
  // Labels for the four quadrants, clockwise from top-right.
  quadrantLabels?: { topRight: string; topLeft: string; bottomLeft: string; bottomRight: string };
}

function median(values: number[]): number {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

// SVG scatter with median crosshairs splitting the plane into four quadrants.
// Surfaces bodies that are heavy on both axes (top-right) — an insight neither
// underlying ranking gives alone. Single series, so one hue; each point is
// hover-labelled with its name/values.
export function QuadrantScatter({ points, xLabel, yLabel, quadrantLabels }: Props) {
  const width = 720;
  const height = 360;
  const pad = { top: 24, right: 24, bottom: 40, left: 48 };
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;

  const maxX = Math.max(...points.map((p) => p.x), 1);
  const maxY = Math.max(...points.map((p) => p.y), 1);
  const sx = (x: number) => pad.left + (x / maxX) * plotW;
  const sy = (y: number) => pad.top + plotH - (y / maxY) * plotH;

  const medX = median(points.map((p) => p.x));
  const medY = median(points.map((p) => p.y));

  return (
    <svg width="100%" viewBox={`0 0 ${width} ${height}`} role="img">
      {/* frame */}
      <rect
        x={pad.left}
        y={pad.top}
        width={plotW}
        height={plotH}
        fill="none"
        stroke={GRIDLINE}
      />
      {/* median crosshairs */}
      <line x1={sx(medX)} y1={pad.top} x2={sx(medX)} y2={pad.top + plotH} stroke={AXIS} strokeDasharray="4 4" />
      <line x1={pad.left} y1={sy(medY)} x2={pad.left + plotW} y2={sy(medY)} stroke={AXIS} strokeDasharray="4 4" />

      {/* quadrant labels */}
      {quadrantLabels && (
        <>
          <text x={pad.left + plotW - 6} y={pad.top + 14} textAnchor="end" style={{ fontSize: 10, fontWeight: 600 }} fill={INK_MUTED}>
            {quadrantLabels.topRight}
          </text>
          <text x={pad.left + 6} y={pad.top + 14} textAnchor="start" style={{ fontSize: 10 }} fill={INK_MUTED}>
            {quadrantLabels.topLeft}
          </text>
          <text x={pad.left + 6} y={pad.top + plotH - 6} textAnchor="start" style={{ fontSize: 10 }} fill={INK_MUTED}>
            {quadrantLabels.bottomLeft}
          </text>
          <text x={pad.left + plotW - 6} y={pad.top + plotH - 6} textAnchor="end" style={{ fontSize: 10 }} fill={INK_MUTED}>
            {quadrantLabels.bottomRight}
          </text>
        </>
      )}

      {/* points */}
      {points.map((p) => (
        <g key={p.uuid}>
          <circle cx={sx(p.x)} cy={sy(p.y)} r={5} fill={PRIMARY} fillOpacity={0.8} stroke="#fff" strokeWidth={1.5}>
            <title>{`${p.name}\n${xLabel}: ${p.x}\n${yLabel}: ${p.y}`}</title>
          </circle>
        </g>
      ))}

      {/* axis labels */}
      <text x={pad.left + plotW / 2} y={height - 6} textAnchor="middle" style={{ fontSize: 11 }} fill={INK_MUTED}>
        {xLabel}
      </text>
      <text
        x={-(pad.top + plotH / 2)}
        y={14}
        textAnchor="middle"
        transform="rotate(-90)"
        style={{ fontSize: 11 }}
        fill={INK_MUTED}
      >
        {yLabel}
      </text>
    </svg>
  );
}
