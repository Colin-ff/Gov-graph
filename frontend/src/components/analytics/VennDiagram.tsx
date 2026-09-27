import { CATEGORICAL } from "./palette";

interface Props {
  countA: number;
  countB: number;
  shared: number;
  labelA: string;
  labelB: string;
}

const COLOR_A = CATEGORICAL[0]; // blue
const COLOR_B = CATEGORICAL[5]; // orange — distinct from blue for CVD

// Two overlapping circles, radii proportional to √(member count) so area tracks
// size. Horizontal offset shrinks as the overlap grows. Guards against
// zero-member groups (which would otherwise give a zero/NaN radius).
export function VennDiagram({ countA, countB, shared, labelA, labelB }: Props) {
  const width = 360;
  const height = 220;
  const maxCount = Math.max(countA, countB, 1);
  const maxR = 78;
  const minR = 12;

  const radius = (count: number) =>
    count <= 0 ? minR : minR + (maxR - minR) * Math.sqrt(count / maxCount);

  const rA = radius(countA);
  const rB = radius(countB);

  // Overlap fraction relative to the smaller group drives how much the circles
  // are pulled together. No overlap -> circles just touch; full overlap -> nearly
  // concentric.
  const smaller = Math.min(countA, countB);
  const overlapFrac = smaller > 0 ? Math.min(shared / smaller, 1) : 0;
  const separation = (rA + rB) * (1 - 0.75 * overlapFrac);
  const cx = width / 2;
  const cy = height / 2;
  const ax = cx - separation / 2;
  const bx = cx + separation / 2;

  return (
    <div>
      <svg width="100%" viewBox={`0 0 ${width} ${height}`} role="img">
        <circle cx={ax} cy={cy} r={rA} fill={COLOR_A} fillOpacity={0.35} stroke={COLOR_A} />
        <circle cx={bx} cy={cy} r={rB} fill={COLOR_B} fillOpacity={0.35} stroke={COLOR_B} />
        {shared > 0 && (
          <text
            x={cx}
            y={cy + 4}
            textAnchor="middle"
            className="fill-gray-900"
            style={{ fontSize: 16, fontWeight: 700 }}
          >
            {shared}
          </text>
        )}
      </svg>
      <div className="flex justify-between text-sm mt-2">
        <span className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-sm" style={{ backgroundColor: COLOR_A }} />
          <span className="text-gray-700 truncate max-w-[9rem]" title={labelA}>
            {labelA}
          </span>
          <span className="text-gray-400 tabular-nums">{countA}</span>
        </span>
        <span className="flex items-center gap-2">
          <span className="text-gray-400 tabular-nums">{countB}</span>
          <span className="text-gray-700 truncate max-w-[9rem]" title={labelB}>
            {labelB}
          </span>
          <span className="w-3 h-3 rounded-sm" style={{ backgroundColor: COLOR_B }} />
        </span>
      </div>
    </div>
  );
}
