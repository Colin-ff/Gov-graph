from collections import deque

from app.db_schema import (
    REPORT_TO_TYPE_NAME,
    GovernanceGroup,
    GroupRelationship,
    Membership,
    Person,
    RelationshipType,
)
from app.extensions import db


def _find_group_by_uuid(group_uuid: str) -> GovernanceGroup | None:
    """Return a group by public uuid, or None when it does not exist."""
    return GovernanceGroup.query.filter_by(uuid=group_uuid).first()


def group_exists(group_uuid: str) -> bool:
    """True when a governance group with this public uuid exists."""
    return _find_group_by_uuid(group_uuid) is not None


def person_exists(person_uuid: str) -> bool:
    """True when a person with this public uuid exists."""
    return Person.query.filter_by(uuid=person_uuid).first() is not None


def _get_group_members(group_uuid: str) -> list[Person]:
    group = _find_group_by_uuid(group_uuid)
    if group is None:
        return []

    return (
        db.session.query(Person)
        .join(Membership, Membership.person_id == Person.id)
        .filter(Membership.group_id == group.id)
        .all()
    )


# Governance(person) button:


# Top X people by number of governance groups
def get_top_people_by_group_count(person_number: int) -> list[dict]:
    if person_number <= 0:
        return []

    rows = (
        db.session.query(
            Person.uuid,
            Person.first_name,
            Person.last_name,
            db.func.count(Membership.group_id).label("group_count"),
        )
        .join(Membership, Membership.person_id == Person.id)
        .group_by(Person.id, Person.uuid)
        .order_by(db.func.count(Membership.group_id).desc(), Person.uuid)
        .limit(person_number)
        .all()
    )
    return [
        {
            "uuid": uuid,
            "name": f"{first_name} {last_name}",
            "count": group_count,
        }
        for uuid, first_name, last_name, group_count in rows
    ]


# Top X people by yearly meeting hours
def get_top_people_by_meeting_hours(person_number: int) -> list[dict]:
    if person_number <= 0:
        return []

    burdens: dict[str, dict] = {}
    rows = (
        db.session.query(Person.uuid, Person.first_name, Person.last_name, GovernanceGroup)
        .join(Membership, Membership.person_id == Person.id)
        .join(GovernanceGroup, GovernanceGroup.id == Membership.group_id)
        .all()
    )
    for person_uuid, first_name, last_name, group in rows:
        if person_uuid not in burdens:
            burdens[person_uuid] = {
                "uuid": person_uuid,
                "name": f"{first_name} {last_name}",
                "count": 0,
            }
        burdens[person_uuid]["count"] += get_number_of_governance_hours_of_a_group(group.uuid)

    return sorted(burdens.values(), key=lambda item: (-item["count"], item["uuid"]))[:person_number]


# Number of governance groups a person belongs to
def get_number_of_groups_a_person_belongs(person_uuid: str) -> int:
    person = Person.query.filter_by(uuid=person_uuid).first()
    if person is None:
        return 0

    return Membership.query.filter_by(person_id=person.id).count()


# Total meeting hours a person has attended per year
def get_total_meeting_hours_for_a_person(person_uuid: str) -> float:
    person = Person.query.filter_by(uuid=person_uuid).first()
    if person is None:
        return 0.0

    groups = (
        db.session.query(GovernanceGroup)
        .join(Membership, Membership.group_id == GovernanceGroup.id)
        .filter(Membership.person_id == person.id)
        .all()
    )
    return sum(
        float(group.meeting_frequency_per_year * group.meeting_duration_hour)
        if group.meeting_frequency_per_year is not None and group.meeting_duration_hour is not None
        else 0.0
        for group in groups
    )


# Governance Effort Concentration：


# Total number of governance groups report to a group.
def get_number_of_governance_groups_under_control(group_uuid: str) -> int:
    group = _find_group_by_uuid(group_uuid)
    if group is None:
        return 0

    return (
        db.session.query(GroupRelationship)
        .join(
            RelationshipType,
            RelationshipType.id == GroupRelationship.relationship_type_id,
        )
        .filter(GroupRelationship.target_group_id == group.id)
        .filter(RelationshipType.type_name == REPORT_TO_TYPE_NAME)
        .count()
    )


# Top X groups by number of subordinate/reporting groups.
def get_top_groups_by_under_control_count(group_number: int) -> list[dict]:
    if group_number <= 0:
        return []

    groups = GovernanceGroup.query.order_by(GovernanceGroup.uuid).all()
    burdens = [
        {
            "uuid": group.uuid,
            "name": group.group_name,
            "count": get_number_of_governance_groups_under_control(group.uuid),
        }
        for group in groups
    ]
    return sorted(burdens, key=lambda item: (-item["count"], item["uuid"]))[:group_number]


# Total governance meeting hours of a group per year.
def get_number_of_governance_hours_of_a_group(group_uuid: str) -> float:
    group = _find_group_by_uuid(group_uuid)
    if group is None:
        return 0.0
    if group.meeting_frequency_per_year is None or group.meeting_duration_hour is None:
        return 0.0

    return float(group.meeting_frequency_per_year * group.meeting_duration_hour)


# Top X groups by yearly meeting hours.
def get_top_groups_by_governance_hours(group_number: int) -> list[dict]:
    if group_number <= 0:
        return []

    groups = GovernanceGroup.query.order_by(GovernanceGroup.uuid).all()
    burdens = [
        {
            "uuid": group.uuid,
            "name": group.group_name,
            "count": (
                float(group.meeting_frequency_per_year * group.meeting_duration_hour)
                if group.meeting_frequency_per_year is not None
                and group.meeting_duration_hour is not None
                else 0.0
            ),
        }
        for group in groups
    ]
    return sorted(burdens, key=lambda item: (-item["count"], item["uuid"]))[:group_number]


# Unusual Governance Relations:


# Return all groups that do not report to any other group.
def get_all_orphan_groups() -> list[dict]:
    report_to_type = RelationshipType.query.filter_by(type_name=REPORT_TO_TYPE_NAME).first()
    if report_to_type is None:
        groups = GovernanceGroup.query.order_by(GovernanceGroup.uuid).all()
    else:
        reporting_group_ids = (
            db.session.query(GroupRelationship.source_group_id)
            .filter(GroupRelationship.relationship_type_id == report_to_type.id)
            .scalar_subquery()
        )
        groups = (
            GovernanceGroup.query.filter(~GovernanceGroup.id.in_(reporting_group_ids))
            .order_by(GovernanceGroup.uuid)
            .all()
        )

    return [{"uuid": group.uuid, "name": group.group_name} for group in groups]


# Groups with two or more outgoing "Report to" relationships.
# Return [uuid,name,count] list for all the group, and order by count.
def get_all_multiple_reporting_line_groups() -> list[dict]:
    report_to_type = RelationshipType.query.filter_by(type_name=REPORT_TO_TYPE_NAME).first()
    if report_to_type is None:
        return []

    rows = (
        db.session.query(
            GovernanceGroup.uuid,
            GovernanceGroup.group_name,
            db.func.count(GroupRelationship.target_group_id).label("report_to_count"),
        )
        .join(GroupRelationship, GroupRelationship.source_group_id == GovernanceGroup.id)
        .filter(GroupRelationship.relationship_type_id == report_to_type.id)
        .group_by(GovernanceGroup.id, GovernanceGroup.uuid, GovernanceGroup.group_name)
        .having(db.func.count(GroupRelationship.target_group_id) >= 2)
        .order_by(db.func.count(GroupRelationship.target_group_id).desc(), GovernanceGroup.uuid)
        .all()
    )

    return [
        {
            "uuid": uuid,
            "name": group_name,
            "count": report_to_count,
        }
        for uuid, group_name, report_to_count in rows
    ]


# Inefficient Overlapping Members:

def get_shared_members_between_two_groups(group_a_uuid: str, group_b_uuid: str) -> set:
    group_a = _find_group_by_uuid(group_a_uuid)
    group_b = _find_group_by_uuid(group_b_uuid)
    if group_a is None or group_b is None:
        return 0

    group_a_members = {
        person_id
        for (person_id,) in db.session.query(Membership.person_id)
        .filter(Membership.group_id == group_a.id)
        .all()
    }
    group_b_members = {
        person_id
        for (person_id,) in db.session.query(Membership.person_id)
        .filter(Membership.group_id == group_b.id)
        .all()
    }
    return group_a_members & group_b_members

def get_number_of_shared_members_between_two_groups(group_a_uuid: str, group_b_uuid: str) -> int:
    return len(get_shared_members_between_two_groups(group_a_uuid, group_b_uuid))

# return the percentage of members in group A that are also members of group B
def get_percentage_of_membership_overlapping_relevant_to_group_a(
    group_a_uuid: str, group_b_uuid: str
) -> float:
    group_a = _find_group_by_uuid(group_a_uuid)
    if group_a is None:
        return 0.0

    group_a_member_count = Membership.query.filter_by(group_id=group_a.id).count()
    if group_a_member_count == 0:
        return 0.0

    shared_member_count = get_number_of_shared_members_between_two_groups(
        group_a_uuid, group_b_uuid
    )
    return shared_member_count / group_a_member_count * 100


# Diversity:


def get_gender_distribution_of_a_group(group_uuid: str) -> dict:
    members = _get_group_members(group_uuid)
    if not members:
        return {}

    counts: dict[str, int] = {}
    for member in members:
        gender = member.gender or "unknown"
        counts[gender] = counts.get(gender, 0) + 1

    total = len(members)
    return {gender: count / total * 100 for gender, count in sorted(counts.items())}


def get_member_representation_of_a_group(group_uuid: str) -> dict:
    """Return the percentage split of a group's members across student,
    faculty, and external representation.

    Internal members who are not students are counted as faculty, so the three
    buckets always sum to 100% for a non-empty group. Returns an empty dict when
    the group is unknown or has no members.
    """
    members = _get_group_members(group_uuid)
    if not members:
        return {}

    counts = {
        "student": 0,
        "faculty": 0,
        "external": 0,
    }
    for member in members:
        if member.is_external:
            counts["external"] += 1
        elif member.is_student:
            counts["student"] += 1
        else:
            counts["faculty"] += 1

    total = len(members)
    return {source: count / total * 100 for source, count in counts.items()}


# Chain-of-command Intelligence：


def _get_list_of_groups_under_control(group_uuid: str) -> list[str]:
    """Return the uuids of groups that directly report to (are controlled by) the given group.

    A relationship ``source --"Report to"--> target`` means the target controls
    the source, so the groups under ``group_uuid`` are the sources whose
    relationship targets it.
    """
    group = _find_group_by_uuid(group_uuid)
    if group is None:
        return []

    rows = (
        db.session.query(GovernanceGroup.uuid)
        .join(GroupRelationship, GroupRelationship.source_group_id == GovernanceGroup.id)
        .join(RelationshipType, RelationshipType.id == GroupRelationship.relationship_type_id)
        .filter(GroupRelationship.target_group_id == group.id)
        .filter(RelationshipType.type_name == REPORT_TO_TYPE_NAME)
        .all()
    )
    return [uuid for (uuid,) in rows]


def _bfs_reporting_path(start_uuid: str, target_uuid: str) -> list[str] | None:
    """BFS downward from ``start_uuid`` following control edges.

    Returns the path ``[start_uuid, ..., target_uuid]`` (most powerful first) if
    ``target_uuid`` is reachable, otherwise None.
    """
    if start_uuid == target_uuid:
        return [start_uuid]

    visited = {start_uuid}
    parent: dict[str, str] = {}
    queue = deque([start_uuid])
    while queue:
        current = queue.popleft()
        for child in _get_list_of_groups_under_control(current):
            if child in visited:
                continue
            visited.add(child)
            parent[child] = current
            if child == target_uuid:
                path = [child]
                while path[-1] != start_uuid:
                    path.append(parent[path[-1]])
                path.reverse()
                return path
            queue.append(child)
    return None


def get_chain_of_command(from_group_uuid: str, to_group_uuid: str) -> list[str] | None:
    """
    Find the reporting line between two queried groups using breadth-first search.

    Returns the chain of group uuids ordered from most to least powerful, e.g.
    ``[powerful_group, ..., less_powerful_group]``. Returns None when neither group
    reports (directly or transitively) to the other, or when an uuid does not exist.
    """
    if _find_group_by_uuid(from_group_uuid) is None or _find_group_by_uuid(to_group_uuid) is None:
        return None

    # Case 1: from_group is the more powerful one and controls to_group.
    path = _bfs_reporting_path(from_group_uuid, to_group_uuid)
    if path is not None:
        return path

    # Case 2: to_group is the more powerful one and controls from_group.
    return _bfs_reporting_path(to_group_uuid, from_group_uuid)
