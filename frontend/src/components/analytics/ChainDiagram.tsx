import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

export interface ChainNode {
  uuid: string;
  name: string;
}

interface Props {
  nodes: ChainNode[]; // ordered most-powerful first
}

// Blue-intensity gradient: most-powerful node darkest, fading down the chain.
const BLUE_STEPS = ["#0d366b", "#184f95", "#1c5cab", "#256abf", "#2a78d6", "#3987e5", "#5598e7"];

function nodeColor(index: number, total: number): string {
  if (total <= 1) return BLUE_STEPS[0];
  const t = index / (total - 1);
  return BLUE_STEPS[Math.round(t * (BLUE_STEPS.length - 1))];
}

// Horizontal node → arrow → node sequence, revealed sequentially (one of the
// four agreed motions — motion mirrors authority flowing down the reporting line).
export function ChainDiagram({ nodes }: Props) {
  const [revealed, setRevealed] = useState(0);

  useEffect(() => {
    setRevealed(0);
    if (nodes.length === 0) return;
    let i = 0;
    const id = setInterval(() => {
      i += 1;
      setRevealed(i);
      if (i >= nodes.length) clearInterval(id);
    }, 220);
    return () => clearInterval(id);
  }, [nodes]);

  return (
    <div className="flex flex-wrap items-center gap-y-3">
      {nodes.map((node, i) => {
        const visible = i < revealed;
        return (
          <div key={node.uuid} className="flex items-center">
            <div className="relative group">
              <div
                className="rounded-lg px-4 py-2 text-white text-sm font-medium max-w-[12rem] truncate transition-opacity duration-300"
                style={{
                  backgroundColor: nodeColor(i, nodes.length),
                  opacity: visible ? 1 : 0,
                }}
              >
                {node.name}
              </div>
              {/* Hover card: full (untruncated) name + a shortcut to the graph
                  centred on this group. pt-1 bridges the gap so the card stays
                  open while the cursor moves onto it. */}
              {visible && (
                <div className="absolute left-0 top-full z-10 hidden group-hover:block pt-1">
                  <div className="min-w-[10rem] max-w-[20rem] rounded-md border border-gray-200 bg-white px-3 py-2 shadow-lg">
                    <p className="text-sm font-medium text-gray-900 break-words">{node.name}</p>
                    <Link
                      to={`/visualisation?group=${node.uuid}`}
                      className="mt-1 inline-block text-xs text-blue-600 hover:underline"
                    >
                      Visualise →
                    </Link>
                  </div>
                </div>
              )}
            </div>
            {i < nodes.length - 1 && (
              <span
                className="mx-2 text-gray-400 transition-opacity duration-300"
                style={{ opacity: i + 1 < revealed ? 1 : 0 }}
              >
                →
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}
