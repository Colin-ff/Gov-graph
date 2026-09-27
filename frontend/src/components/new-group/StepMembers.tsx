import { useEffect, useState } from "react";
import { PersonFields } from "./PersonFields";
import { Modal } from "../ui/Modal";
import { FormField } from "./FormField";
import {
  blankPerson,
  CHAIR_ROLE,
  representationFromApi,
  SECRETARIAT_ROLE,
} from "./types";
import type { Person } from "./types";
import {
  createMemberRole,
  fetchMemberRoles,
  fetchPeople,
  fetchPerson,
} from "../../api/client";
import type { PersonListItem } from "../../types/governance";

const inp =
  "w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:border-blue-500";

// The default role a freshly added common member starts with, so the common
// case needs no extra pick and passes the "at least one role" check.
const DEFAULT_MEMBER_ROLE = "Member";
const DEFAULT_ROLES = [CHAIR_ROLE, SECRETARIAT_ROLE, DEFAULT_MEMBER_ROLE];

// Chair and Secretariat are added by the form itself, never by the member
// picker. Assigning a second holder breaks the single-holder design, so they
// are barred from both selection and the "create a new role" path.
const isReservedRole = (name: string) =>
  name.trim().toLowerCase() === CHAIR_ROLE.toLowerCase() ||
  name.trim().toLowerCase() === SECRETARIAT_ROLE.toLowerCase();

interface Props {
  members: Person[];
  setMembers: (v: Person[]) => void;
}

// One flat list of members, each carrying their own roles.
//
// The previous design had fixed Chair and Secretariat blocks plus an "extra
// members" array, which made the common "one person chairs and runs the
// secretariat" case impossible to express without entering them twice. Roles
// living on the member means that person is one row holding two roles.
export function StepMembers({ members, setMembers }: Props) {
  const [people, setPeople] = useState<PersonListItem[]>([]);
  const [roleOptions, setRoleOptions] = useState<string[]>(DEFAULT_ROLES);
  const [notice, setNotice] = useState("");

  const [creatingRole, setCreatingRole] = useState(false);
  const [newRoleName, setNewRoleName] = useState("");
  const [newRoleDescription, setNewRoleDescription] = useState("");
  const [roleError, setRoleError] = useState("");
  // Which member row asked for the new role, so it can be applied on create.
  const [roleTargetIndex, setRoleTargetIndex] = useState<number | null>(null);

  useEffect(() => {
    fetchPeople()
      .then(setPeople)
      .catch(() => setPeople([]));
    fetchMemberRoles()
      .then((roles) => {
        if (roles.length > 0) setRoleOptions(roles);
      })
      .catch(() => {
        // keep the defaults if the lookup endpoint is unavailable
      });
  }, []);

  function updateMember(i: number, patch: Partial<Person>) {
    const copy = [...members];
    copy[i] = { ...copy[i], ...patch };
    setMembers(copy);
  }

  // Chair and Secretariat are fixed positions: their role is already decided, so
  // those rows show it as a label rather than the picker. A row is "designated"
  // when it holds either — after a "Same as Chair" merge one row holds both.
  const chairIndex = members.findIndex((m) =>
    m.roles.some((r) => r.toLowerCase() === CHAIR_ROLE.toLowerCase()),
  );
  const secretariatIndex = members.findIndex((m) =>
    m.roles.some((r) => r.toLowerCase() === SECRETARIAT_ROLE.toLowerCase()),
  );

  // Chair/Secretariat are never offered in the picker — they are added by the
  // form itself, and assigning a second holder breaks the single-holder design.
  const assignableRoles = roleOptions.filter((r) => !isReservedRole(r));

  // Fold row `from` into row `into`: move any roles that aren't already there,
  // then drop the now-redundant row — one person, one row.
  function mergeRows(from: number, into: number, noticeText: string) {
    const merged = [...members];
    const target = merged[into];
    const rolesToMove = merged[from].roles.filter((r) => !target.roles.includes(r));
    merged[into] = { ...target, roles: [...target.roles, ...rolesToMove] };
    setMembers(merged.filter((_, i) => i !== from));
    setNotice(noticeText);
  }

  // "Same as Chair": this row is the same person as the Chair, so reuse the
  // duplicate-person fold instead of making the user retype their details.
  function sameAsChair(i: number) {
    if (chairIndex === -1 || i === chairIndex) return;
    const chairName = members[chairIndex].name.trim();
    mergeRows(
      i,
      chairIndex,
      `Same person as the Chair — the roles were combined onto ${
        chairName ? `${chairName}'s` : "the Chair's"
      } row.`,
    );
  }

  // Picking someone who is already on this group folds the two rows together
  // rather than creating a duplicate person entry, per the DTO contract.
  async function selectExisting(index: number, picked: PersonListItem) {
    const existingIndex = members.findIndex(
      (m, i) => i !== index && m.uuid === picked.uuid,
    );

    if (existingIndex === -1) {
      updateMember(index, {
        uuid: picked.uuid,
        name: `${picked.first_name} ${picked.last_name}`.trim(),
      });

      // Pull their stored details in so the submitter does not retype what the
      // registry already knows. A non-privileged caller gets the minimal public
      // view, which carries no contact fields — the row simply stays sparse,
      // and the backend no longer requires them for a resolved person.
      try {
        const detail = await fetchPerson(picked.uuid);
        updateMember(index, {
          uuid: picked.uuid,
          name: `${detail.first_name} ${detail.last_name}`.trim(),
          gender: detail.gender ?? "",
          email: detail.email ?? "",
          phone: detail.phone ?? "",
          // Stored with the "z" prefix; the form collects the digits only.
          zId: (detail.zID ?? "").replace(/^z/i, ""),
          representation: representationFromApi(detail.member_representation),
        });
      } catch {
        // Keep the identity we already set; the details stay blank.
      }
      return;
    }

    // Move this row's roles onto the row that person already occupies, then
    // drop the now-redundant row.
    mergeRows(
      index,
      existingIndex,
      `${picked.first_name} ${picked.last_name} is already on this group — their roles were combined.`,
    );
  }

  async function submitNewRole() {
    const name = newRoleName.trim();
    if (!name) {
      setRoleError("Name is required.");
      return;
    }
    if (isReservedRole(name)) {
      setRoleError(
        "Chair and Secretariat are assigned automatically — pick a different role name.",
      );
      return;
    }
    try {
      const roles = await createMemberRole(name, newRoleDescription.trim() || undefined);
      setRoleOptions(roles);
      if (roleTargetIndex !== null) {
        const member = members[roleTargetIndex];
        if (member && !member.roles.includes(name)) {
          updateMember(roleTargetIndex, { roles: [...member.roles, name] });
        }
      }
      setCreatingRole(false);
      setNewRoleName("");
      setNewRoleDescription("");
      setRoleError("");
    } catch {
      setRoleError("Could not create that role. Please try again.");
    }
  }

  return (
    <div className="space-y-6">
      <p className="text-sm text-gray-500">
        Every group needs at least one {CHAIR_ROLE} and one {SECRETARIAT_ROLE}. The
        same person may hold both — give them both roles on one row.
      </p>

      {notice && (
        <div className="rounded border border-blue-200 bg-blue-50 px-3 py-2 text-sm text-blue-700">
          {notice}
          <button
            type="button"
            onClick={() => setNotice("")}
            className="ml-2 text-blue-400 hover:text-blue-700"
          >
            ×
          </button>
        </div>
      )}

      {members.map((m, i) => {
        const designated = m.roles.some(isReservedRole);
        return (
          <div key={i} className="border-t border-gray-100 pt-6 first:border-t-0 first:pt-0">
            <div className="mb-3 flex items-center justify-between">
              <p className="text-sm font-semibold text-gray-800">
                {m.roles.length > 0 ? m.roles.join(" · ") : `Member ${i + 1}`}
              </p>
              <div className="flex items-center gap-4">
                {/* Only the distinct Secretariat row offers this. One-shot: the
                    row folds into the Chair's, so it is never rendered checked. */}
                {i === secretariatIndex &&
                  chairIndex !== -1 &&
                  secretariatIndex !== chairIndex && (
                    <label className="flex cursor-pointer items-center gap-1.5 text-xs text-gray-500">
                      <input
                        type="checkbox"
                        checked={false}
                        onChange={() => sameAsChair(i)}
                      />
                      Same as Chair
                    </label>
                  )}
                {/* Chair and Secretariat are structural and cannot be removed —
                    only optional common members can. */}
                {!designated && (
                  <button
                    type="button"
                    onClick={() => setMembers(members.filter((_, j) => j !== i))}
                    className="text-xs text-gray-400 hover:text-red-500"
                  >
                    Remove
                  </button>
                )}
              </div>
            </div>
            <PersonFields
              value={m}
              onChange={(patch) => updateMember(i, patch)}
              people={people}
              onSelectExisting={(picked) => selectExisting(i, picked)}
              roleOptions={assignableRoles}
              rolesLocked={designated}
              onCreateRole={(name) => {
                if (isReservedRole(name)) {
                  setNotice(
                    "Chair and Secretariat are assigned automatically and can't be added to another member.",
                  );
                  return;
                }
                setRoleTargetIndex(i);
                setNewRoleName(name);
                setNewRoleDescription("");
                setRoleError("");
                setCreatingRole(true);
              }}
            />
          </div>
        );
      })}

      <button
        type="button"
        onClick={() => setMembers([...members, blankPerson([DEFAULT_MEMBER_ROLE])])}
        className="text-sm text-blue-600 hover:underline"
      >
        + Add new member
      </button>

      <Modal
        open={creatingRole}
        title="Create a new role"
        onClose={() => setCreatingRole(false)}
        footer={
          <>
            <button
              type="button"
              onClick={() => setCreatingRole(false)}
              className="rounded border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={submitNewRole}
              className="rounded bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700"
            >
              Create
            </button>
          </>
        }
      >
        <div className="space-y-3">
          <FormField label="Role name" required>
            <input
              className={inp}
              value={newRoleName}
              onChange={(e) => setNewRoleName(e.target.value)}
              placeholder="e.g. Treasurer"
            />
          </FormField>
          <FormField label="Short description" optional>
            <textarea
              className={`${inp} resize-none`}
              rows={3}
              value={newRoleDescription}
              onChange={(e) => setNewRoleDescription(e.target.value)}
            />
          </FormField>
          <p className="text-xs text-gray-500">
            This role becomes available to every future ToR form.
          </p>
          {roleError && <p className="text-xs text-red-600">{roleError}</p>}
        </div>
      </Modal>
    </div>
  );
}
