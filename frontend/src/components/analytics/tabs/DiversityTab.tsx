import { SectionCard } from "../SectionCard";
import { GroupSelect } from "../GroupSelect";
import { DonutChart } from "../DonutChart";
import { StackedBar } from "../StackedBar";
import { SkeletonBlock } from "../SkeletonBlock";
import { EmptyState } from "../EmptyState";
import { useAnalyticsResource } from "../useAnalyticsResource";
import { fetchGenderDistribution, fetchMemberRepresentation } from "../../../api/analytics";
import { genderColor, REPRESENTATION_COLORS } from "../palette";
import { groupName } from "./types";
import type { OrganisationListItem } from "../../../types/governance";
import type { TabProps } from "./types";

const MAX_COMPARE = 4;

function GroupDiversityCard({
  uuid,
  groups,
  onRemove,
  compact,
}: {
  uuid: string;
  groups: OrganisationListItem[];
  onRemove?: () => void;
  compact: boolean;
}) {
  const gender = useAnalyticsResource(() => fetchGenderDistribution(uuid), [uuid]);
  const rep = useAnalyticsResource(() => fetchMemberRepresentation(uuid), [uuid]);

  const distribution = gender.data?.distribution ?? {};
  const genderKeys = Object.keys(distribution).sort();
  const genderSlices = genderKeys.map((label) => ({
    label,
    value: distribution[label],
    color: genderColor(label, genderKeys),
  }));

  const representation = rep.data?.representation ?? {};
  const repSegments = ["student", "faculty", "external"]
    .filter((k) => k in representation)
    .map((k) => ({
      label: k,
      value: (representation as Record<string, number>)[k],
      color: REPRESENTATION_COLORS[k],
    }));

  const empty =
    !gender.loading &&
    !rep.loading &&
    genderSlices.length === 0 &&
    repSegments.length === 0;

  return (
    <SectionCard
      label={groupName(groups, uuid)}
      right={
        onRemove ? (
          <button
            type="button"
            onClick={onRemove}
            className="text-gray-400 hover:text-gray-600 text-lg leading-none"
            aria-label="Remove group"
          >
            ×
          </button>
        ) : undefined
      }
    >
      {gender.loading || rep.loading ? (
        <SkeletonBlock className="h-40 w-full" />
      ) : empty ? (
        <EmptyState message="This group has no members to break down." />
      ) : (
        <div className={compact ? "space-y-5" : "space-y-6"}>
          <div>
            <p className="text-xs text-gray-400 mb-2">Gender</p>
            {genderSlices.length > 0 ? (
              <DonutChart slices={genderSlices} size={compact ? 150 : 180} />
            ) : (
              <p className="text-sm text-gray-400">No gender data.</p>
            )}
          </div>
          <div>
            <p className="text-xs text-gray-400 mb-2">Representation</p>
            {repSegments.length > 0 ? (
              <StackedBar segments={repSegments} />
            ) : (
              <p className="text-sm text-gray-400">No representation data.</p>
            )}
          </div>
        </div>
      )}
    </SectionCard>
  );
}

export function DiversityTab({ groups, param, setParam }: TabProps) {
  const raw = param("div_groups");
  const selected = raw ? raw.split(",").filter(Boolean).slice(0, MAX_COMPARE) : [];

  function add(uuid: string | null) {
    if (!uuid || selected.includes(uuid) || selected.length >= MAX_COMPARE) return;
    setParam({ div_groups: [...selected, uuid].join(",") });
  }
  function remove(uuid: string) {
    const next = selected.filter((u) => u !== uuid);
    setParam({ div_groups: next.length ? next.join(",") : null });
  }

  const compact = selected.length > 1;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end gap-4">
        <div className="min-w-[16rem] flex-1 max-w-sm">
          <GroupSelect
            groups={groups}
            value={null}
            onChange={add}
            label={`Add a group to compare (up to ${MAX_COMPARE})`}
            placeholder="Search groups…"
          />
        </div>
        {selected.length > 0 && (
          <span className="text-xs text-gray-400">
            {selected.length}/{MAX_COMPARE} selected
          </span>
        )}
      </div>

      {selected.length === 0 ? (
        <EmptyState message="Pick a group to see its gender and representation breakdown." />
      ) : (
        <div
          className={
            selected.length === 1
              ? "grid grid-cols-1"
              : "grid grid-cols-1 md:grid-cols-2 gap-6"
          }
        >
          {selected.map((uuid) => (
            <GroupDiversityCard
              key={uuid}
              uuid={uuid}
              groups={groups}
              compact={compact}
              onRemove={() => remove(uuid)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
