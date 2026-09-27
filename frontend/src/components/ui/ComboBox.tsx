import { useEffect, useMemo, useRef, useState } from "react";

export interface ComboOption {
  value: string;
  label: string;
  // Optional secondary line, e.g. a group's chair or a person's email.
  sublabel?: string;
  // Renders the row in a muted style — used for groups that exist only because
  // someone named them, so the user can tell them apart from registered ones.
  muted?: boolean;
  // Optional section this option belongs to. When it differs from the previous
  // rendered option's group, a non-selectable divider labelled with it appears
  // above the option — e.g. separating prescribed from user-defined types.
  group?: string;
}

interface Props {
  options: ComboOption[];
  // The current text in the box. This is a text-first control: the caller owns
  // the query, so a value the user typed but never picked is still usable.
  query: string;
  onQueryChange: (query: string) => void;
  onSelect: (option: ComboOption) => void;
  placeholder?: string;
  disabled?: boolean;
  // When set, a final row appears offering to create whatever was typed.
  createLabel?: (query: string) => string;
  onCreate?: (query: string) => void;
  // Skip local filtering when the caller already filters server-side.
  filter?: boolean;
  id?: string;
}

const inputClass =
  "w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:border-blue-500 disabled:bg-gray-100";

// Text input + filtered dropdown, with optional "create what I typed" row.
//
// Unlike `analytics/Typeahead`, which resolves strictly to an existing uuid,
// this keeps the typed text authoritative. The ToR form needs that: a group
// name or role that matches nothing yet is a legitimate answer, not an error.
export function ComboBox({
  options,
  query,
  onQueryChange,
  onSelect,
  placeholder,
  disabled,
  createLabel,
  onCreate,
  filter = true,
  id,
}: Props) {
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const rootRef = useRef<HTMLDivElement>(null);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!filter || !q) return options.slice(0, 50);
    return options.filter((o) => o.label.toLowerCase().includes(q)).slice(0, 50);
  }, [options, query, filter]);

  // An exact match means "create" would be a no-op, so hide that row.
  const canCreate =
    !!onCreate &&
    !!createLabel &&
    query.trim().length > 0 &&
    !options.some((o) => o.label.toLowerCase() === query.trim().toLowerCase());

  const rowCount = filtered.length + (canCreate ? 1 : 0);

  useEffect(() => {
    function onDoc(e: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  function commit(index: number) {
    if (index < filtered.length) {
      onSelect(filtered[index]);
    } else if (canCreate) {
      onCreate!(query.trim());
    }
    setOpen(false);
  }

  function onKeyDown(e: React.KeyboardEvent) {
    if (!open && (e.key === "ArrowDown" || e.key === "ArrowUp")) {
      setOpen(true);
      return;
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((a) => Math.min(a + 1, rowCount - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((a) => Math.max(a - 1, 0));
    } else if (e.key === "Enter") {
      // Only intercept Enter while a row is highlighted, so plain typing in a
      // wizard step does not get swallowed by the dropdown.
      if (open && rowCount > 0) {
        e.preventDefault();
        commit(active);
      }
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  }

  return (
    <div ref={rootRef} className="relative">
      <input
        id={id}
        className={inputClass}
        placeholder={placeholder}
        value={query}
        disabled={disabled}
        autoComplete="off"
        onChange={(e) => {
          onQueryChange(e.target.value);
          setOpen(true);
          setActive(0);
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={onKeyDown}
      />

      {open && rowCount > 0 && (
        <ul className="absolute z-20 mt-1 max-h-60 w-full overflow-auto rounded-md border border-gray-200 bg-white shadow-sm">
          {filtered.map((o, i) => {
            // A divider precedes the first option of each new section. Keyed off
            // the previous *rendered* option so it survives filtering, and it is
            // purely visual — it never counts toward the active/keyboard index.
            const showDivider = !!o.group && o.group !== filtered[i - 1]?.group;
            return (
              <li key={o.value}>
                {showDivider && (
                  <div className="border-t border-gray-100 px-3 pt-2 pb-1 text-[11px] font-medium tracking-wide text-gray-400 uppercase">
                    {o.group}
                  </div>
                )}
                <button
                  type="button"
                  onMouseEnter={() => setActive(i)}
                  onClick={() => commit(i)}
                  className={`w-full px-3 py-2 text-left text-sm ${
                    i === active ? "bg-blue-50" : "hover:bg-gray-50"
                  }`}
                >
                  <span className={o.muted ? "text-gray-500 italic" : "text-gray-800"}>
                    {o.label}
                  </span>
                  {o.sublabel && (
                    <span className="block text-xs text-gray-400">{o.sublabel}</span>
                  )}
                </button>
              </li>
            );
          })}

          {canCreate && (
            <li>
              <button
                type="button"
                onMouseEnter={() => setActive(filtered.length)}
                onClick={() => commit(filtered.length)}
                className={`w-full border-t border-gray-100 px-3 py-2 text-left text-sm text-blue-600 ${
                  active === filtered.length ? "bg-blue-50" : "hover:bg-gray-50"
                }`}
              >
                {createLabel!(query.trim())}
              </button>
            </li>
          )}
        </ul>
      )}
    </div>
  );
}
