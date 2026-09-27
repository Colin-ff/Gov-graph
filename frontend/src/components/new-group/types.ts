// Where a member is drawn from. Mutually exclusive and collectively exhaustive:
// the backend rejects a member with zero or two of these set, and the analytics
// diversity tab buckets on them.
export type Representation = "student" | "staff" | "external";

export type Person = {
  // Set once the person is resolved against the registry, so the backend joins
  // to the existing record instead of matching by zID/email.
  uuid: string | null;
  // The name exactly as typed, kept as one string while the form is open.
  // Holding first/last separately here meant the displayed value had to be
  // recombined and trimmed on every render, which swallowed the space the user
  // had just pressed. It is split into first/last once, at submit.
  name: string;
  gender: string;
  email: string;
  phone: string;
  zId: string;
  representation: Representation | "";
  roles: string[];
};

export type ReportEntry = {
  groupName: string;
  // Set when the named group is already in the registry. Null means it is not
  // registered yet and the backend will record it as proposed.
  groupUuid: string | null;
  note: string;
};

export type ResourceEntry = { title: string; url: string };

export const blankPerson = (roles: string[] = []): Person => ({
  uuid: null,
  name: "",
  gender: "",
  email: "",
  phone: "",
  zId: "",
  representation: "",
  roles,
});

export const blankReport = (): ReportEntry => ({
  groupName: "",
  groupUuid: null,
  note: "",
});

/**
 * Split a typed name into the first/last pair the API stores.
 *
 * Everything after the first space is the surname, so "Mary Anne van der Berg"
 * keeps "Anne van der Berg" together instead of dropping the middle of it.
 * Runs once at submit — never while the user is typing, or the round-trip would
 * eat their spaces.
 */
export function splitName(name: string): { first_name: string; last_name: string } {
  const cleaned = name.trim().replace(/\s+/g, " ");
  const gap = cleaned.indexOf(" ");
  return gap === -1
    ? { first_name: cleaned, last_name: "" }
    : { first_name: cleaned.slice(0, gap), last_name: cleaned.slice(gap + 1) };
}

/**
 * Inverse of `splitName`, for rehydrating a saved draft.
 *
 * `splitName` normalises whitespace and splits at the first space, with the
 * surname taking the whole remainder — so rejoining with a single space
 * reproduces exactly what it stored. Runs once on load, never while typing.
 */
export function joinName(first?: string | null, last?: string | null): string {
  return [first, last].filter(Boolean).join(" ");
}

// "staff" is the term the form uses; the API and analytics call the same bucket
// "faculty". Translate here so the wording stays consistent in each place.
export function representationFlags(representation: Representation | "") {
  return {
    is_student: representation === "student",
    is_faculty: representation === "staff",
    is_external: representation === "external",
  };
}

// Inverse of `representationFlags`: the API calls the staff bucket "faculty".
export function representationFromApi(value?: string): Representation | "" {
  if (value === "student" || value === "external") return value;
  if (value === "faculty") return "staff";
  return "";
}

// Inverse of `representationFlags` for the boolean triple a ToR member carries.
// A draft may legitimately have none set — the user had not chosen yet.
export function representationFromFlags(flags: {
  is_student?: boolean;
  is_faculty?: boolean;
  is_external?: boolean;
}): Representation | "" {
  if (flags.is_student) return "student";
  if (flags.is_faculty) return "staff";
  if (flags.is_external) return "external";
  return "";
}

export const REPRESENTATION_OPTIONS: { value: Representation; label: string }[] = [
  { value: "student", label: "Student" },
  { value: "staff", label: "Staff" },
  { value: "external", label: "External" },
];

export const GENDER_OPTIONS = ["Female", "Male", "Non-binary", "Prefer not to say"];

// The form adds these itself; every other role comes from the registry's
// configurable list.
export const CHAIR_ROLE = "Chair";
export const SECRETARIAT_ROLE = "Secretariat";

// Chair and Secretariat are single-holder, structural positions. Keep each only
// on the first row that holds it and strip any later duplicate, so ingested data
// (an old draft, an autofilled form) can never carry a second Chair/Secretariat
// onto a common member. Returns the same array when nothing needs changing.
export function dedupeDesignatedRoles(members: Person[]): Person[] {
  let chairSeen = false;
  let secretariatSeen = false;
  let changed = false;

  const cleaned = members.map((m) => {
    const roles = m.roles.filter((role) => {
      const lower = role.toLowerCase();
      if (lower === CHAIR_ROLE.toLowerCase()) {
        if (chairSeen) return false;
        chairSeen = true;
        return true;
      }
      if (lower === SECRETARIAT_ROLE.toLowerCase()) {
        if (secretariatSeen) return false;
        secretariatSeen = true;
        return true;
      }
      return true;
    });
    if (roles.length === m.roles.length) return m;
    changed = true;
    return { ...m, roles };
  });

  return changed ? cleaned : members;
}
