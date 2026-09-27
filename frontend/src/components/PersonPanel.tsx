import { ResizablePanel } from "./ui/ResizablePanel";
import type { PersonPublic } from "../types/governance";

interface Props {
  person: PersonPublic;
  loading: boolean;
  onClose: () => void;
  onBack: () => void;
  onGroupSelect: (uuid: string, groupName: string) => void;
}

const sectionLabel =
  "text-[10px] font-semibold text-gray-400 uppercase tracking-widest";

// The API calls the staff bucket "faculty"; the UI says "Staff" everywhere else,
// so translate rather than leaking the internal wording.
const representationLabel: Record<string, string> = {
  student: "Student",
  faculty: "Staff",
  external: "External",
};

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-4">
      <span className="w-28 shrink-0 text-xs text-gray-400">{label}</span>
      <span className="break-all text-right text-xs text-gray-800">{value}</span>
    </div>
  );
}

export function PersonPanel({ person, loading, onClose, onBack, onGroupSelect }: Props) {
  // Contact details are only present in the superuser view; a staff caller gets
  // the minimal public reference and this whole block stays hidden.
  const details: { label: string; value: string }[] = [];
  if (person.email) details.push({ label: "Email", value: person.email });
  if (person.phone) details.push({ label: "Phone", value: person.phone });
  if (person.zID) details.push({ label: "zID", value: person.zID });
  if (person.gender) details.push({ label: "Gender", value: person.gender });
  if (person.member_representation) {
    details.push({
      label: "Representation",
      value:
        representationLabel[person.member_representation] ??
        person.member_representation,
    });
  }

  return (
    <ResizablePanel>
      {/* Header */}
      <div className="flex items-start justify-between px-5 pb-4 pt-5">
        <div className="min-w-0 flex-1">
          <button
            onClick={onBack}
            className="mb-2 flex items-center gap-1 text-xs text-gray-400 hover:text-gray-600"
          >
            ← Back
          </button>
          <span className="rounded-full bg-gray-100 px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-gray-600">
            Person
          </span>
          <h2 className="mt-2 text-xl font-bold leading-tight text-gray-900">
            {person.first_name} {person.last_name}
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

      {/* Body */}
      <div className="flex-1 overflow-y-auto">
        {loading && <p className="px-5 py-3 text-xs text-gray-400">Loading…</p>}

        {!loading && details.length > 0 && (
          <div className="border-t border-gray-100 px-5 py-4">
            <p className={`${sectionLabel} mb-3`}>Contact details</p>
            <div className="space-y-2.5">
              {details.map((d) => (
                <DetailRow key={d.label} label={d.label} value={d.value} />
              ))}
            </div>
          </div>
        )}

        {!loading && person.affiliated_groups.length === 0 && (
          <p className="px-5 py-3 text-xs text-gray-400">Not a member of any groups.</p>
        )}

        {!loading && person.affiliated_groups.length > 0 && (
          <div className="border-t border-gray-100 px-5 py-4">
            <p className={`${sectionLabel} mb-3`}>
              Member of ({person.affiliated_groups.length})
            </p>
            <div className="space-y-3">
              {person.affiliated_groups.map((g) => (
                <button
                  key={g.group_uuid}
                  onClick={() => onGroupSelect(g.group_uuid, g.group_name)}
                  className="-mx-1 flex w-full items-start gap-2.5 rounded px-1 py-0.5 text-left transition-colors hover:bg-gray-50"
                >
                  <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-blue-300" />
                  <div>
                    <p className="text-xs font-semibold text-gray-800">{g.group_name}</p>
                    <p className="text-[10px] uppercase tracking-wide text-gray-400">
                      {g.roles.join(", ")}
                    </p>
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </ResizablePanel>
  );
}
