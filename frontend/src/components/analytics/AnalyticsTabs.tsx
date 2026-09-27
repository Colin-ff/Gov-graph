export interface TabDef {
  key: string;
  label: string;
}

interface Props {
  tabs: TabDef[];
  active: string;
  onChange: (key: string) => void;
}

// Six-tab bar styled like the Layout NavLink strip, plus a sliding underline
// positioned by the active index (one of the four agreed motions).
export function AnalyticsTabs({ tabs, active, onChange }: Props) {
  const activeIndex = Math.max(
    tabs.findIndex((t) => t.key === active),
    0,
  );
  const widthPct = 100 / tabs.length;

  return (
    <div className="border-b border-gray-200">
      <div className="flex relative">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => onChange(tab.key)}
            className={`flex-1 text-center text-sm py-3 px-2 transition-colors ${
              tab.key === active
                ? "text-blue-600 font-medium"
                : "text-gray-600 hover:text-gray-900"
            }`}
          >
            {tab.label}
          </button>
        ))}
        <span
          className="absolute bottom-0 h-0.5 bg-blue-600 transition-[left] duration-300 ease-out"
          style={{ width: `${widthPct}%`, left: `${activeIndex * widthPct}%` }}
        />
      </div>
    </div>
  );
}
