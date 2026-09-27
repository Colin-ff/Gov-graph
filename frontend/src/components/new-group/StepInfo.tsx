import { ChangeEvent, useEffect, useRef, useState } from "react";
import { FormField } from "./FormField";
import { ComboBox } from "../ui/ComboBox";
import { Modal } from "../ui/Modal";
import {
  apiErrorMessages,
  autofillTor,
  createEntityType,
  fetchEntityTypes,
  fetchOrganisations,
} from "../../api/client";
import type { OrganisationListItem, TorFormPayload } from "../../types/governance";

const inp =
  "w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:border-blue-500";

// Fallback list used until the backend type list loads (or if it fails). Mirrors
// the backend seed (db_init_seed.GROUP_TYPES) so the fallback is all-prescribed.
const DEFAULT_ENTITY_TYPES = [
  "Committee",
  "Board",
  "Working Group",
  "Advisory Panel",
  "Subcommittee",
  "Taskforces",
];

const USER_DEFINED_GROUP = "User-defined entity types";

export interface StepInfoProps {
  groupName: string;
  setGroupName: (v: string) => void;
  entityType: string;
  setEntityType: (v: string) => void;
  purpose: string;
  setPurpose: (v: string) => void;
  responsibility: string;
  setResponsibility: (v: string) => void;
  // A registered group with this name blocks the submission; the page owns that
  // state so it can also block "Next" and raise the toast.
  duplicateGroup: OrganisationListItem | null;
  setDuplicateGroup: (g: OrganisationListItem | null) => void;
  onDuplicate: (message: string) => void;
  // Called with the extracted (possibly sparse) form once autofill succeeds.
  onAutofill: (form: Partial<TorFormPayload>) => void;
  onAutofillError: (message: string) => void;
}

export function StepInfo({
  groupName,
  setGroupName,
  entityType,
  setEntityType,
  purpose,
  setPurpose,
  responsibility,
  setResponsibility,
  duplicateGroup,
  setDuplicateGroup,
  onDuplicate,
  onAutofill,
  onAutofillError,
}: StepInfoProps) {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [selectedToR, setSelectedToR] = useState<File | null>(null);
  const [autofilling, setAutofilling] = useState(false);

  const [entityTypes, setEntityTypes] = useState<string[]>(DEFAULT_ENTITY_TYPES);
  // On fallback every default is prescribed, so no divider shows until the API
  // returns a list that actually contains user-added types.
  const [prescribedTypes, setPrescribedTypes] = useState<string[]>(DEFAULT_ENTITY_TYPES);
  const [creatingType, setCreatingType] = useState(false);
  const [newTypeName, setNewTypeName] = useState("");
  const [newTypeDescription, setNewTypeDescription] = useState("");
  const [typeError, setTypeError] = useState("");

  const [groups, setGroups] = useState<OrganisationListItem[]>([]);

  useEffect(() => {
    fetchEntityTypes()
      .then(({ entityTypes: types, prescribed }) => {
        if (types.length > 0) {
          setEntityTypes(types);
          setPrescribedTypes(prescribed);
        }
      })
      .catch(() => {
        // keep the fallback list if the lookup endpoint is unavailable
      });
  }, []);

  // The registry is small enough to search client-side, and holding the whole
  // list avoids a request per keystroke.
  useEffect(() => {
    fetchOrganisations()
      .then(setGroups)
      .catch(() => setGroups([]));
  }, []);

  // Re-check on every edit: the name is only usable if nothing registered owns
  // it. A "proposed" match is fine — this submission will adopt that record.
  function checkName(name: string) {
    const match = groups.find(
      (g) => g.group_name.trim().toLowerCase() === name.trim().toLowerCase(),
    );
    if (match && match.status !== "proposed") {
      setDuplicateGroup(match);
      onDuplicate(`"${match.group_name}" is already registered. Pick a different name.`);
    } else {
      setDuplicateGroup(null);
    }
  }

  function onNameChange(name: string) {
    setGroupName(name);
    checkName(name);
  }

  async function submitNewType() {
    const name = newTypeName.trim();
    if (!name) {
      setTypeError("Name is required.");
      return;
    }
    try {
      const { entityTypes: types, prescribed } = await createEntityType(
        name,
        newTypeDescription.trim() || undefined,
      );
      setEntityTypes(types);
      setPrescribedTypes(prescribed);
      setEntityType(name);
      setCreatingType(false);
      setNewTypeName("");
      setNewTypeDescription("");
      setTypeError("");
    } catch {
      setTypeError("Could not create that type. Please try again.");
    }
  }

  const proposedMatch =
    duplicateGroup === null &&
    groups.find(
      (g) =>
        g.status === "proposed" &&
        g.group_name.trim().toLowerCase() === groupName.trim().toLowerCase(),
    );

  const handleDivClick = (): void => {
    if (autofilling) return;
    fileInputRef.current?.click();
  };

  const handleFileChange = async (event: ChangeEvent<HTMLInputElement>): Promise<void> => {
    const file = event.target.files?.[0];
    // Let the same file be re-picked after an error without the input's
    // change event failing to fire a second time.
    event.target.value = "";
    if (!file) return;

    setSelectedToR(file);
    setAutofilling(true);
    try {
      const form = await autofillTor(file);
      onAutofill(form);
    } catch (err) {
      onAutofillError(apiErrorMessages(err)[0]);
    } finally {
      setAutofilling(false);
    }
  };

  return (
    <div className="space-y-4">
      <FormField label="Upload ToR document" optional>
        <div
          className={`rounded-lg border-2 border-dashed border-gray-200 p-8 text-center ${
            autofilling ? "cursor-wait opacity-60" : "cursor-pointer hover:border-gray-300"
          }`}
          onClick={handleDivClick}
        >
          <div className="mb-1 text-3xl text-gray-300">⊕</div>
          {autofilling ? (
            <p className="text-sm text-gray-400">Extracting fields…</p>
          ) : selectedToR ? (
            <p className="text-sm text-gray-400">{selectedToR.name}</p>
          ) : (
            <p className="text-sm text-gray-400">Upload Your ToR Here</p>
          )}
        </div>
      </FormField>

      <FormField label="Group name" required>
        <ComboBox
          options={groups.map((g) => ({
            value: g.uuid,
            label: g.group_name,
            sublabel:
              g.status === "proposed"
                ? "Mentioned by another group — not registered yet"
                : g.chair
                  ? `Chair: ${g.chair}`
                  : undefined,
            muted: g.status === "proposed",
          }))}
          query={groupName}
          onQueryChange={onNameChange}
          onSelect={(o) => onNameChange(o.label)}
          placeholder="e.g. Academic Board"
        />
        {duplicateGroup && (
          <p className="mt-1 text-xs text-red-600">
            A group called “{duplicateGroup.group_name}” is already registered.
          </p>
        )}
        {proposedMatch && (
          <p className="mt-1 text-xs text-amber-600">
            “{proposedMatch.group_name}” was named by another group but never
            registered. Submitting will register it and keep its existing
            reporting lines.
          </p>
        )}
      </FormField>

      <FormField label="Entity type" required>
        <ComboBox
          options={entityTypes.map((t) => ({
            value: t,
            label: t,
            // Prescribed types carry no group; user-added ones sit under a
            // divider so submitters can tell the curated list apart.
            group: prescribedTypes.includes(t) ? undefined : USER_DEFINED_GROUP,
          }))}
          query={entityType}
          onQueryChange={setEntityType}
          onSelect={(o) => setEntityType(o.label)}
          placeholder="Select a type"
          createLabel={(q) => `+ Create new entity type “${q}”`}
          onCreate={(q) => {
            setNewTypeName(q);
            setNewTypeDescription("");
            setTypeError("");
            setCreatingType(true);
          }}
        />
      </FormField>

      <FormField label="Purpose" required>
        <textarea
          className={`${inp} resize-none`}
          rows={3}
          value={purpose}
          onChange={(e) => setPurpose(e.target.value)}
        />
      </FormField>

      <FormField label="Responsibilities" required>
        <textarea
          className={`${inp} resize-none`}
          rows={3}
          value={responsibility}
          onChange={(e) => setResponsibility(e.target.value)}
        />
      </FormField>

      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileChange}
        className="hidden"
        accept=".pdf,.docx"
        disabled={autofilling}
      />

      <Modal
        open={creatingType}
        title="Create a new entity type"
        onClose={() => setCreatingType(false)}
        footer={
          <>
            <button
              type="button"
              onClick={() => setCreatingType(false)}
              className="rounded border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={submitNewType}
              className="rounded bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700"
            >
              Create
            </button>
          </>
        }
      >
        <div className="space-y-3">
          <FormField label="Type name" required>
            <input
              className={inp}
              value={newTypeName}
              onChange={(e) => setNewTypeName(e.target.value)}
              placeholder="e.g. Taskforce"
            />
          </FormField>
          <FormField label="Short description" optional>
            <textarea
              className={`${inp} resize-none`}
              rows={3}
              value={newTypeDescription}
              onChange={(e) => setNewTypeDescription(e.target.value)}
              placeholder="What kind of body is this?"
            />
          </FormField>
          <p className="text-xs text-gray-500">
            This type becomes available to every future ToR form.
          </p>
          {typeError && <p className="text-xs text-red-600">{typeError}</p>}
        </div>
      </Modal>
    </div>
  );
}
