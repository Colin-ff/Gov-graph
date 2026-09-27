import Dagre from "@dagrejs/dagre";
import {
  Background,
  Controls,
  Handle,
  MarkerType,
  Position,
  ReactFlow,
  useNodesState,
  useEdgesState,
  useReactFlow,
} from "@xyflow/react";
import type { Edge, Node, NodeProps } from "@xyflow/react";
import { useEffect, useState } from "react";

import "@xyflow/react/dist/style.css";

import { fetchGraph } from "../api/client";
import { mockGraphData } from "../api/mockData";
import type { GraphData, GraphNode } from "../types/governance";

const NODE_W = 80;
const NODE_H = 100;

const EDGE_GREY = "#9ca3af";
const EDGE_BLUE = "#3b82f6";

function GovernanceNode({ data, selected }: NodeProps) {
  const orphan = data.orphan as boolean;
  // A group that only exists because another group's ToR named it as its
  // reporting line. Drawn dashed so it reads as "known of, not registered".
  const proposed = data.proposed as boolean;

  const circleClass = proposed
    ? "bg-white border-blue-300 border-dashed"
    : orphan
      ? "bg-gray-200 border-gray-400 border-dashed"
      : "bg-blue-50 border-blue-300";

  return (
    <div className={`flex flex-col items-center ${orphan && !proposed ? "opacity-40" : ""}`}>
      <div
        className={`relative h-16 w-16 rounded-full border-2 ${circleClass} ${
          selected ? "ring-4 ring-blue-500 ring-offset-2" : ""
        }`}
      >
        {/* A reporting line leaves the subordinate's top edge and arrives at
            the governing group's bottom edge, so the arrow always points up
            the hierarchy. */}
        <Handle type="source" position={Position.Top} className="opacity-0" />
        <Handle type="target" position={Position.Bottom} className="opacity-0" />
      </div>
      <span className="mt-1.5 block max-w-[6rem] text-center text-xs font-medium leading-tight text-gray-700">
        {data.label as string}
      </span>
      {proposed && (
        <span className="text-[10px] italic leading-tight text-gray-400">
          not registered
        </span>
      )}
    </div>
  );
}

const nodeTypes = { governance: GovernanceNode };

function layout(data: GraphData): { id: string; x: number; y: number }[] {
  const g = new Dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: "TB", nodesep: 60, ranksep: 80 });

  for (const n of data.nodes) g.setNode(n.uuid, { width: NODE_W, height: NODE_H });

  // Edges are stored subordinate -> governing, but dagre ranks an edge's source
  // *above* its target. Feeding it reversed puts the governing group on top,
  // which is the whole point of the diagram.
  for (const r of data.relations) g.setEdge(r.target_uuid, r.source_uuid);

  Dagre.layout(g);

  return data.nodes.map((n) => {
    const pos = g.node(n.uuid);
    return { id: n.uuid, x: pos?.x ?? 0, y: pos?.y ?? 0 };
  });
}

function buildNodes(data: GraphData, selectedId?: string | null): Node[] {
  const connectedIds = new Set(
    data.relations.flatMap((r) => [r.source_uuid, r.target_uuid]),
  );
  const positions = layout(data);
  const posMap = Object.fromEntries(positions.map((p) => [p.id, p]));

  return data.nodes.map((n) => ({
    id: n.uuid,
    type: "governance",
    data: {
      label: n.group_name,
      orphan: !connectedIds.has(n.uuid),
      proposed: n.status === "proposed",
    },
    position: { x: posMap[n.uuid]?.x ?? 0, y: posMap[n.uuid]?.y ?? 0 },
    selected: n.uuid === selectedId,
  }));
}

function buildEdges(data: GraphData, selectedId?: string | null): Edge[] {
  // Every edge means the same thing now — "reports to" — so the type label that
  // used to sit on each line is just noise. The arrowhead carries the meaning.
  return data.relations.map((r) => {
    const highlighted =
      !!selectedId && (r.source_uuid === selectedId || r.target_uuid === selectedId);
    const colour = highlighted ? EDGE_BLUE : EDGE_GREY;
    return {
      id: `${r.source_uuid}->${r.target_uuid}`,
      type: "smoothstep",
      source: r.source_uuid,
      target: r.target_uuid,
      style: { stroke: colour, strokeWidth: highlighted ? 2 : 1.5 },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: colour,
        width: 18,
        height: 18,
      },
    };
  });
}

// Rendered inside <ReactFlow> so it can access the React Flow context
function AutoCenter({
  selectedNodeId,
  nodes,
}: {
  selectedNodeId?: string | null;
  nodes: Node[];
}) {
  const { setCenter } = useReactFlow();
  useEffect(() => {
    if (!selectedNodeId) return;
    const node = nodes.find((n) => n.id === selectedNodeId);
    if (node)
      setCenter(node.position.x + NODE_W / 2, node.position.y + NODE_H / 2, {
        zoom: 1.2,
        duration: 500,
      });
  }, [selectedNodeId, nodes, setCenter]);
  return null;
}

export function GovernanceGraph({ onNodeClick, selectedNodeId }: Props) {
  const [rawData, setRawData] = useState<GraphData>({ nodes: [], relations: [] });
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges] = useEdgesState<Edge>([]);

  useEffect(() => {
    fetchGraph()
      .then((data) => setRawData(data.nodes.length > 0 ? data : mockGraphData))
      .catch(() => setRawData(mockGraphData));
  }, []);

  // Re-run dagre layout only when the underlying data changes
  useEffect(() => {
    setNodes(buildNodes(rawData, selectedNodeId));
    setEdges(buildEdges(rawData, selectedNodeId));
  }, [rawData]); // eslint-disable-line react-hooks/exhaustive-deps

  // Update selection + edge highlighting without resetting node positions
  useEffect(() => {
    setNodes((prev) => prev.map((n) => ({ ...n, selected: n.id === selectedNodeId })));
    setEdges(buildEdges(rawData, selectedNodeId));
  }, [selectedNodeId]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="relative h-full min-w-0 flex-1">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onNodeClick={(_, node) => {
          const graphNode = rawData.nodes.find((n) => n.uuid === node.id);
          if (graphNode) onNodeClick?.(node.id, graphNode);
        }}
        fitView
      >
        <AutoCenter selectedNodeId={selectedNodeId} nodes={nodes} />
        <Background />
        <Controls />
      </ReactFlow>

      <div className="pointer-events-none absolute bottom-4 right-4 rounded border border-gray-200 bg-white/90 px-3 py-2 text-xs text-gray-500 shadow-sm">
        <span className="inline-flex items-center gap-1.5">
          <svg width="26" height="8" aria-hidden="true">
            <line x1="0" y1="4" x2="18" y2="4" stroke={EDGE_GREY} strokeWidth="1.5" />
            <polygon points="18,1 25,4 18,7" fill={EDGE_GREY} />
          </svg>
          reports to
        </span>
      </div>
    </div>
  );
}

interface Props {
  onNodeClick?: (nodeId: string, node: GraphNode) => void;
  selectedNodeId?: string | null;
}
