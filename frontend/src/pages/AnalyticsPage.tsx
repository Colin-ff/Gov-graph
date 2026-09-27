import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { AnalyticsTabs } from "../components/analytics/AnalyticsTabs";
import type { TabDef } from "../components/analytics/AnalyticsTabs";
import { EmptyState } from "../components/analytics/EmptyState";
import { SkeletonBlock } from "../components/analytics/SkeletonBlock";
import { PersonBurdenTab } from "../components/analytics/tabs/PersonBurdenTab";
import { GroupConcentrationTab } from "../components/analytics/tabs/GroupConcentrationTab";
import { StructuralPitfallsTab } from "../components/analytics/tabs/StructuralPitfallsTab";
import { OverlappedDutiesTab } from "../components/analytics/tabs/OverlappedDutiesTab";
import { DiversityTab } from "../components/analytics/tabs/DiversityTab";
import { ChainOfCommandTab } from "../components/analytics/tabs/ChainOfCommandTab";
import type { TabProps } from "../components/analytics/tabs/types";
import { fetchOrganisations, fetchPeople, apiErrorMessages } from "../api/client";
import type { OrganisationListItem, PersonListItem } from "../types/governance";

const TABS: TabDef[] = [
  { key: "burden", label: "Person Burden" },
  { key: "concentration", label: "Group Concentration" },
  { key: "pitfalls", label: "Structural Pitfalls" },
  { key: "overlap", label: "Overlapped Duties" },
  { key: "diversity", label: "Diversity" },
  { key: "chain", label: "Chain of Command" },
];

const TAB_COMPONENTS: Record<string, (props: TabProps) => JSX.Element> = {
  burden: PersonBurdenTab,
  concentration: GroupConcentrationTab,
  pitfalls: StructuralPitfallsTab,
  overlap: OverlappedDutiesTab,
  diversity: DiversityTab,
  chain: ChainOfCommandTab,
};

export default function AnalyticsPage() {
  const [searchParams, setSearchParams] = useSearchParams();

  // Page-level, once-fetched lists shared by every tab (avoids per-tab refetch).
  const [groups, setGroups] = useState<OrganisationListItem[]>([]);
  const [people, setPeople] = useState<PersonListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    Promise.all([fetchOrganisations(), fetchPeople()])
      .then(([orgs, ppl]) => {
        if (cancelled) return;
        setGroups(orgs);
        setPeople(ppl);
      })
      .catch((err) => {
        if (!cancelled) setError(apiErrorMessages(err)[0]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const activeTab = searchParams.get("tab") ?? TABS[0].key;

  const param = useCallback((key: string) => searchParams.get(key), [searchParams]);

  // Patch the query string, keeping deep links shareable. `replace` avoids a
  // history entry per control tweak.
  const setParam = useCallback(
    (patch: Record<string, string | null>) => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          for (const [key, value] of Object.entries(patch)) {
            if (value == null || value === "") next.delete(key);
            else next.set(key, value);
          }
          return next;
        },
        { replace: true },
      );
    },
    [setSearchParams],
  );

  const ActiveTab = TAB_COMPONENTS[activeTab] ?? TAB_COMPONENTS.burden;

  return (
    <div>
      <h1 className="text-xl font-semibold text-gray-900 mb-1">Governance Analytics</h1>
      <p className="text-sm text-gray-500 mb-6">
        Insight over the governance graph — burden, concentration, structure, overlap, diversity,
        and reporting lines.
      </p>

      <AnalyticsTabs
        tabs={TABS}
        active={activeTab}
        onChange={(key) => setParam({ tab: key })}
      />

      <div className="mt-6">
        {loading ? (
          <div className="space-y-4">
            <SkeletonBlock className="h-8 w-64" />
            <SkeletonBlock className="h-48 w-full" />
          </div>
        ) : error ? (
          <EmptyState message={error} />
        ) : (
          <ActiveTab groups={groups} people={people} param={param} setParam={setParam} />
        )}
      </div>
    </div>
  );
}
