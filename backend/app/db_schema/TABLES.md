# Database Tables

This folder defines the SQLAlchemy models for the GovGraph backend. The models intentionally keep only table columns and foreign keys; query joins are written explicitly in services/routes.

## Core Entity Tables

### `users`
Stores application login/account records.

- `email` is the unique account identifier.
- `password` stores a hash generated with Werkzeug, not the raw password.
- `user_role` is a fixed system enum: `STAFF` or `SUPER_USER`.
- `is_active` gates login. Staff self-registration creates an active account; admin registration creates an account only after approval.
- `temp_token` is the persistent development token returned by login/register and replayed by the frontend as `X-Token`.

### `admin_registration_requests`
Stores self-service admin account requests while they wait for a current superuser to review them.

- `email`, `display_name`, and hashed `password` are copied into `users` only on approval.
- `requested_role` is currently `SUPER_USER`.
- `status` is a fixed enum: `pending_review`, `approved`, or `rejected`.
- `admin_comment`, `reviewed_by`, and `reviewed_at` store review information. `admin_comment` is required when rejecting.
- `created_at` and `updated_at` support the Admin Registry pending/history views.

### `persons`
Stores people who may belong to governance groups.

- Uses `uuid` as the public/canonical person identifier.
- Stores personal details such as name, gender, email, phone, zID, student flag, and external-member flag.
- `z_id` can be null for external people.

### `governance_groups`
Stores governance bodies such as committees, boards, working groups, and panels.

- Uses `uuid` as the public/canonical group identifier.
- `group_type_id` points to `group_types`.
- `status` is a fixed enum: `Active`, `Inactive`, `Archived`, or `Proposed`.
- Stores ToR-related fields such as purpose, responsibility, meeting frequency, duration, start date, and review date.

### `tor_submissions`
Stores a submitted ToR form as it moves through the review lifecycle.

- This table stores the form JSON only; uploaded source files are not stored here.
- `uuid` is the unique ToR submission UUID. It identifies the **submission**, not the group.
- `group_uuid` points at the `governance_groups` row this submission produced, once it has produced one. It is null while the submission is a draft (a draft never writes to the graph). It is a separate column rather than reusing `uuid` because a submission may **adopt** a `Proposed` group whose UUID was minted earlier by another group's ToR — so submission UUID and group UUID are not interchangeable.
- `group_name` stores the group name from the form. Nullable, since a draft may be saved before a name is typed.
- `submitted_by_email` stores the submitter's email. `users` has no UUID column and no link to `persons`, and email is already unique and indexed, so email is the identity used for "my submissions" scoping (the same convention as `viewer_email` in `group_service`).
- `status` is a fixed enum: `draft`, `pending_review`, `approved` or `rejected`.
- `form_json_data` stores the complete ToR form JSON.
- `admin_comment`, `reviewed_by`, and `reviewed_at` store review information. `admin_comment` is required when rejecting.
- `created_at`, `submitted_at` and `reviewed_at` are deliberately distinct: a draft has been created but not submitted, so a submission date cannot be derived from `created_at`.

## Type / Lookup Tables

### `group_types`
Stores configurable group/entity types, for example `Committee`, `Board`, or `Working Group`.

Users may add new group types later, so these are stored as data instead of hard-coded enums.

### `membership_role_types`
Stores configurable member role types, for example `Chair`, `Secretariat`, `Member`, `Treasurer`, or external roles.

Roles are stored as data because users may add new role types later.

### `relationship_types`
Stores configurable relationship types between groups, for example `Subgroup`, `Report to`, or `Work with`.

- `is_directed` records whether this relationship type has direction.
- Individual relationship rows do not store direction separately.

## Link / Association Tables

### `memberships`
Links one person to one governance group.

- `group_id` points to `governance_groups`.
- `person_id` points to `persons`.
- Role information is not stored directly here because one membership can have multiple roles.

### `membership_roles`
Links one membership to one role type.

This allows a person to hold multiple roles in the same group, such as `Chair` and `Member`.

### `group_relationships`
Links two governance groups together.

- `source_group_id` points to the source group.
- `target_group_id` points to the target group.
- `relationship_type_id` points to `relationship_types`.
- Direction rules come from the selected relationship type.

### `group_reference_links`
Stores external/reference links for a governance group.

This is separate from `governance_groups` because a group can have multiple links, such as ToR pages, RAMS records, or meeting minutes.
