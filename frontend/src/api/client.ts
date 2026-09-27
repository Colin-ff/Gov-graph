import axios from "axios";

import { getAuth } from "../auth/auth";
import type { AuthUser } from "../auth/auth";
import type {
  AdminRegistrationRequest,
  AdminRegistrationScope,
  GraphData,
  GovernanceGroup,
  OrganisationListItem,
  PersonListItem,
  PersonPublic,
  TorFormPayload,
  TorSubmission,
  TorSubmissionScope,
  TorSubmissionSummary,
} from "../types/governance";

const baseURL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:5000/api";

export const api = axios.create({ baseURL });

// Attach the Sprint-1 auth headers (X-User-Email + X-Token) to every request
// when the user is logged in, so protected endpoints like POST /api/tor resolve
// the caller. Reads from localStorage so it works outside React render.
api.interceptors.request.use((config) => {
  const auth = getAuth();
  if (auth) {
    config.headers.set("X-User-Email", auth.email);
    config.headers.set("X-Token", auth.token);
  }
  return config;
});

// Thin wrappers over the Sprint 1 endpoints. Extend as tickets land.

export async function login(email: string, password: string): Promise<AuthUser> {
  const { data } = await api.post<AuthUser>("/auth/login", { email, password });
  return data;
}

export interface RegisterPayload {
  email: string;
  displayName: string;
  password: string;
  userRole: string;
}

export type RegisterResult =
  | { kind: "authenticated"; user: AuthUser }
  | {
      kind: "pending_admin_review";
      message: string;
      request: AdminRegistrationRequest;
    };

export async function registerUser(payload: RegisterPayload): Promise<RegisterResult> {
  const { data, status } = await api.post<
    AuthUser | { status: "pending_review"; message: string; request: AdminRegistrationRequest }
  >("/register", payload);
  if (status === 202 && "request" in data) {
    return {
      kind: "pending_admin_review",
      message: data.message,
      request: data.request,
    };
  }
  return { kind: "authenticated", user: data as AuthUser };
}

export async function fetchGraph(): Promise<GraphData> {
  const { data } = await api.get<GraphData>("/graph");
  return data;
}

export async function fetchGroup(uuid: string): Promise<GovernanceGroup> {
  const { data } = await api.get<GovernanceGroup>(`/groups/${uuid}`);
  return data;
}

// Groups as the organisation_list DTO — feeds group search/typeahead controls.
// An optional `name` applies a case-insensitive substring filter server-side.
export async function fetchOrganisations(name?: string): Promise<OrganisationListItem[]> {
  const { data } = await api.get<{ organisations: OrganisationListItem[] }>("/groups", {
    params: name ? { name } : undefined,
  });
  return data.organisations;
}

// All people, as the person_list DTO — feeds person search/typeahead controls.
// Requires an authenticated caller (any role); the interceptor attaches the headers.
export async function fetchPeople(): Promise<PersonListItem[]> {
  const { data } = await api.get<{ people: PersonListItem[] }>("/person");
  return data.people;
}

export async function fetchPerson(uuid: string): Promise<PersonPublic> {
  const { data } = await api.get<PersonPublic>(`/person/${uuid}`);
  return data;
}

export interface EntityTypeList {
  // All types, prescribed (seeded) first then user-added.
  entityTypes: string[];
  // The subset that are prescribed, so the form can divide the two groups.
  prescribed: string[];
}

export async function fetchEntityTypes(): Promise<EntityTypeList> {
  const { data } = await api.get<{
    entity_types: string[];
    prescribed_entity_types?: string[];
  }>("/tor/entity_types");
  return {
    entityTypes: data.entity_types,
    prescribed: data.prescribed_entity_types ?? [],
  };
}

// Both create endpoints return the refreshed list, so the caller can drop the
// response straight into its options state without a follow-up GET.
export async function createEntityType(
  type_name: string,
  description?: string,
): Promise<EntityTypeList> {
  const { data } = await api.post<{
    entity_types: string[];
    prescribed_entity_types?: string[];
  }>("/tor/entity_types", {
    type_name,
    description,
  });
  return {
    entityTypes: data.entity_types,
    prescribed: data.prescribed_entity_types ?? [],
  };
}

export async function fetchMemberRoles(): Promise<string[]> {
  const { data } = await api.get<{ member_types: string[] }>("/tor/member_roles");
  return data.member_types;
}

export async function createMemberRole(
  type_name: string,
  description?: string,
): Promise<string[]> {
  const { data } = await api.post<{ member_types: string[] }>("/tor/member_roles", {
    type_name,
    description,
  });
  return data.member_types;
}

export async function createGroup(payload: TorFormPayload): Promise<{ uuid: string }> {
  const { data } = await api.post<{ uuid: string }>("/tor", payload);
  return data;
}

// Extracts a sparse partial ToR form from an uploaded document. Any field the
// document didn't clearly state is simply absent, so the result should be run
// through applyForm() exactly like a resumed draft — missing keys fall back
// to blank rather than needing special handling here.
export async function autofillTor(file: File): Promise<Partial<TorFormPayload>> {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await api.post<{ form_json_data: Partial<TorFormPayload> }>(
    "/tor/autofill",
    formData,
  );
  return data.form_json_data;
}

// ----- ToR submission lifecycle -------------------------------------------
// Scope is enforced server-side: "history" and "pending" 403 for a common user,
// and drafts are never returned org-wide, so these must not be treated as one
// list the client filters down.

export async function fetchSubmissions(
  scope: TorSubmissionScope,
): Promise<TorSubmissionSummary[]> {
  const { data } = await api.get<{ submissions: TorSubmissionSummary[] }>("/tor-submissions", {
    params: { scope },
  });
  return data.submissions;
}

export async function fetchSubmission(uuid: string): Promise<TorSubmission> {
  const { data } = await api.get<TorSubmission>(`/tor-submissions/${uuid}`);
  return data;
}

// Drafts are stored unvalidated, so the form is deliberately Partial here.
export async function createDraft(form: Partial<TorFormPayload>): Promise<TorSubmission> {
  const { data } = await api.post<TorSubmission>("/tor-submissions", {
    form_json_data: form,
  });
  return data;
}

export async function updateDraft(
  uuid: string,
  form: Partial<TorFormPayload>,
): Promise<TorSubmission> {
  const { data } = await api.put<TorSubmission>(`/tor-submissions/${uuid}`, {
    form_json_data: form,
  });
  return data;
}

// Runs the full ToR validation server-side, so this is where a 400 with
// per-field details comes from.
export async function submitDraft(uuid: string): Promise<TorSubmission> {
  const { data } = await api.post<TorSubmission>(`/tor-submissions/${uuid}/submit`);
  return data;
}

export async function approveSubmission(
  uuid: string,
  adminComment?: string,
): Promise<TorSubmission> {
  const { data } = await api.post<TorSubmission>(`/tor-submissions/${uuid}/approve`, {
    admin_comment: adminComment,
  });
  return data;
}

// The comment is required: rejection is terminal, so it is the only chance to
// tell the submitter why.
export async function rejectSubmission(
  uuid: string,
  adminComment: string,
): Promise<TorSubmission> {
  const { data } = await api.post<TorSubmission>(`/tor-submissions/${uuid}/reject`, {
    admin_comment: adminComment,
  });
  return data;
}

export async function deleteDraft(uuid: string): Promise<void> {
  await api.delete(`/tor-submissions/${uuid}`);
}

export async function fetchAdminRegistrations(
  scope: AdminRegistrationScope,
): Promise<AdminRegistrationRequest[]> {
  const { data } = await api.get<{ requests: AdminRegistrationRequest[] }>(
    "/admin-registrations",
    { params: { scope } },
  );
  return data.requests;
}

export async function approveAdminRegistration(
  id: number,
): Promise<AdminRegistrationRequest> {
  const { data } = await api.post<AdminRegistrationRequest>(
    `/admin-registrations/${id}/approve`,
  );
  return data;
}

export async function rejectAdminRegistration(
  id: number,
  adminComment: string,
): Promise<AdminRegistrationRequest> {
  const { data } = await api.post<AdminRegistrationRequest>(
    `/admin-registrations/${id}/reject`,
    { adminComment },
  );
  return data;
}

// Turn an axios error from a JSON endpoint into user-facing messages. The
// backend returns {error, details} on 400 (details maps field -> message).
export function apiErrorMessages(err: unknown): string[] {
  if (axios.isAxiosError(err)) {
    const data = err.response?.data as
      | { error?: string; details?: Record<string, string>; message?: string }
      | undefined;
    if (data?.details && Object.keys(data.details).length > 0) {
      return Object.entries(data.details).map(([field, msg]) => `${field}: ${msg}`);
    }
    if (err.response?.status === 401) {
      return ["You must be logged in to do that. Please log in and try again."];
    }
    if (err.response?.status === 403) {
      return ["You need superuser access to view this."];
    }
    if (data?.error) return [data.error];
    if (data?.message) return [data.message];
  }
  return ["Something went wrong. Please try again."];
}
