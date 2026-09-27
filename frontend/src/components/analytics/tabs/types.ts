import type { OrganisationListItem, PersonListItem } from "../../../types/governance";

// Shared contract passed from AnalyticsPage to every tab. The page owns the
// once-fetched group + people lists and the URL-synced param store; tabs read
// their params through `param` and write via `setParam` (which patches the
// query string), keeping deep links shareable.
export interface TabProps {
  groups: OrganisationListItem[];
  people: PersonListItem[];
  param: (key: string) => string | null;
  setParam: (patch: Record<string, string | null>) => void;
}

// Resolve a group's display name from the page-level list, falling back to a
// truncated uuid when unresolvable (used by the chain tab).
export function groupName(groups: OrganisationListItem[], uuid: string): string {
  const found = groups.find((g) => g.uuid === uuid);
  return found ? found.group_name : `${uuid.slice(0, 8)}…`;
}
