import { SectionCard } from "../SectionCard";
import { GroupSelect } from "../GroupSelect";
import { VennDiagram } from "../VennDiagram";
import { SkeletonBlock } from "../SkeletonBlock";
import { EmptyState } from "../EmptyState";
import { useAnalyticsResource } from "../useAnalyticsResource";
import { fetchOverlapPercentage, fetchSharedMemberList } from "../../../api/analytics";
import { fetchGroup } from "../../../api/client";
import type { TabProps } from "./types";

export function OverlappedDutiesTab({ groups, param, setParam }: TabProps) {
  const groupA = param("group_a");
  const groupB = param("group_b");
  const both = groupA && groupB ? ([groupA, groupB] as const) : null;

  const percentage = useAnalyticsResource(
    both ? () => fetchOverlapPercentage(both[0], both[1]) : null,
    [groupA, groupB],
  );
  const sharedList = useAnalyticsResource(
    both ? () => fetchSharedMemberList(both[0], both[1]) : null,
    [groupA, groupB],
  );
  const detailA = useAnalyticsResource(groupA ? () => fetchGroup(groupA) : null, [groupA]);
  const detailB = useAnalyticsResource(groupB ? () => fetchGroup(groupB) : null, [groupB]);

  const countA = detailA.data?.membership?.length ?? 0;
  const countB = detailB.data?.membership?.length ?? 0;
  const shared = sharedList.data?.shared_member_count ?? 0;

  function swap() {
    setParam({ group_a: groupB, group_b: groupA });
  }

  const nameOf = (uuid: string | null) =>
    groups.find((g) => g.uuid === uuid)?.group_name ?? "—";

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end gap-4">
        <div className="min-w-[14rem] flex-1 max-w-xs">
          <GroupSelect
            groups={groups}
            value={groupA}
            onChange={(uuid) => setParam({ group_a: uuid })}
            label="Group A"
          />
        </div>
        <button
          type="button"
          onClick={swap}
          disabled={!groupA || !groupB}
          className="px-3 py-2 text-sm border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-40"
          title="Swap A and B (the overlap % is relative to group B)"
        >
          ⇄ Swap
        </button>
        <div className="min-w-[14rem] flex-1 max-w-xs">
          <GroupSelect
            groups={groups}
            value={groupB}
            onChange={(uuid) => setParam({ group_b: uuid })}
            label="Group B (denominator)"
          />
        </div>
      </div>

      {!both ? (
        <EmptyState message="Pick two groups to compare their memberships." />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <SectionCard label="Membership overlap" className="lg:col-span-2">
            {detailA.loading || detailB.loading || sharedList.loading ? (
              <SkeletonBlock className="h-52 w-full" />
            ) : (
              <VennDiagram
                countA={countA}
                countB={countB}
                shared={shared}
                labelA={nameOf(groupA)}
                labelB={nameOf(groupB)}
              />
            )}
            {percentage.data && (
              <p className="text-sm text-gray-700 mt-4 border-t border-gray-100 pt-4">
                {percentage.data.description}
              </p>
            )}
          </SectionCard>

          <SectionCard label={`Shared members (${shared})`}>
            {sharedList.loading ? (
              <SkeletonBlock className="h-40 w-full" />
            ) : sharedList.error ? (
              <EmptyState message={sharedList.error} />
            ) : shared === 0 ? (
              <EmptyState message="These two groups share no members." />
            ) : (
              <div className="flex flex-wrap gap-2">
                {sharedList.data!.shared_members.map((m) => (
                  <span
                    key={m.uuid}
                    className="text-xs bg-gray-100 text-gray-700 rounded-full px-2.5 py-1"
                  >
                    {m.first_name} {m.last_name}
                  </span>
                ))}
              </div>
            )}
          </SectionCard>
        </div>
      )}
    </div>
  );
}
