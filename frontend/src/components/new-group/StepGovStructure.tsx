import { useEffect, useState } from "react";
import { DynamicList } from "./DynamicList";
import { ComboBox } from "../ui/ComboBox";
import { blankReport } from "./types";
import type { ReportEntry } from "./types";
import { fetchOrganisations } from "../../api/client";
import type { OrganisationListItem } from "../../types/governance";

const inp =
  "w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:border-blue-500";

interface Props {
  reportsTo: ReportEntry[];
  setReportsTo: (v: ReportEntry[]) => void;
}

// Reporting lines only.
//
// Earlier sprints also collected "affiliated groups", but that data was never
// submitted and a graph mixing relation kinds cannot be read at a glance. The
// registry now models one thing: who this group reports to. A group may report
// to several bodies, so the list stays multi-entry.
export function StepGovStructure({ reportsTo, setReportsTo }: Props) {
  const [groups, setGroups] = useState<OrganisationListItem[]>([]);

  useEffect(() => {
    fetchOrganisations()
      .then(setGroups)
      .catch(() => setGroups([]));
  }, []);

  function updateReportsTo(i: number, patch: Partial<ReportEntry>) {
    const copy = [...reportsTo];
    copy[i] = { ...copy[i], ...patch };
    setReportsTo(copy);
  }

  return (
    <div className="space-y-2">
      <p className="text-sm font-semibold text-gray-800">This group reports to</p>
      <p className="mb-3 text-xs text-gray-400">
        Pick a group already in the registry, or type the name of one that has
        not been registered yet — it will appear on the graph either way.
      </p>

      <DynamicList
        items={reportsTo}
        onAdd={() => setReportsTo([...reportsTo, blankReport()])}
        onRemove={(i) => setReportsTo(reportsTo.filter((_, j) => j !== i))}
        addLabel="+ Add reporting line"
        renderItem={(r, i) => (
          <>
            <ComboBox
              options={groups.map((g) => ({
                value: g.uuid,
                label: g.group_name,
                sublabel:
                  g.status === "proposed"
                    ? "Not registered yet"
                    : g.chair
                      ? `Chair: ${g.chair}`
                      : undefined,
                muted: g.status === "proposed",
              }))}
              query={r.groupName}
              // Typing clears the resolved uuid: the text no longer refers to
              // the group that was picked.
              onQueryChange={(name) =>
                updateReportsTo(i, { groupName: name, groupUuid: null })
              }
              onSelect={(o) =>
                updateReportsTo(i, { groupName: o.label, groupUuid: o.value })
              }
              placeholder="Search groups, or type a name"
            />
            {r.groupName.trim() && !r.groupUuid && (
              <p className="text-xs text-amber-600">
                Not in the registry — it will be added as an unregistered group.
              </p>
            )}
            <textarea
              className={`${inp} resize-none`}
              rows={2}
              placeholder="Note (optional)"
              value={r.note}
              onChange={(e) => updateReportsTo(i, { note: e.target.value })}
            />
          </>
        )}
      />
    </div>
  );
}
