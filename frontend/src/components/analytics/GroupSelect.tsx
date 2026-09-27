import { useMemo } from "react";
import { Typeahead } from "./Typeahead";
import type { OrganisationListItem } from "../../types/governance";

interface Props {
  groups: OrganisationListItem[];
  value: string | null;
  onChange: (uuid: string | null) => void;
  label?: string;
  placeholder?: string;
}

// Group typeahead fed by the page-level organisation list.
export function GroupSelect({ groups, value, onChange, label, placeholder }: Props) {
  const options = useMemo(
    () =>
      groups.map((g) => ({
        uuid: g.uuid,
        label: g.group_name,
        sublabel: g.chair ? `Chair: ${g.chair}` : undefined,
      })),
    [groups],
  );
  return (
    <Typeahead
      options={options}
      value={value}
      onChange={onChange}
      label={label}
      placeholder={placeholder ?? "Search groups…"}
    />
  );
}
