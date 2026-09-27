import { useState } from "react";
import { SectionCard } from "../SectionCard";
import { RankedBarList } from "../RankedBarList";
import { TopNSelect } from "../TopNSelect";
import { QuadrantScatter } from "../QuadrantScatter";
import { SkeletonBlock } from "../SkeletonBlock";
import { EmptyState } from "../EmptyState";
import { useAnalyticsResource } from "../useAnalyticsResource";
import { fetchTopGovernanceHours, fetchTopGovernedGroupCount } from "../../../api/analytics";
import type { ScatterPoint } from "../QuadrantScatter";

// Large n to pull every group's value from the ranking endpoints (they compute
// over all groups then slice), so the scatter can join both axes in two calls.
const ALL = 1000;

// This tab needs no page-level props — it drives entirely off the ranking endpoints.
export function GroupConcentrationTab() {
  const [topN, setTopN] = useState(10);

  const topGoverned = useAnalyticsResource(() => fetchTopGovernedGroupCount(topN), [topN]);
  const topHours = useAnalyticsResource(() => fetchTopGovernanceHours(topN), [topN]);

  // Full lists (all groups) for the scatter — one call each, joined by uuid.
  const allGoverned = useAnalyticsResource(() => fetchTopGovernedGroupCount(ALL), []);
  const allHours = useAnalyticsResource(() => fetchTopGovernanceHours(ALL), []);

  const scatter: ScatterPoint[] = (() => {
    if (!allGoverned.data || !allHours.data) return [];
    const governedByUuid = new Map(allGoverned.data.groups.map((g) => [g.uuid, g]));
    return allHours.data.groups
      .map((h) => {
        const g = governedByUuid.get(h.uuid);
        return {
          uuid: h.uuid,
          name: h.name,
          x: h.count, // hours
          y: g ? g.count : 0, // groups governed
        };
      })
      .filter((p) => p.x > 0 || p.y > 0);
  })();

  const scatterLoading = allGoverned.loading || allHours.loading;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-500">
          Which bodies concentrate governance effort — by hours and by how many groups they govern.
        </p>
        <TopNSelect value={topN} onChange={setTopN} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <SectionCard label={`Top ${topN} by groups governed`}>
          {topGoverned.loading ? (
            <SkeletonBlock className="h-40 w-full" />
          ) : topGoverned.error ? (
            <EmptyState message={topGoverned.error} />
          ) : (
            <RankedBarList
              items={topGoverned.data?.groups ?? []}
              emptyMessage="No reporting lines recorded yet."
            />
          )}
        </SectionCard>
        <SectionCard label={`Top ${topN} by yearly meeting hours`}>
          {topHours.loading ? (
            <SkeletonBlock className="h-40 w-full" />
          ) : topHours.error ? (
            <EmptyState message={topHours.error} />
          ) : (
            <RankedBarList
              items={topHours.data?.groups ?? []}
              formatValue={(n) => `${n.toFixed(0)}h`}
              emptyMessage="No meeting hours recorded yet."
            />
          )}
        </SectionCard>
      </div>

      <SectionCard label="Effort hotspots — hours × groups governed">
        {scatterLoading ? (
          <SkeletonBlock className="h-72 w-full" />
        ) : scatter.length === 0 ? (
          <EmptyState message="Not enough group data to plot yet." />
        ) : (
          <QuadrantScatter
            points={scatter}
            xLabel="Yearly meeting hours"
            yLabel="Groups governed"
            quadrantLabels={{
              topRight: "Hotspot (heavy on both)",
              topLeft: "Governs many, light hours",
              bottomLeft: "Light on both",
              bottomRight: "Long hours, governs few",
            }}
          />
        )}
      </SectionCard>
    </div>
  );
}
