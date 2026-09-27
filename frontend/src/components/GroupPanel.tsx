import { useState } from "react";
import { ClampedText } from "./ui/ClampedText";
import { ResizablePanel } from "./ui/ResizablePanel";
import type { GovernanceGroup, GraphNode, OrgMember } from "../types/governance";

interface Props {
  graphNode: GraphNode;
  group: GovernanceGroup | null;
  loading: boolean;
  error?: string;
  onClose: () => void;
  onNodeSelect?: (uuid: string, groupName: string) => void;
  onPersonSelect?: (uuid: string, firstName: string, lastName: string) => void;
}

const typeBadge: Record<string, string> = {
  Committee: "bg-blue-100 text-blue-700",
  Board: "bg-purple-100 text-purple-700",
  "Working Group": "bg-green-100 text-green-700",
  "Advisory Panel": "bg-cyan-100 text-cyan-700",
  "Faculty/School": "bg-orange-100 text-orange-700",
};

const statusBadge: Record<string, string> = {
  active: "bg-green-100 text-green-700",
  inactive: "bg-gray-100 text-gray-600",
  archived: "bg-gray-100 text-gray-600",
  proposed: "bg-amber-100 text-amber-700",
};

const sectionLabel =
  "text-[10px] font-semibold text-gray-400 uppercase tracking-widest";

function formatDate(value?: string | null) {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function MemberRow({
  member,
  onPersonSelect,
}: {
  member: OrgMember;
  onPersonSelect?: Props["onPersonSelect"];
}) {
  return (
    <div className="flex items-start justify-between gap-4">
      <button
        onClick={() => onPersonSelect?.(member.uuid, member.first_name, member.last_name)}
        className="text-left text-xs font-medium text-blue-600 hover:underline"
      >
        {member.first_name} {member.last_name}
      </button>
      <span className="shrink-0 text-[10px] uppercase tracking-wide text-gray-500">
        {member.roles.join(", ")}
      </span>
    </div>
  );
}

export function GroupPanel({
  graphNode,
  group,
  loading,
  error,
  onClose,
  onNodeSelect,
  onPersonSelect,
}: Props) {
  const [showAllMembers, setShowAllMembers] = useState(false);

  const badge = group ? (typeBadge[group.entity_type] ?? "bg-gray-100 text-gray-700") : null;
  const members = group?.membership ?? [];

  // Chair and Secretariat are what a reader wants first; everyone else is
  // behind "view all" so the panel stays scannable on a large group.
  const isOfficer = (m: OrgMember) =>
    m.roles.some((r) => ["chair", "secretariat"].includes(r.toLowerCase()));
  const officers = members.filter(isOfficer);
  const others = members.filter((m) => !isOfficer(m));

  const reportsTo = (group?.relations ?? []).filter(
    (r) => r.direction !== "reported_to_by",
  );
  const reportedToBy = (group?.relations ?? []).filter(
    (r) => r.direction === "reported_to_by",
  );

  const torLink = group?.reference_links?.find((l) => l.title === "ToR");
  const validFrom = formatDate(group?.start_date);
  const validTo = formatDate(group?.review_date);

  return (
    <ResizablePanel>
      {/* Header */}
      <div className="flex items-start justify-between px-5 pb-4 pt-5">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-1.5">
            {badge && (
              <span
                className={`rounded-full px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide ${badge}`}
              >
                {group?.entity_type}
              </span>
            )}
            {group?.status && (
              <span
                className={`rounded-full px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide ${
                  statusBadge[group.status] ?? "bg-gray-100 text-gray-600"
                }`}
              >
                {group.status}
              </span>
            )}
          </div>
          <h2 className="mt-2 text-xl font-bold leading-tight text-gray-900">
            {graphNode.group_name}
          </h2>
        </div>
        <button
          onClick={onClose}
          aria-label="Close panel"
          className="ml-3 mt-0.5 shrink-0 text-xl leading-none text-gray-400 hover:text-gray-600"
        >
          ×
        </button>
      </div>

      {/* Scrollable body */}
      <div className="flex-1 overflow-y-auto">
        {loading && <p className="px-5 py-3 text-xs text-gray-400">Loading details…</p>}

        {!loading && error && <p className="px-5 py-3 text-xs text-red-600">{error}</p>}

        {group?.purpose && (
          <div className="border-t border-gray-100 px-5 py-4">
            <p className={`${sectionLabel} mb-2`}>Purpose</p>
            <ClampedText text={group.purpose} />
          </div>
        )}

        {group?.responsibilities && (
          <div className="border-t border-gray-100 px-5 py-4">
            <p className={`${sectionLabel} mb-2`}>Responsibilities</p>
            <ClampedText text={group.responsibilities} />
          </div>
        )}

        {/* Validity */}
        {group && (validFrom || validTo) && (
          <div className="border-t border-gray-100 px-5 py-4">
            <p className={`${sectionLabel} mb-2`}>Validity</p>
            <p className="text-sm text-gray-700">
              {validFrom ?? "—"} → {validTo ?? "—"}
            </p>
          </div>
        )}

        {/* Key roles, with the rest behind a toggle */}
        {members.length > 0 && (
          <div className="border-t border-gray-100 px-5 py-4">
            <p className={`${sectionLabel} mb-3`}>Members ({members.length})</p>
            <div className="space-y-2.5">
              {officers.map((m) => (
                <MemberRow key={m.uuid} member={m} onPersonSelect={onPersonSelect} />
              ))}
              {showAllMembers &&
                others.map((m) => (
                  <MemberRow key={m.uuid} member={m} onPersonSelect={onPersonSelect} />
                ))}
            </div>
            {others.length > 0 && (
              <button
                type="button"
                onClick={() => setShowAllMembers(!showAllMembers)}
                className="mt-2 text-xs text-blue-600 hover:underline"
              >
                {showAllMembers ? "Show less" : `View all ${members.length} members`}
              </button>
            )}
          </div>
        )}

        {/* Meetings — only present when the viewer is a superuser or a member. */}
        {group?.can_view_meetings && (
          <div className="border-t border-gray-100 px-5 py-4">
            <p className={`${sectionLabel} mb-3`}>Meetings</p>
            <div className="space-y-2.5">
              {group.meeting_frequency_per_year != null && (
                <div className="flex items-start justify-between gap-4">
                  <span className="w-36 shrink-0 text-xs text-gray-400">Frequency</span>
                  <span className="text-right text-xs text-gray-800">
                    {group.meeting_frequency_per_year} times/yr
                    {group.meeting_duration_hour != null &&
                      `, ${group.meeting_duration_hour} h/meeting`}
                  </span>
                </div>
              )}
              {torLink && (
                <div className="flex items-center justify-between gap-4">
                  <span className="w-36 shrink-0 text-xs text-gray-400">
                    Terms of Reference
                  </span>
                  <a
                    href={torLink.url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-xs text-blue-600 hover:underline"
                  >
                    View →
                  </a>
                </div>
              )}
              {(group.reference_links ?? [])
                .filter((l) => l.title !== "ToR")
                .map((l) => (
                  <div key={l.url} className="flex items-center justify-between gap-4">
                    <span className="w-36 shrink-0 text-xs text-gray-400">{l.title}</span>
                    <a
                      href={l.url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-xs text-blue-600 hover:underline"
                    >
                      View →
                    </a>
                  </div>
                ))}
            </div>
          </div>
        )}

        {group && !group.can_view_meetings && (
          <div className="border-t border-gray-100 px-5 py-4">
            <p className={`${sectionLabel} mb-2`}>Meetings</p>
            <p className="text-xs text-gray-400">
              Meeting details are visible to members of this group.
            </p>
          </div>
        )}

        {reportsTo.length > 0 && (
          <div className="border-t border-gray-100 px-5 py-4">
            <p className={`${sectionLabel} mb-3`}>Reports to ({reportsTo.length})</p>
            <div className="space-y-3">
              {reportsTo.map((rel) => (
                <button
                  key={rel.uuid}
                  onClick={() => onNodeSelect?.(rel.uuid, rel.group_name)}
                  className="-mx-1 flex w-full items-start gap-2.5 rounded px-1 py-0.5 text-left transition-colors hover:bg-gray-50"
                >
                  <span className="mt-1 shrink-0 text-xs text-gray-400">↑</span>
                  <p className="text-xs font-semibold text-gray-800">{rel.group_name}</p>
                </button>
              ))}
            </div>
          </div>
        )}

        {reportedToBy.length > 0 && (
          <div className="border-t border-gray-100 px-5 py-4">
            <p className={`${sectionLabel} mb-3`}>
              Governs ({reportedToBy.length})
            </p>
            <div className="space-y-3">
              {reportedToBy.map((rel) => (
                <button
                  key={rel.uuid}
                  onClick={() => onNodeSelect?.(rel.uuid, rel.group_name)}
                  className="-mx-1 flex w-full items-start gap-2.5 rounded px-1 py-0.5 text-left transition-colors hover:bg-gray-50"
                >
                  <span className="mt-1 shrink-0 text-xs text-gray-400">↓</span>
                  <p className="text-xs font-semibold text-gray-800">{rel.group_name}</p>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </ResizablePanel>
  );
}
