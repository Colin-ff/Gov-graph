// Thin wrappers over the 16 /api/analytics endpoints. Kept separate from
// client.ts so that module doesn't balloon. Imports the shared `api` instance
// so the auth interceptor (X-User-Email / X-Token) applies — every analytics
// endpoint is SUPER_USER-only.
import { api } from "./client";
import type {
  ChainOfCommand,
  GenderDistribution,
  GovernedCount,
  GroupHours,
  MemberRepresentation,
  MultipleReportingGroups,
  OrphanGroups,
  OverlapPercentage,
  PersonGroupCount,
  PersonLoad,
  SharedMemberList,
  SharedMembers,
  TopGroups,
  TopPeople,
} from "../types/analytics";

// ----- Person burden ------------------------------------------------------
export async function fetchTopGovernanceLoad(n: number): Promise<TopPeople> {
  const { data } = await api.get<TopPeople>("/analytics/people/top-governance-load", {
    params: { n },
  });
  return data;
}

export async function fetchTopGroupCount(n: number): Promise<TopPeople> {
  const { data } = await api.get<TopPeople>("/analytics/people/top-group-count", {
    params: { n },
  });
  return data;
}

export async function fetchPersonGovernanceLoad(uuid: string): Promise<PersonLoad> {
  const { data } = await api.get<PersonLoad>(`/analytics/people/${uuid}/governance-load`);
  return data;
}

export async function fetchPersonGroupCount(uuid: string): Promise<PersonGroupCount> {
  const { data } = await api.get<PersonGroupCount>(`/analytics/people/${uuid}/group-count`);
  return data;
}

// ----- Group concentration ------------------------------------------------
export async function fetchTopGovernedGroupCount(n: number): Promise<TopGroups> {
  const { data } = await api.get<TopGroups>("/analytics/groups/top-governed-group-count", {
    params: { n },
  });
  return data;
}

export async function fetchTopGovernanceHours(n: number): Promise<TopGroups> {
  const { data } = await api.get<TopGroups>("/analytics/groups/top-governance-hours", {
    params: { n },
  });
  return data;
}

export async function fetchGroupGovernedCount(uuid: string): Promise<GovernedCount> {
  const { data } = await api.get<GovernedCount>(
    `/analytics/groups/${uuid}/governed-group-count`,
  );
  return data;
}

export async function fetchGroupGovernanceHours(uuid: string): Promise<GroupHours> {
  const { data } = await api.get<GroupHours>(`/analytics/groups/${uuid}/governance-hours`);
  return data;
}

// ----- Structural pitfalls ------------------------------------------------
export async function fetchOrphanGroups(): Promise<OrphanGroups> {
  const { data } = await api.get<OrphanGroups>("/analytics/orphan-groups");
  return data;
}

export async function fetchMultipleReportingGroups(): Promise<MultipleReportingGroups> {
  const { data } = await api.get<MultipleReportingGroups>(
    "/analytics/multiple-reporting-line-groups",
  );
  return data;
}

// ----- Overlapped duties --------------------------------------------------
export async function fetchOverlapPercentage(
  groupA: string,
  groupB: string,
): Promise<OverlapPercentage> {
  const { data } = await api.get<OverlapPercentage>("/analytics/overlap/percentage", {
    params: { group_a: groupA, group_b: groupB },
  });
  return data;
}

export async function fetchSharedMembersCount(
  groupA: string,
  groupB: string,
): Promise<SharedMembers> {
  const { data } = await api.get<SharedMembers>("/analytics/overlap/shared-members", {
    params: { group_a: groupA, group_b: groupB },
  });
  return data;
}

export async function fetchSharedMemberList(
  groupA: string,
  groupB: string,
): Promise<SharedMemberList> {
  const { data } = await api.get<SharedMemberList>("/analytics/overlap/shared-member-list", {
    params: { group_a: groupA, group_b: groupB },
  });
  return data;
}

// ----- Diversity & representation -----------------------------------------
export async function fetchGenderDistribution(uuid: string): Promise<GenderDistribution> {
  const { data } = await api.get<GenderDistribution>(
    `/analytics/groups/${uuid}/gender-distribution`,
  );
  return data;
}

export async function fetchMemberRepresentation(uuid: string): Promise<MemberRepresentation> {
  const { data } = await api.get<MemberRepresentation>(
    `/analytics/groups/${uuid}/member-representation`,
  );
  return data;
}

// ----- Chain-of-command ---------------------------------------------------
export async function fetchChainOfCommand(from: string, to: string): Promise<ChainOfCommand> {
  const { data } = await api.get<ChainOfCommand>("/analytics/chain-of-command", {
    params: { from, to },
  });
  return data;
}
