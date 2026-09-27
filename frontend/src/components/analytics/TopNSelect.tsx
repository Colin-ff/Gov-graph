interface Props {
  value: number;
  onChange: (n: number) => void;
  options?: number[];
}

// Segmented control for the top-N size (5 / 10 / 20 by default).
export function TopNSelect({ value, onChange, options = [5, 10, 20] }: Props) {
  return (
    <div className="inline-flex rounded-md border border-gray-300 overflow-hidden text-sm">
      {options.map((opt, i) => (
        <button
          key={opt}
          type="button"
          onClick={() => onChange(opt)}
          className={`px-3 py-1 ${i > 0 ? "border-l border-gray-300" : ""} ${
            value === opt
              ? "bg-blue-600 text-white font-medium"
              : "bg-white text-gray-600 hover:bg-gray-50"
          }`}
        >
          {opt}
        </button>
      ))}
    </div>
  );
}
