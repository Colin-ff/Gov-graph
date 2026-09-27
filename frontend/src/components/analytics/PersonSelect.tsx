import { useMemo } from "react";
import { Typeahead } from "./Typeahead";
import type { PersonListItem } from "../../types/governance";

interface Props {
  people: PersonListItem[];
  value: string | null;
  onChange: (uuid: string | null) => void;
  label?: string;
  placeholder?: string;
}

// Person typeahead fed by the page-level people list.
export function PersonSelect({ people, value, onChange, label, placeholder }: Props) {
  const options = useMemo(
    () =>
      people.map((p) => ({
        uuid: p.uuid,
        label: `${p.first_name} ${p.last_name}`,
        sublabel: p.email,
      })),
    [people],
  );
  return (
    <Typeahead
      options={options}
      value={value}
      onChange={onChange}
      label={label}
      placeholder={placeholder ?? "Search people…"}
    />
  );
}
