import { useState } from "react";
import { SectionCard } from "../SectionCard";
import { RankedBarList } from "../RankedBarList";
import { StatTile } from "../StatTile";
import { TopNSelect } from "../TopNSelect";
import { PersonSelect } from "../PersonSelect";
import { SkeletonBlock } from "../SkeletonBlock";
import { EmptyState } from "../EmptyState";
import { useAnalyticsResource } from "../useAnalyticsResource";
import {
  fetchPersonGovernanceLoad,
  fetchPersonGroupCount,
  fetchTopGovernanceLoad,
  fetchTopGroupCount,
} from "../../../api/analytics";
import type { TabProps } from "./types";

type Metric = "hours" | "groups";

export function PersonBurdenTab({ people, param, setParam }: TabProps) {
  const [metric, setMetric] = useState<Metric>("hours");
  const [topN, setTopN] = useState(10);
  const selected = param("person");

  const top = useAnalyticsResource(
    () => (metric === "hours" ? fetchTopGovernanceLoad(topN) : fetchTopGroupCount(topN)),
    [metric, topN],
  );

  const load = useAnalyticsResource(
    selected ? () => fetchPersonGovernanceLoad(selected) : null,
    [selected],
  );
  const groupCount = useAnalyticsResource(
    selected ? () => fetchPersonGroupCount(selected) : null,
    [selected],
  );

  const selectedPerson = people.find((p) => p.uuid === selected);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end gap-4">
        <div className="inline-flex rounded-md border border-gray-300 overflow-hidden text-sm">
          <button
            type="button"
            onClick={() => setMetric("hours")}
            className={`px-3 py-1 ${metric === "hours" ? "bg-blue-600 text-white font-medium" : "bg-white text-gray-600 hover:bg-gray-50"}`}
          >
            Meeting hours
          </button>
          <button
            type="button"
            onClick={() => setMetric("groups")}
            className={`px-3 py-1 border-l border-gray-300 ${metric === "groups" ? "bg-blue-600 text-white font-medium" : "bg-white text-gray-600 hover:bg-gray-50"}`}
          >
            Groups
          </button>
        </div>
        <TopNSelect value={topN} onChange={setTopN} />
        <div className="min-w-[16rem] flex-1 max-w-sm">
          <PersonSelect
            people={people}
            value={selected}
            onChange={(uuid) => setParam({ person: uuid })}
            label="Drill down to a person"
          />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <SectionCard
          label={metric === "hours" ? `Top ${topN} by yearly meeting hours` : `Top ${topN} by group count`}
          className="lg:col-span-2"
        >
          {top.loading ? (
            <div className="space-y-3">
              {Array.from({ length: 5 }).map((_, i) => (
                <SkeletonBlock key={i} className="h-6 w-full" />
              ))}
            </div>
          ) : top.error ? (
            <EmptyState message={top.error} />
          ) : (
            <RankedBarList
              items={top.data?.people ?? []}
              formatValue={(n) => (metric === "hours" ? `${n.toFixed(0)}h` : String(n))}
              onSelect={(uuid) => setParam({ person: uuid })}
              selectedUuid={selected}
              emptyMessage="No people on any governance groups yet."
            />
          )}
        </SectionCard>

        <SectionCard label="Person drill-down">
          {!selected ? (
            <EmptyState message="Pick a person, or click a bar, to see their load." />
          ) : (
            <div className="space-y-6">
              <div>
                {selectedPerson ? (
                  <a
                    href={`/visualisation?person=${selected}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm font-medium text-blue-600 hover:underline"
                    title="Open this person in the visualisation (new tab)"
                  >
                    {selectedPerson.first_name} {selectedPerson.last_name}
                  </a>
                ) : (
                  <p className="text-sm font-medium text-gray-900">Selected person</p>
                )}
                {selectedPerson?.email && (
                  <p className="text-xs text-gray-500 mt-0.5">{selectedPerson.email}</p>
                )}
              </div>
              <StatTile
                value={load.loading ? null : load.data?.meeting_hours ?? 0}
                decimals={1}
                suffix="h"
                caption="Yearly meeting hours"
                loading={load.loading}
              />
              <StatTile
                value={groupCount.loading ? null : groupCount.data?.group_count ?? 0}
                caption="Governance groups"
                loading={groupCount.loading}
              />
            </div>
          )}
        </SectionCard>
      </div>
    </div>
  );
}
