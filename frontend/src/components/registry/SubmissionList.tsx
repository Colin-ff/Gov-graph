import { SubmissionRow } from "./SubmissionRow";
import type { TorSubmissionSummary } from "../../types/governance";

export function SubmissionList({
  submissions,
  loading,
  errors,
  emptyMessage,
  showSubmitter = false,
}: {
  submissions: TorSubmissionSummary[];
  loading: boolean;
  errors: string[];
  emptyMessage: string;
  showSubmitter?: boolean;
}) {
  if (loading) {
    return <p className="text-sm text-gray-500">Loading…</p>;
  }

  if (errors.length > 0) {
    return (
      <ul className="list-inside list-disc space-y-1">
        {errors.map((e, i) => (
          <li key={i} className="text-sm text-red-600">
            {e}
          </li>
        ))}
      </ul>
    );
  }

  if (submissions.length === 0) {
    return <p className="text-sm text-gray-500">{emptyMessage}</p>;
  }

  return (
    <div className="space-y-3">
      {submissions.map((submission) => (
        <SubmissionRow
          key={submission.uuid}
          submission={submission}
          showSubmitter={showSubmitter}
        />
      ))}
    </div>
  );
}
