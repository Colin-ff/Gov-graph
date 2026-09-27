# Purpose of the document
This document describes the key Data Transfer Object (DTO) the application should follow when frontend and backend communicate. Keep an eye on the use cases of each DTO.

> Dummy JSON objects in this folder can be modified when the application faces new use cases. There must be technical pitfalls existing as well.

> ### Warning
> This manual is the only **source of truth** for key DTOs, and everyone who tries to deviate from these DTOs during implementation should first change the examples in this folder first.

## person_details_superuser
The DTO that stores the person's information. It is used when superusers click on the hyperlinked full name of a person, and the backend needs to send personal information to the frontend.
> A person might hold multiple roles in an organisation; therefore, "role" is a list.

## person_public_reference
The DTO that stores brief person's information for public views. It is used when a common staff clicks on the hyperlinked full name of a person.

## organisation
The DTO that stores the organisation's information. It is universally accessible by all users when a user clicks on the name of an organisation, for example, when on the visualisation graph.

> ⚠️ This is a **server-produced read DTO** and is **universally readable**, so it must **not** ship internal actor UUIDs. `created_by_uuid` / `last_modified_by_uuid` are omitted here; only the timestamps are public. Expose actor identity only in privileged/admin views.
- `membership[]` mirrors the stored membership relation: each member carries `roles` (a **list**). The `uuid` is the authoritative identity — the embedded `first_name`/`last_name` are display snapshots, never an identity or write-back source.
- `relations[]` carries a `direction` field (`"reports_to"` — this group answers to the related one — or `"reported_to_by"` for the reverse). **Both directions are returned**, so a parent body can see what reports to it. Resolve related groups by `uuid` + direction, never by name.
- `entity_type` must be an **exact** value from `entity_types_tor` (Title Case, e.g. `"Committee"`, `"Working Group"` — not `"committee"`). `status` is a server-controlled enum (`active` / `inactive` / `archived` / `proposed`) and is never client-settable.

> ### 🔒 Meeting details are viewer-scoped
> `can_view_meetings` is **true** only for a SUPER_USER or for a caller whose account email matches a member of this group. `meeting_frequency_per_year`, `meeting_duration_hour` and `reference_links` are **omitted entirely** when it is false — reference links routinely point at minutes, so they are gated with the rest rather than left exposed. Clients must branch on `can_view_meetings`, not on the presence of a field.

## organisation_list
A list of organisations with uuid, group name, `status`, chair's full name, and secretariat's full name. This JSON object is returned to the front end whenever a client types in the search bar to search for an existing group. Accepts an optional `?name=` case-insensitive substring filter.

> `status` is what lets the ToR form decide between two very different outcomes for a name that already exists: a **registered** group (`active`/`inactive`/`archived`) blocks the submission, while a **`proposed`** one is adopted by it. Never make that call on name alone.

## person_list
A list of people with uuid, first name, last name, and email. This JSON object is returned to the front end whenever a client types in a person search bar (e.g. the analytics people picker or the ToR wizard's member search) so an existing person can be resolved back with their `uuid` already populated, and so two people sharing a name can be told apart.

> ⚠️ Carries `uuid` + name + `email` — email is included specifically to disambiguate same-name people in search results. `phone`, `zID` and `gender` stay off this list. Enumerating every person is more sensitive than a single lookup, so the endpoint requires an authenticated caller.

## auth_login
`POST /api/auth/login` verifies a user's email and password against the `users` table.

Request:

```json
{
  "email": "admin@unsw.edu.au",
  "password": "admin"
}
```

Success response:

```json
{
  "email": "admin@unsw.edu.au",
  "displayName": "GovGraph Admin",
  "userRole": "SUPER_USER",
  "token": "dev-token-admin"
}
```

Passwords are stored as hashes in the database. Later authenticated requests send `X-User-Email` and `X-Token`; both must match one active `users` row.

## register
`POST /api/register` creates staff accounts immediately and sends admin account requests into a review queue.

Request:

```json
{
  "email": "new.user@unsw.edu.au",
  "displayName": "New User",
  "password": "secret1",
  "userRole": "STAFF"
}
```

`userRole` must be exactly `STAFF` or `SUPER_USER`.

Staff success response (`201`) is the same auth profile as login, so the frontend logs the user in immediately:

```json
{
  "email": "new.user@unsw.edu.au",
  "displayName": "New User",
  "userRole": "STAFF",
  "token": "generated-token"
}
```

Admin registration response (`202`) does **not** include a login token:

```json
{
  "status": "pending_review",
  "message": "Admin registration submitted for review.",
  "request": {
    "id": 1,
    "email": "new.admin@unsw.edu.au",
    "displayName": "New Admin",
    "requestedRole": "SUPER_USER",
    "status": "pending_review",
    "adminComment": null,
    "reviewedBy": null,
    "reviewedAt": null,
    "createdAt": "2026-08-01T10:00:00",
    "updatedAt": "2026-08-01T10:00:00"
  }
}
```

## admin_registration_request
Superusers review admin registrations through:

- `GET /api/admin-registrations?scope=pending`
- `GET /api/admin-registrations?scope=history`
- `POST /api/admin-registrations/{id}/approve`
- `POST /api/admin-registrations/{id}/reject`

List response:

```json
{
  "requests": [
    {
      "id": 1,
      "email": "new.admin@unsw.edu.au",
      "displayName": "New Admin",
      "requestedRole": "SUPER_USER",
      "status": "pending_review",
      "adminComment": null,
      "reviewedBy": null,
      "reviewedAt": null,
      "createdAt": "2026-08-01T10:00:00",
      "updatedAt": "2026-08-01T10:00:00"
    }
  ]
}
```

Reject request body:

```json
{
  "adminComment": "Please use your UNSW staff email."
}
```

`adminComment` is required when rejecting. Approval creates an active `users` row from the request's hashed password; rejection keeps the request in history and does not create a login account.

## organisations_visualisation
This DTO will return a list of organisations as nodes that frontend demands to visualise governance structures.

## affiliations_visualisation
This DTO will return a list of affiliations as edges that frontend demands to visualise governance structures.

## nodes_edges_visualisation
This DTO will return a list of nodes and edges that frontend demands to visualise governance structures.

> ### The graph models exactly one relation
> Every edge is a **`Report to`** and reads `source reports to target` — the **target governs the source**. Earlier sprints also carried `Subgroup`, `Work with` and `Advice`; a graph mixing several edge meanings cannot be read without prior governance knowledge, so those are gone. Because there is only one kind of edge, the frontend draws an arrowhead instead of a type label.
>
> Nodes carry `status` and `entity_type`. `status: "proposed"` marks a group that exists only because another group's ToR named it as a reporting line — it must be visually distinguishable from a registered one, or the graph implies a formality that is not there.

## entity_types_tor
A list of entity types that is used to suggest users when filling in ToR form. Examples of entity types include: committees, boards, working groups, advisory panels, and subcommittees. The list might expand in the future if users create new entity types during form filling. This JSON object is returned to the frontend when users create a new ToR.

## member_types_tor
A list of **appointed** member types used to suggest roles when filling in the ToR form. It deliberately **excludes** `Chair` and `Secretariat` (special positions the form adds itself) and **excludes** external roles. Standardise on the term `Secretariat` (never "Secretary") everywhere.

## external_roles_tor
A list of role types for **external** members (people with no UNSW affiliation), e.g. `Consultant`, `External Advisor`. The form's role picker draws from this list (instead of `member_types_tor`) when a member is marked `is_external: true`.

## tor_form
A JSON object that frontend sends to the backend when the user fills in the ToR form and submits for admin's review.

> ⚠️ This object is a **transport DTO — the shape the form submits, NOT the shape you store.** Members are embedded as full blobs for submission convenience. The backend must normalise them into a person record + a membership relation (`membership(person_uuid, organisation_uuid, roles[])`) before persisting. Do not store the embedded blob as-is, or you will create a disconnected copy of a person on every submission and break the "click a person → see all their groups" reverse lookup.

### Naming conventions (applies to every schema, called out here because the form is the main write path)
- All keys are **snake_case**. No space-separated keys.
- One concept = one canonical key across all schemas. In particular: a group's name is always `group_name` (never `name`/`title`); the student flag is `is_student` (the old `if_student` was a typo); meeting cadence is `meeting_frequency_per_year` (unit is explicit — do not reintroduce a bare `meeting_frequency`); a person's roles within a group is the list `roles` (plural).

### Person identity — read this before writing match/create logic
A person can sit on many groups, and external members may have **no zID**. Identity therefore rests on `uuid`, not zID. Each member object carries up to three keys:

| Key | Meaning | Nullable? |
| --- | --- | --- |
| `uuid` | Canonical, system-issued person identity and the **only** reliable join key. | `null` **only** when the submitter is adding a brand-new person the backend has not seen — backend mints the uuid on create. |
| `zID` | UNSW natural key, format `z` + 7 digits. Unique **when present** (use a partial/sparse unique index — `null` must not collide). | `null` for external members (consultants, industry/other-institution advisors). |
| `email` | Required for everyone. Acts as the **fallback unique key** to dedupe people who have no zID. | Never null. |

**Backend match-or-create priority:** `uuid` → `zID` → `email` → no match ⇒ create a new person with a fresh `uuid`. The cheapest path is resolution at entry time: the frontend person-picker should search **all** people (staff + external) so an existing person is sent back with their `uuid` already populated and the backend never has to guess.

### Field notes / frontend warnings
- **`roles` is a list, one member entry per person.** A person holding multiple roles in this group (e.g. `["Member", "Treasurer"]`) is **one** member object with several roles — never duplicate the person into multiple rows. The frontend must dedupe on entry (match by `uuid`/`zID`): if the user re-adds an existing person, focus their existing row and add the role there. For internal members, role options come from `member_types_tor` **plus** `Chair` and `Secretariat` (which that list deliberately excludes); for members marked `is_external: true`, draw from `external_roles_tor` instead.
- **Member representation** is the triple `is_student` / `is_faculty` / `is_external`. Exactly **one** must be true — the buckets are mutually exclusive and collectively exhaustive, and the analytics diversity tab reads them, so zero or two is rejected with `members[i].member_representation`. The form labels `is_faculty` as "Staff"; the API and analytics call the same bucket `faculty`.
- **`is_external`** marks members with no UNSW affiliation. When `true`, `zID` is legitimately `null` — validate the `z`+7-digit zID format **only when `is_external` is false**, and require a zID for staff/students.
- **`gender`** is required on every member.
- **`relations`** entries are reporting lines. Each is either an existing group (`existing_group: true`, identified by `group_uuid`) or a group not yet registered (`existing_group: false`, supplying only `group_name` — no chair/secretariat details, which would be a lot to demand for a body you are merely naming). There is no `relation_type`: every entry is a `Report to`, and a client-supplied type is ignored. A group may declare **several** reporting lines.
- **`start_date` / `review_date`** are both required, and the start must be **strictly earlier** than the end. A start date in the past is fine — groups that have been running for years still need registering.

### Name collisions on submit
`group_name` is matched case-insensitively against existing groups:
- matches a **registered** group ⇒ `400` with `group_name: "A group with this name is already registered."`
- matches a **`proposed`** group ⇒ the submission **adopts that row in place**, preserving its `uuid` and every reporting line already pointing at it. Creating a fresh row instead would silently orphan those edges.
- a reporting line naming an unregistered group likewise reuses an existing match before creating a new `proposed` row, so one body never appears as several nodes.

### 🔒 Server-owned fields — never trust these from the client
The inbound form must **not** carry provenance/audit fields: `created_by_uuid`, `last_modified_by_uuid`, `created_timestamp`, `last_modified_timestamp`. The server stamps **identity from the authenticated session** and **time from its own clock**.
- **Backend:** strip these on ingest even if a client sends them — accepting a client-supplied `created_by_uuid` lets anyone forge authorship. Do not bind request body straight onto the stored entity; whitelist the client-writable fields.
- **Absent values:** never represent a missing timestamp as `""`. An empty string is falsy in JS so it slips through naive checks, but a date parser will choke on it. Use `null`, or better, **omit the field entirely**.
- These fields legitimately appear on **read** DTOs (e.g. `organisation`), where the server is the producer — they are write-forbidden, not read-forbidden. (Note: even on read DTOs, omit *actor* UUIDs from universally-readable views — see the `organisation` section.)

### 🧼 Untrusted input — treat every client free-text and URL field as hostile
Everything the form submits is later rendered in universally-readable views, so each string is a stored-XSS (and, for URLs, SSRF) vector.
- **`reference_links[].url`:** a **missing** scheme is filled in with `https://` rather than rejected — non-technical submitters type "www.unsw.edu.au/tor". An **explicit** scheme is left untouched and then allowlisted to `http`/`https`, so `javascript:` and `data:` are still rejected. Detect the scheme with a regex, **not** `urlparse().scheme`: that reads `example.com:8080/x` as scheme `example.com`. Equally, do not treat "no `://`" as "no scheme" — prepending `https://` to `javascript:alert(1)` would launder it into a URL that validates. The frontend mirrors this normalisation so the field shows what will be stored, and the backend **re-validates** (never trust the client check). If the server ever fetches these URLs, guard against SSRF (block loopback, private ranges, and cloud metadata addresses).
- **Free-text (`purpose`, `responsible`, `note`, `group_name`, names):** escape on output — never interpolate into HTML unescaped. Enforce server-side length limits.
