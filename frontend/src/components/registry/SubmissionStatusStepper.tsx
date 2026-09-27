import type { TorSubmissionStatus } from "../../types/governance";

// Three nodes joined by two lines: Draft -> Pending Review -> Result.
type NodeState = "done" | "active" | "future" | "approved" | "rejected";

const DOT: Record<NodeState, string> = {
  done: "bg-gray-400",
  active: "bg-blue-600",
  future: "bg-gray-200",
  approved: "bg-green-600",
  rejected: "bg-red-600",
};

const LABEL: Record<NodeState, string> = {
  done: "text-gray-500",
  active: "font-medium text-gray-900",
  future: "text-gray-400",
  approved: "font-medium text-green-700",
  rejected: "font-medium text-red-700",
};

/**
 * The three node states for a submission, kept as a pure function so the JSX
 * below stays free of nested ternaries.
 */
function nodeStates(status: TorSubmissionStatus): [NodeState, NodeState, NodeState] {
  switch (status) {
    case "draft":
      return ["active", "future", "future"];
    case "pending_review":
      return ["done", "active", "future"];
    case "approved":
      return ["done", "done", "approved"];
    case "rejected":
      return ["done", "done", "rejected"];
  }
}

function resultLabel(status: TorSubmissionStatus): string {
  if (status === "approved") return "Approved";
  if (status === "rejected") return "Rejected";
  return "Result";
}

const STATUS_LABEL: Record<TorSubmissionStatus, string> = {
  draft: "Draft",
  pending_review: "Pending review",
  approved: "Approved",
  rejected: "Rejected",
};

export function SubmissionStatusStepper({
  status,
  className,
}: {
  status: TorSubmissionStatus;
  className?: string;
}) {
  const states = nodeStates(status);
  const labels = ["Draft", "Pending Review", resultLabel(status)];

  return (
    // Colour alone carries the stage, so the text under each dot is doing real
    // work for anyone who cannot distinguish them — it is not decoration.
    <div
      className={`flex w-64 items-start ${className ?? ""}`}
      aria-label={`Status: ${STATUS_LABEL[status]}`}
    >
      {states.map((state, i) => (
        <div key={i} className="flex flex-1 flex-col items-center">
          <div className="flex w-full items-center">
            {/* Half-width spacers keep each dot centred over its own label. */}
            <div
              className={`h-0.5 flex-1 ${i === 0 ? "bg-transparent" : states[i] === "future" ? "bg-gray-200" : "bg-gray-400"}`}
            />
            <div className={`h-2.5 w-2.5 shrink-0 rounded-full ${DOT[state]}`} />
            <div
              className={`h-0.5 flex-1 ${i === states.length - 1 ? "bg-transparent" : states[i + 1] === "future" ? "bg-gray-200" : "bg-gray-400"}`}
            />
          </div>
          <span className={`mt-1.5 text-center text-[11px] leading-tight ${LABEL[state]}`}>
            {labels[i]}
          </span>
        </div>
      ))}
    </div>
  );
}
