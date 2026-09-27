import { useMemo } from "react";
import { Link } from "react-router-dom";
import { ReactFlow, Background } from "@xyflow/react";
import type { Node, Edge } from "@xyflow/react";
import { SectionCard } from "../SectionCard";
import { SkeletonBlock } from "../SkeletonBlock";
import { EmptyState } from "../EmptyState";
import { useAnalyticsResource } from "../useAnalyticsResource";
import { fetchGraph } from "../../../api/client";
import { fetchMultipleReportingGroups, fetchOrphanGroups } from "../../../api/analytics";
import type { GraphData } from "../../../types/governance";
import type { TabProps } from "./types";

// Build a small neighbourhood (selected group + its direct relations) from the
// already-fetched graph. Parents (groups it reports to) sit above; children
// (groups reporting to it) sit below. Orphan-styled when isolated.
function buildNeighbourhood(
  graph: GraphData,
  selected: string,
): { nodes: Node[]; edges: Edge[] } {
  const nameOf = (uuid: string) =>
    graph.nodes.find((n) => n.uuid === uuid)?.group_name ?? `${uuid.slice(0, 8)}…`;

  const parents: string[] = [];
  const children: string[] = [];
  const edges: Edge[] = [];
  graph.relations.forEach((r, i) => {
    if (r.source_uuid === selected) {
      parents.push(r.target_uuid);
      edges.push({ id: `e${i}`, source: r.source_uuid, target: r.target_uuid, label: r.relation_type });
    } else if (r.target_uuid === selected) {
      children.push(r.source_uuid);
      edges.push({ id: `e${i}`, source: r.source_uuid, target: r.target_uuid, label: r.relation_type });
    }
  });

  const isolated = parents.length === 0 && children.length === 0;
  const spread = (list: string[], y: number): Node[] =>
    list.map((uuid, idx) => ({
      id: uuid,
      position: { x: 60 + idx * 180, y },
      data: { label: nameOf(uuid) },
      style: nodeStyle(false, false),
    }));

  const nodes: Node[] = [
    {
      id: selected,
      position: { x: 60 + (Math.max(parents.length, children.length, 1) - 1) * 90, y: 110 },
      data: { label: nameOf(selected) },
      style: nodeStyle(isolated, true),
    },
    ...spread(parents, 10),
    ...spread(children, 210),
  ];
  return { nodes, edges };
}

// The selected group is drawn amber so its place among the (blue) neighbours is
// unmistakable; an isolated selected group keeps the dashed border to still
// read as an orphan.
function nodeStyle(orphan: boolean, selected: boolean): React.CSSProperties {
  return {
    fontSize: 11,
    borderRadius: 8,
    padding: 6,
    width: 150,
    textAlign: "center",
    border: selected
      ? `2px ${orphan ? "dashed" : "solid"} #f59e0b`
      : orphan
        ? "1px dashed #9ca3af"
        : "1px solid #93c5fd",
    background: selected ? "#fef3c7" : orphan ? "#f3f4f6" : "#eff6ff",
    color: "#1f2937",
    fontWeight: selected ? 600 : undefined,
    opacity: orphan && !selected ? 0.6 : 1,
  };
}

function Neighbourhood({ graph, uuid }: { graph: GraphData; uuid: string }) {
  const { nodes, edges } = useMemo(() => buildNeighbourhood(graph, uuid), [graph, uuid]);
  return (
    <div className="h-56 border border-gray-200 rounded-md overflow-hidden">
      <ReactFlow nodes={nodes} edges={edges} fitView nodesDraggable={false} nodesConnectable={false}>
        <Background />
      </ReactFlow>
    </div>
  );
}

export function StructuralPitfallsTab({ param, setParam }: TabProps) {
  const orphans = useAnalyticsResource(() => fetchOrphanGroups(), []);
  const multi = useAnalyticsResource(() => fetchMultipleReportingGroups(), []);
  const graph = useAnalyticsResource(() => fetchGraph(), []);
  const selected = param("pitfall_group");

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <SectionCard
          label="Orphan groups — report to nobody"
          right={
            <span className="text-2xl font-bold text-gray-900 tabular-nums">
              {orphans.data?.groups.length ?? "—"}
            </span>
          }
        >
          {orphans.loading ? (
            <SkeletonBlock className="h-32 w-full" />
          ) : orphans.error ? (
            <EmptyState message={orphans.error} />
          ) : (orphans.data?.groups.length ?? 0) === 0 ? (
            <EmptyState message="No orphan groups — every group reports somewhere." />
          ) : (
            <ul className="space-y-1">
              {orphans.data!.groups.map((g) => (
                <li key={g.uuid}>
                  <button
                    type="button"
                    onClick={() => setParam({ pitfall_group: g.uuid })}
                    className={`w-full text-left text-sm px-2 py-1.5 rounded hover:bg-gray-50 ${
                      selected === g.uuid ? "bg-blue-50 text-blue-700" : "text-gray-700"
                    }`}
                  >
                    {g.name}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </SectionCard>

        <SectionCard
          label="Multiple reporting lines"
          right={
            <span className="text-2xl font-bold text-gray-900 tabular-nums">
              {multi.data?.groups.length ?? "—"}
            </span>
          }
        >
          {multi.loading ? (
            <SkeletonBlock className="h-32 w-full" />
          ) : multi.error ? (
            <EmptyState message={multi.error} />
          ) : (multi.data?.groups.length ?? 0) === 0 ? (
            <EmptyState message="No group reports to more than one parent." />
          ) : (
            <ul className="space-y-1">
              {multi.data!.groups.map((g) => (
                <li key={g.uuid}>
                  <button
                    type="button"
                    onClick={() => setParam({ pitfall_group: g.uuid })}
                    className={`w-full flex items-center justify-between text-sm px-2 py-1.5 rounded hover:bg-gray-50 ${
                      selected === g.uuid ? "bg-blue-50 text-blue-700" : "text-gray-700"
                    }`}
                  >
                    <span>{g.name}</span>
                    <span className="text-xs font-semibold bg-gray-100 text-gray-600 rounded-full px-2 py-0.5">
                      {g.count} lines
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </SectionCard>
      </div>

      {selected && (
        <SectionCard
          label="Neighbourhood preview"
          right={
            <Link
              to={`/visualisation?group=${selected}`}
              className="text-sm text-blue-600 hover:underline"
            >
              View in graph →
            </Link>
          }
        >
          {graph.loading ? (
            <SkeletonBlock className="h-56 w-full" />
          ) : graph.data ? (
            <Neighbourhood graph={graph.data} uuid={selected} />
          ) : (
            <EmptyState message="Could not load the graph." />
          )}
        </SectionCard>
      )}
    </div>
  );
}
