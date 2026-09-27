// Response shapes for the /api/analytics endpoints (see backend/app/routes/analytics.py
// and backend/app/routes/swagger_models.py). One interface per response body.

// Shared by all four top-N endpoints — backend emits {uuid, name, count}.
// (count is meeting-hours (float) or a group/subordinate count (int); number covers both.)
export interface RankedEntry {
  uuid: string;
  name: string;
  count: number;
}

// Orphan groups carry no count.
export interface GroupRef {
  uuid: string;
  name: string;
}

// Multiple-reporting-line groups: GroupRef + how many reporting lines.
export interface RankedGroup extends GroupRef {
  count: number;
}

// ----- single-subject drill-downs ----------------------------------------
export interface PersonLoad {
  uuid: string;
  meeting_hours: number;
}

export interface PersonGroupCount {
  uuid: string;
  group_count: number;
}

export interface GovernedCount {
  uuid: string;
  governed_group_count: number;
}

export interface GroupHours {
  uuid: string;
  governance_hours: number;
}

// ----- collections --------------------------------------------------------
export interface TopPeople {
  people: RankedEntry[];
}

export interface TopGroups {
  groups: RankedEntry[];
}

export interface OrphanGroups {
  groups: GroupRef[];
}

export interface MultipleReportingGroups {
  groups: RankedGroup[];
}

// ----- overlap ------------------------------------------------------------
export interface SharedMembers {
  group_a_uuid: string;
  group_b_uuid: string;
  shared_member_count: number;
}

export interface SharedMember {
  uuid: string;
  first_name: string;
  last_name: string;
}

export interface SharedMemberList {
  group_a_uuid: string;
  group_b_uuid: string;
  shared_member_count: number;
  shared_members: SharedMember[];
}

export interface OverlapPercentage {
  group_a_uuid: string;
  group_b_uuid: string;
  shared_member_count: number;
  overlap_percentage: number;
  relative_to: "group_b";
  description: string;
}

// ----- diversity ----------------------------------------------------------
// distribution keys are dynamic: gender labels plus "unknown" for null gender;
// {} for an empty / member-less group.
export interface GenderDistribution {
  uuid: string;
  distribution: Record<string, number>;
}

export interface RepresentationSplit {
  student: number;
  faculty: number;
  external: number;
}

export interface MemberRepresentation {
  uuid: string;
  // {} (Record<string, never>) for an empty / member-less group.
  representation: RepresentationSplit | Record<string, never>;
}

// ----- chain-of-command ---------------------------------------------------
// chain is a list of group UUIDs (most-powerful first), or null when unconnected.
// The backend auto-detects direction, so chain[0] may be the group passed as `to`.
export interface ChainOfCommand {
  from_uuid: string;
  to_uuid: string;
  connected: boolean;
  chain: string[] | null;
}
