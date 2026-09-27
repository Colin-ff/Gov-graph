import { useState } from "react";
import { FormField } from "./FormField";
import { ComboBox } from "../ui/ComboBox";
import { GENDER_OPTIONS, REPRESENTATION_OPTIONS } from "./types";
import type { Person, Representation } from "./types";
import type { PersonListItem } from "../../types/governance";

const inp =
  "w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:border-blue-500 disabled:bg-gray-100";

interface Props {
  value: Person;
  onChange: (patch: Partial<Person>) => void;
  // Everyone in the registry, for the name search.
  people: PersonListItem[];
  // Called when an existing person is picked, so the page can either fill this
  // row or redirect onto the row that person already occupies.
  onSelectExisting: (person: PersonListItem) => void;
  roleOptions: string[];
  onCreateRole: (name: string) => void;
  // A designated Chair/Secretariat row: its role is already known, so the roles
  // are shown as fixed labels with no picker and cannot be changed here.
  rolesLocked?: boolean;
}

export function PersonFields({
  value,
  onChange,
  people,
  onSelectExisting,
  roleOptions,
  onCreateRole,
  rolesLocked = false,
}: Props) {
  const [roleQuery, setRoleQuery] = useState("");
  const external = value.representation === "external";
  // A uuid means the picker matched someone already in the registry.
  const resolved = value.uuid !== null;

  const representationLabel = REPRESENTATION_OPTIONS.find(
    (o) => o.value === value.representation,
  )?.label;

  const storedDetails = [
    { label: "Gender", value: value.gender },
    { label: "Email", value: value.email },
    { label: "Phone", value: value.phone },
    { label: "zID", value: value.zId ? `z${value.zId}` : "" },
    { label: "Representation", value: representationLabel ?? "" },
  ].filter((d) => d.value);

  function setName(text: string) {
    // Stored verbatim — no trimming or splitting while typing, so spaces reach
    // the field. Editing also clears any resolved uuid: the row no longer
    // refers to the person that was picked.
    onChange({ uuid: null, name: text });
  }

  function toggleRole(role: string) {
    const has = value.roles.includes(role);
    onChange({
      roles: has ? value.roles.filter((r) => r !== role) : [...value.roles, role],
    });
  }

  return (
    <div className="space-y-3">
      <FormField label="Name" required>
        <ComboBox
          options={people.map((p) => ({
            value: p.uuid,
            label: `${p.first_name} ${p.last_name}`,
            sublabel: p.email,
          }))}
          query={value.name}
          onQueryChange={setName}
          onSelect={(o) => {
            const person = people.find((p) => p.uuid === o.value);
            if (person) onSelectExisting(person);
          }}
          placeholder="Search people, or type a new name"
        />
        <p className="mt-1 text-xs text-gray-400">
          Pick someone already in the registry, or type a name to add them.
        </p>
      </FormField>

      {/* A resolved person's details belong to their record, not to this ToR:
          the write path keeps the stored values and ignores anything sent here,
          so they are shown read-only rather than as editable fields that would
          silently do nothing. Fields the caller may not read are simply absent. */}
      {resolved ? (
        <div className="rounded border border-gray-200 bg-gray-50 px-3 py-2.5">
          <p className="mb-1.5 text-xs text-gray-500">
            Linked to an existing person — details come from their record.
          </p>
          {storedDetails.length > 0 ? (
            <dl className="space-y-1">
              {storedDetails.map((d) => (
                <div key={d.label} className="flex gap-3 text-xs">
                  <dt className="w-24 shrink-0 text-gray-400">{d.label}</dt>
                  <dd className="break-all text-gray-700">{d.value}</dd>
                </div>
              ))}
            </dl>
          ) : (
            <p className="text-xs text-gray-400">
              Their contact details are already on record.
            </p>
          )}
        </div>
      ) : (
      <>
      <div className="grid grid-cols-2 gap-3">
        <FormField label="Gender" required small>
          <select
            className={inp}
            value={value.gender}
            onChange={(e) => onChange({ gender: e.target.value })}
          >
            <option value="">—</option>
            {GENDER_OPTIONS.map((g) => (
              <option key={g} value={g}>
                {g}
              </option>
            ))}
          </select>
        </FormField>

        <FormField label="Email" required small>
          <input
            className={inp}
            type="email"
            value={value.email}
            onChange={(e) => onChange({ email: e.target.value })}
          />
        </FormField>
      </div>

      <FormField label="Member representation" required small>
        {/* Three mutually exclusive buckets — the diversity analytics reads
            these, so a member must sit in exactly one. */}
        <div className="inline-flex rounded-md border border-gray-300 p-0.5">
          {REPRESENTATION_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() =>
                onChange({
                  representation: opt.value as Representation,
                  // An external member has no zID to give.
                  ...(opt.value === "external" ? { zId: "" } : {}),
                })
              }
              className={`rounded px-3 py-1.5 text-sm ${
                value.representation === opt.value
                  ? "bg-blue-600 text-white"
                  : "text-gray-600 hover:bg-gray-50"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </FormField>

      <div className="grid grid-cols-2 gap-3">
        <FormField label="Phone" optional small>
          <input
            className={inp}
            type="tel"
            value={value.phone}
            onChange={(e) => onChange({ phone: e.target.value })}
          />
        </FormField>

        <FormField label="zID (no z)" required={!external} small>
          <input
            className={inp}
            value={value.zId}
            disabled={external}
            placeholder={external ? "Not applicable" : "1234567"}
            onChange={(e) => onChange({ zId: e.target.value })}
          />
        </FormField>
      </div>
      </>
      )}

      {/* A designated Chair/Secretariat row already has its role decided, so the
          role is shown as a fixed label with no picker. Common members choose
          their own — those roles describe this person's place in *this* group. */}
      {rolesLocked ? (
        <FormField label="Role in this group" small>
          <div className="flex flex-wrap gap-1">
            {value.roles.map((role) => (
              <span
                key={role}
                className="inline-flex items-center rounded-full bg-blue-50 px-2.5 py-1 text-xs font-medium text-blue-700"
              >
                {role}
              </span>
            ))}
          </div>
        </FormField>
      ) : (
        <FormField label="Roles in this group" required small>
          <div className="mb-2 flex flex-wrap gap-1">
            {value.roles.map((role) => (
              <span
                key={role}
                className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2.5 py-1 text-xs text-blue-700"
              >
                {role}
                <button
                  type="button"
                  aria-label={`Remove role ${role}`}
                  onClick={() => toggleRole(role)}
                  className="text-blue-400 hover:text-blue-700"
                >
                  ×
                </button>
              </span>
            ))}
            {value.roles.length === 0 && (
              <span className="text-xs text-gray-400">No roles yet</span>
            )}
          </div>
          <ComboBox
            options={roleOptions
              .filter((r) => !value.roles.includes(r))
              .map((r) => ({ value: r, label: r }))}
            query={roleQuery}
            onQueryChange={setRoleQuery}
            onSelect={(o) => {
              toggleRole(o.label);
              setRoleQuery("");
            }}
            placeholder="Add a role"
            createLabel={(q) => `+ Create new role “${q}”`}
            onCreate={(q) => {
              onCreateRole(q);
              setRoleQuery("");
            }}
          />
        </FormField>
      )}
    </div>
  );
}
