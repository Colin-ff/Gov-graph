// Shape returned by GET /api/graph
export interface GraphNode {
  uuid: string;
  group_name: string;
  // "proposed" means another group's ToR named this body as its reporting line,
  // but nobody has registered it yet.
  status?: string;
  entity_type?: string | null;
}

// The graph models exactly one relation: source reports to target, so the
// target is the governing body.
export interface GraphRelation {
  source_uuid: string;
  target_uuid: string;
  relation_type: string;
  directed?: boolean;
}

export interface GraphData {
  nodes: GraphNode[];
  relations: GraphRelation[];
}

// Shape returned by GET /api/person/:uuid
export interface AffiliatedGroup {
  group_uuid: string;
  group_name: string;
  roles: string[];
}

export interface PersonPublic {
  uuid: string;
  first_name: string;
  last_name: string;
  affiliated_groups: AffiliatedGroup[];
  // Present only in the superuser view (person_details_superuser).
  gender?: string | null;
  email?: string;
  phone?: string | null;
  zID?: string | null;
  is_student?: boolean;
  is_external?: boolean;
  is_faculty?: boolean;
  member_representation?: string;
}

// Shape returned by GET /api/groups/:uuid
export interface OrgMember {
  uuid: string;
  first_name: string;
  last_name: string;
  roles: string[];
}

export interface OrgRelation {
  uuid: string;
  group_name: string;
  relation_type: string;
  // "reports_to": this group answers to the related one.
  // "reported_to_by": the related one answers to this group.
  direction?: "reports_to" | "reported_to_by";
}

export interface ReferenceLink {
  title: string;
  url: string;
}

// One entry in POST /api/tor/check-duplicates's `possible_duplicates` list.
export interface PossibleDuplicateGroup {
  uuid: string;
  group_name: string;
  score: number;
}

export interface GovernanceGroup {
  uuid: string;
  group_name: string;
  entity_type: string;
  status: string;
  purpose: string | null;
  responsibilities: string | null;
  membership?: OrgMember[];
  relations?: OrgRelation[];
  start_date?: string | null;
  review_date?: string | null;
  // True for a superuser or a member of this group. The three fields below are
  // present only when it is true.
  can_view_meetings?: boolean;
  meeting_frequency_per_year?: number | null;
  meeting_duration_hour?: number | null;
  reference_links?: ReferenceLink[];
}

// Shape returned by GET /api/groups (organisation_list DTO) — feeds group search/typeahead.
export interface OrganisationListItem {
  uuid: string;
  group_name: string;
  // "proposed" groups may be adopted by a ToR submission; registered ones may not.
  status: string;
  chair: string | null;
  secretariat: string | null;
}

// Shape returned by GET /api/person (person_list DTO) — feeds person search/typeahead.
export interface PersonListItem {
  uuid: string;
  first_name: string;
  last_name: string;
  email: string;
}

// DTO sent to the backend when submitting a new ToR form (see data_transfer_object_examples/tor/tor_form.json).
export interface TorMember {
  uuid: string | null;
  first_name: string;
  last_name: string;
  gender: string;
  email: string;
  phone: string;
  zID: string | null;
  roles: string[];
  // Exactly one of these three must be true — the backend rejects zero or two.
  is_student: boolean;
  is_faculty: boolean;
  is_external: boolean;
}

// A reporting line pointing at a group already in the registry.
export interface TorRelationExisting {
  group_uuid: string;
  existing_group: true;
  note?: string;
  // Display-only echo of the resolved group's name. The backend keys off
  // group_uuid and ignores this, but a saved draft needs it to show the name
  // again when the form is reopened.
  group_name?: string;
}

// A reporting line naming a group nobody has registered yet. Only the name is
// needed — the backend records it as "proposed" so it still appears in the graph.
export interface TorRelationNew {
  group_name: string;
  existing_group: false;
  note?: string;
}

export type TorRelation = TorRelationExisting | TorRelationNew;

export interface TorReferenceLink {
  title: string;
  url: string;
}

export interface TorFormPayload {
  group_name: string;
  entity_type: string;
  purpose: string;
  responsibilities: string;
  members: TorMember[];
  relations: TorRelation[];
  meeting_frequency_per_year: number;
  meeting_duration_hour: number;
  reference_links: TorReferenceLink[];
  start_date: string;
  review_date: string;
  // Stamped so a later change to the wizard's shape can migrate old drafts
  // instead of failing to rehydrate them.
  form_version?: number;
}

// ----- ToR submission lifecycle -------------------------------------------

// Draft -> Pending Review -> Result (Approved / Rejected).
export type TorSubmissionStatus = "draft" | "pending_review" | "approved" | "rejected";

// What list endpoints return: everything except the form JSON, which is far too
// large to ship per row.
export interface TorSubmissionSummary {
  uuid: string;
  // The group this submission produced. Null while it is still a draft, and
  // also once a rejected submission's group has been removed from the graph.
  group_uuid: string | null;
  group_name: string | null;
  status: TorSubmissionStatus;
  submitted_by_email: string | null;
  admin_comment: string | null;
  reviewed_by: string | null;
  reviewed_at: string | null;
  created_at: string;
  updated_at: string;
  // Null while a draft — a draft has been started but never submitted, which is
  // why the registry falls back to created_at for those rows.
  submitted_at: string | null;
}

export interface TorSubmission extends TorSubmissionSummary {
  // Partial while a draft: the backend does not validate a draft's contents.
  form_json_data: Partial<TorFormPayload>;
}

// Superuser-only scopes are rejected with 403 for a common user, so the caller
// must pick the one matching its view rather than filtering client-side.
export type TorSubmissionScope = "mine" | "history" | "pending";

// ----- Admin registration review ------------------------------------------

export type AdminRegistrationStatus = "pending_review" | "approved" | "rejected";
export type AdminRegistrationScope = "pending" | "history";

export interface AdminRegistrationRequest {
  id: number;
  email: string;
  displayName: string;
  requestedRole: "SUPER_USER";
  status: AdminRegistrationStatus;
  adminComment: string | null;
  reviewedBy: string | null;
  reviewedAt: string | null;
  createdAt: string;
  updatedAt: string;
}
