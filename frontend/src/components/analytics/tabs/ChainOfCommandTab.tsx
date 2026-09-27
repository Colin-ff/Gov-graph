import { SectionCard } from "../SectionCard";
import { GroupSelect } from "../GroupSelect";
import { ChainDiagram } from "../ChainDiagram";
import { SkeletonBlock } from "../SkeletonBlock";
import { EmptyState } from "../EmptyState";
import { useAnalyticsResource } from "../useAnalyticsResource";
import { fetchChainOfCommand } from "../../../api/analytics";
import { groupName } from "./types";
import type { TabProps } from "./types";

export function ChainOfCommandTab({ groups, param, setParam }: TabProps) {
  const from = param("from");
  const to = param("to");
  const both = from && to ? ([from, to] as const) : null;

  const chain = useAnalyticsResource(
    both ? () => fetchChainOfCommand(both[0], both[1]) : null,
    [from, to],
  );

  function swap() {
    setParam({ from: to, to: from });
  }

  const data = chain.data;
  const nodes = (data?.chain ?? []).map((uuid) => ({ uuid, name: groupName(groups, uuid) }));

  // The backend auto-detects direction, so chain[0] may be the group entered as
  // `to`. Caption according to which end is actually the more powerful.
  let caption: string | null = null;
  if (data?.connected && data.chain && data.chain.length > 0) {
    const topUuid = data.chain[0];
    const bottomUuid = data.chain[data.chain.length - 1];
    caption =
      `${groupName(groups, topUuid)} governs ${groupName(groups, bottomUuid)}` +
      (data.chain.length > 2 ? ` through ${data.chain.length - 2} intermediate group(s).` : ".");
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end gap-4">
        <div className="min-w-[14rem] flex-1 max-w-xs">
          <GroupSelect
            groups={groups}
            value={from}
            onChange={(uuid) => setParam({ from: uuid })}
            label="From"
          />
        </div>
        <button
          type="button"
          onClick={swap}
          disabled={!from || !to}
          className="px-3 py-2 text-sm border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-40"
        >
          ⇄ Swap
        </button>
        <div className="min-w-[14rem] flex-1 max-w-xs">
          <GroupSelect
            groups={groups}
            value={to}
            onChange={(uuid) => setParam({ to: uuid })}
            label="To"
          />
        </div>
      </div>

      {!both ? (
        <EmptyState message="Pick two groups to trace the reporting line between them." />
      ) : (
        <SectionCard label="Reporting chain">
          {chain.loading ? (
            <SkeletonBlock className="h-24 w-full" />
          ) : chain.error ? (
            <EmptyState message={chain.error} />
          ) : !data?.connected ? (
            <EmptyState message="No reporting line exists between these two groups." />
          ) : (
            <div className="space-y-4">
              <ChainDiagram nodes={nodes} />
              {caption && <p className="text-sm text-gray-600">{caption}</p>}
            </div>
          )}
        </SectionCard>
      )}
    </div>
  );
}
