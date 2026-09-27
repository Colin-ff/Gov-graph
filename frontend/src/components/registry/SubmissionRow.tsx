import { useNavigate } from "react-router-dom";
import { SubmissionStatusStepper } from "./SubmissionStatusStepper";
import type {
  GovernanceGroup,
  PossibleDuplicateGroup,
  TorSubmissionSummary,
} from "../../types/governance";
import { api, fetchGroup } from "../../api/client";
import { useEffect, useState } from "react";

function formatDate(iso: string | null): string {
  if (!iso) return "";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export function SubmissionRow({
  submission,
  showSubmitter = false,
}: {
  submission: TorSubmissionSummary;
  // Org-wide superuser lists are unattributable without it; a common user's own
  // list would just repeat their own address on every row.
  showSubmitter?: boolean;
}) {
  const navigate = useNavigate();

  // A draft has never been submitted, so it has no submission date — fall back
  // to when it was started rather than showing a blank.
  const isDraft = submission.status === "draft";
  const date = formatDate(isDraft ? submission.created_at : submission.submitted_at);

  const [groupInfo, setGroupInfo] = useState<GovernanceGroup>();
  const [duplicateGroups, setDuplicateGroups] = useState<PossibleDuplicateGroup[]>([]);
  
  useEffect(() => {
    const retrieveGroupInfo = async () => {
      if (submission.group_uuid != null) {
        const response = await fetchGroup(submission.group_uuid);
        setGroupInfo(response);
      }
    }
    retrieveGroupInfo();
  }, []);

  useEffect(() => {
    const checkDuplicates = async () => {
      if (groupInfo) {
        const payload = {
          "entity_type": groupInfo.entity_type,
          "purpose": groupInfo.purpose,
          "responsibilities": groupInfo.responsibilities,
          "relations": groupInfo.relations ?? [],
          "group_uuid": groupInfo.uuid,
        }
        
        try {
          const response = await api.post("/tor/check-duplicates", payload);
          setDuplicateGroups(response.data.possible_duplicates ?? []);
        } catch (err) {
          console.error("Duplicate check error:", err);
        }
      }
    }
    checkDuplicates();
  }, [groupInfo]);

  return (
    <button
      type="button"
      onClick={() => navigate(`/registry/tor/${submission.uuid}`)}
      className="flex w-full items-center justify-between gap-6 rounded-lg border border-gray-200 bg-white p-6 text-left transition hover:border-gray-300 hover:shadow-sm"
    >
      <div className="min-w-0">
        {submission.group_name ? (
          <p className="truncate text-sm font-medium text-gray-900">{submission.group_name}</p>
        ) : (
          <p className="truncate text-sm text-gray-400 italic">Untitled draft</p>
        )}
        <p className="mt-0.5 text-xs text-gray-500">
          {isDraft ? "Started" : "Submitted"} {date}
          {showSubmitter && submission.submitted_by_email && (
            <span> · {submission.submitted_by_email}</span>
          )}
        </p>
        {/* The reviewer's decision note, once resolved — green for an approval,
            red for a rejection. */}
        {(submission.status === "approved" || submission.status === "rejected") &&
          submission.admin_comment && (
            <p
              className={`mt-1.5 text-xs ${
                submission.status === "approved" ? "text-green-700" : "text-red-700"
              }`}
            >
              {submission.admin_comment}
            </p>
          )}
        {duplicateGroups.length > 0 && (
          <div
            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20 mt-1 max-w-full"
            title={`Similar to: ${duplicateGroups.map((g) => g.group_name).join(", ")}`}
          >
            <span className="truncate">
              Similar to {duplicateGroups.map((g) => g.group_name).join(", ")}
            </span>
          </div>
        )}
      </div>

      <SubmissionStatusStepper status={submission.status} className="shrink-0" />
    </button>
  );
}
