/**
 * Wizard state <-> ToR form JSON.
 *
 * The wizard holds its fields as separate pieces of state so each step stays a
 * plain controlled component. Saving a draft and resuming one both need a
 * single serialisable object, so the conversion lives here rather than being
 * inlined in the submit handler.
 *
 * `collectForm` and `applyForm` are inverses and must be kept that way — the
 * round-trip test in `formAdapters.test.ts` is what enforces it.
 */

import { normaliseUrl } from "../../api/url";
import {
  blankPerson,
  CHAIR_ROLE,
  joinName,
  representationFlags,
  representationFromFlags,
  SECRETARIAT_ROLE,
  splitName,
} from "./types";
import type { Person, ReportEntry, ResourceEntry } from "./types";
import type { TorFormPayload, TorMember, TorRelation } from "../../types/governance";

// Bumped when the shape below changes incompatibly, so an old stored draft can
// be recognised rather than silently mis-rehydrated.
export const FORM_VERSION = 1;

export interface WizardFormState {
  groupName: string;
  entityType: string;
  purpose: string;
  responsibility: string;
  members: Person[];
  reportsTo: ReportEntry[];
  meetingFreq: string;
  meetingDur: string;
  resources: ResourceEntry[];
  validFrom: string;
  validTo: string;
}

/**
 * The two positions every group must fill. They are ordinary rows: if one
 * person holds both, the member picker merges them into a single row carrying
 * both roles.
 */
export function defaultMembers(): Person[] {
  return [blankPerson([CHAIR_ROLE]), blankPerson([SECRETARIAT_ROLE])];
}

function buildMember(p: Person): TorMember {
  return {
    uuid: p.uuid,
    // The one place the typed name is split; it stays whole until here.
    ...splitName(p.name),
    gender: p.gender,
    email: p.email,
    phone: p.phone,
    // The form collects the zID digits only; the backend expects the "z" prefix.
    zID: p.representation === "external" ? null : p.zId ? `z${p.zId}` : null,
    roles: p.roles,
    ...representationFlags(p.representation),
  };
}

function readMember(m: Partial<TorMember>): Person {
  return {
    uuid: m.uuid ?? null,
    name: joinName(m.first_name, m.last_name),
    gender: m.gender ?? "",
    email: m.email ?? "",
    phone: m.phone ?? "",
    // Stored with the "z" prefix, edited without it.
    zId: (m.zID ?? "").replace(/^z/i, ""),
    representation: representationFromFlags(m),
    roles: m.roles ?? [],
  };
}

/** Wizard state -> the ToR form JSON that is both saved and submitted. */
export function collectForm(state: WizardFormState): TorFormPayload {
  const relations: TorRelation[] = state.reportsTo
    .filter((r) => r.groupName.trim())
    .map((r) =>
      r.groupUuid
        ? {
            group_uuid: r.groupUuid,
            existing_group: true as const,
            note: r.note,
            // Ignored by the backend, kept so a reopened draft can show the name.
            group_name: r.groupName.trim(),
          }
        : { group_name: r.groupName.trim(), existing_group: false as const, note: r.note },
    );

  return {
    form_version: FORM_VERSION,
    group_name: state.groupName,
    entity_type: state.entityType,
    purpose: state.purpose,
    responsibilities: state.responsibility,
    members: state.members.map(buildMember),
    relations,
    meeting_frequency_per_year: Number(state.meetingFreq) || 0,
    meeting_duration_hour: Number(state.meetingDur) || 0,
    reference_links: state.resources
      .filter((r) => r.title.trim())
      .map((r) => ({ title: r.title, url: normaliseUrl(r.url) })),
    start_date: state.validFrom,
    review_date: state.validTo,
  };
}

/**
 * Stored form JSON -> wizard state, for resuming a draft or opening a form for
 * review. Everything is optional: a draft is saved unvalidated, so any field
 * may be missing.
 */
export function applyForm(form: Partial<TorFormPayload>): WizardFormState {
  const members = (form.members ?? []).map(readMember);

  return {
    groupName: form.group_name ?? "",
    entityType: form.entity_type ?? "",
    purpose: form.purpose ?? "",
    responsibility: form.responsibilities ?? "",
    // A draft saved before anyone was added would otherwise reopen with an
    // empty members step; fall back to the two positions every group needs.
    members: members.length > 0 ? members : defaultMembers(),
    reportsTo: (form.relations ?? []).map(
      (r): ReportEntry =>
        r.existing_group
          ? { groupName: r.group_name ?? "", groupUuid: r.group_uuid, note: r.note ?? "" }
          : { groupName: r.group_name, groupUuid: null, note: r.note ?? "" },
    ),
    // Numbers on the wire, strings in the inputs. 0 means "not answered" and
    // should show as empty rather than a literal "0".
    meetingFreq: form.meeting_frequency_per_year ? String(form.meeting_frequency_per_year) : "",
    meetingDur: form.meeting_duration_hour ? String(form.meeting_duration_hour) : "",
    resources: (form.reference_links ?? []).map(
      (l): ResourceEntry => ({ title: l.title, url: l.url }),
    ),
    validFrom: form.start_date ?? "",
    validTo: form.review_date ?? "",
  };
}
