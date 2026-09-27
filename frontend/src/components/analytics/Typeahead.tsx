import { useEffect, useMemo, useRef, useState } from "react";

export interface TypeaheadOption {
  uuid: string;
  label: string;
  // Optional secondary line (e.g. chair name).
  sublabel?: string;
}

interface Props {
  options: TypeaheadOption[];
  value: string | null;
  onChange: (uuid: string | null) => void;
  placeholder?: string;
  label?: string;
}

const inputClass =
  "w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:border-blue-500";

// Typeahead search: text input + filtered dropdown, keyboard nav (↑/↓/Enter/Esc)
// and a clear button. Reused by GroupSelect and PersonSelect.
export function Typeahead({ options, value, onChange, placeholder, label }: Props) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const rootRef = useRef<HTMLDivElement>(null);

  const selected = useMemo(
    () => options.find((o) => o.uuid === value) ?? null,
    [options, value],
  );

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return options.slice(0, 50);
    return options.filter((o) => o.label.toLowerCase().includes(q)).slice(0, 50);
  }, [options, query]);

  // Close on outside click.
  useEffect(() => {
    function onDoc(e: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  function commit(uuid: string) {
    onChange(uuid);
    setOpen(false);
    setQuery("");
  }

  function onKeyDown(e: React.KeyboardEvent) {
    if (!open && (e.key === "ArrowDown" || e.key === "ArrowUp")) {
      setOpen(true);
      return;
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((a) => Math.min(a + 1, filtered.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((a) => Math.max(a - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (filtered[active]) commit(filtered[active].uuid);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  }

  return (
    <div ref={rootRef} className="relative">
      {label && <label className="block text-xs text-gray-500 mb-1">{label}</label>}
      <div className="relative">
        <input
          className={inputClass}
          placeholder={placeholder ?? "Search…"}
          value={open ? query : selected?.label ?? ""}
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
            setActive(0);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={onKeyDown}
        />
        {selected && (
          <button
            type="button"
            aria-label="Clear selection"
            onClick={() => {
              onChange(null);
              setQuery("");
            }}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 text-lg leading-none"
          >
            ×
          </button>
        )}
      </div>
      {open && filtered.length > 0 && (
        <ul className="absolute z-10 mt-1 w-full max-h-60 overflow-auto bg-white border border-gray-200 rounded-md shadow-sm">
          {filtered.map((o, i) => (
            <li key={o.uuid}>
              <button
                type="button"
                onMouseEnter={() => setActive(i)}
                onClick={() => commit(o.uuid)}
                className={`w-full text-left px-3 py-2 text-sm ${
                  i === active ? "bg-blue-50" : "hover:bg-gray-50"
                }`}
              >
                <span className="text-gray-800">{o.label}</span>
                {o.sublabel && (
                  <span className="block text-xs text-gray-400">{o.sublabel}</span>
                )}
              </button>
            </li>
          ))}
        </ul>
      )}
      {open && filtered.length === 0 && (
        <div className="absolute z-10 mt-1 w-full bg-white border border-gray-200 rounded-md shadow-sm px-3 py-2 text-sm text-gray-400">
          No matches
        </div>
      )}
    </div>
  );
}
