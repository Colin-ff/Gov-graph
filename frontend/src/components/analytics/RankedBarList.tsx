import { EmptyState } from "./EmptyState";

export interface RankedBarItem {
  uuid: string;
  name: string;
  count: number;
}

interface Props {
  items: RankedBarItem[];
  // Formats the value shown at the row end (e.g. "12h", "3").
  formatValue?: (n: number) => string;
  onSelect?: (uuid: string) => void;
  selectedUuid?: string | null;
  emptyMessage?: string;
}

// Horizontal magnitude bars as styled divs — single hue (blue), width as a % of
// the max. Row = name / bar / value. Bars grow via a CSS width transition (one
// of the four agreed motions).
export function RankedBarList({
  items,
  formatValue = (n) => String(n),
  onSelect,
  selectedUuid,
  emptyMessage = "No data to rank yet.",
}: Props) {
  if (items.length === 0) return <EmptyState message={emptyMessage} />;
  const max = Math.max(...items.map((i) => i.count), 1);

  return (
    <ul className="space-y-2">
      {items.map((item) => {
        const pct = Math.max((item.count / max) * 100, item.count > 0 ? 2 : 0);
        const selected = item.uuid === selectedUuid;
        const RowTag = onSelect ? "button" : "div";
        return (
          <li key={item.uuid}>
            <RowTag
              type={onSelect ? "button" : undefined}
              onClick={onSelect ? () => onSelect(item.uuid) : undefined}
              className={`w-full flex items-center gap-3 text-left rounded px-2 py-1 ${
                onSelect ? "hover:bg-gray-50 cursor-pointer" : ""
              } ${selected ? "bg-blue-50" : ""}`}
            >
              <span
                className="text-sm text-gray-700 w-40 shrink-0 truncate"
                title={item.name}
              >
                {item.name}
              </span>
              <span className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                <span
                  className="block h-2 rounded-full bg-blue-600 transition-[width] duration-500 ease-out"
                  style={{ width: `${pct}%` }}
                />
              </span>
              <span className="text-sm text-gray-900 tabular-nums w-14 text-right shrink-0">
                {formatValue(item.count)}
              </span>
            </RowTag>
          </li>
        );
      })}
    </ul>
  );
}
