"""Service functions for governance group operations.

This module contains business logic for creating groups, retrieving group
details, and generating graph data for frontend visualisation.
"""

from app.db_schema import (
    REPORT_TO_TYPE_NAME,
    GovernanceGroup,
    GroupReferenceLink,
    GroupRelationship,
    GroupType,
    Membership,
    MembershipRole,
    MembershipRoleType,
    Person,
    RelationshipType,
)
from app.extensions import db


def create_group(payload: dict) -> dict:
    """Create a governance group from submitted ToR form data.

    This function will later:
    - validate required group fields
    - create a GovernanceGroup record
    - create or reuse Person records
    - create Membership records
    - create GroupRelationship records
    - store external record references
    - use a database transaction

    Args:
        payload: JSON payload submitted from the frontend ToR form.

    Returns:
        A dictionary containing the created group result.
    """
    return {
        "message": "not implemented",
        "received": payload,
    }


def _membership(group_id: int) -> list[dict]:
    """Each person on the group, with their role names in this group."""
    members = []
    for m in Membership.query.filter_by(group_id=group_id).all():
        person = db.session.get(Person, m.person_id)
        if person is None:
            continue
        roles = (
            db.session.query(MembershipRoleType.type_name)
            .join(MembershipRole, MembershipRole.role_type_id == MembershipRoleType.id)
            .filter(MembershipRole.membership_id == m.id)
            .order_by(MembershipRoleType.type_name)
            .all()
        )
        members.append(
            {
                "uuid": person.uuid,
                "first_name": person.first_name,
                "last_name": person.last_name,
                "roles": [name for (name,) in roles],
            }
        )
    return members


def _relations(group_id: int) -> list[dict]:
    """Every reporting line touching this group, in both directions.

    An edge reads ``source reports to target``. Outgoing edges are the groups
    this one answers to (``direction: "reports_to"``); incoming edges are the
    groups that answer to it (``direction: "reported_to_by"``). Returning only
    outgoing edges — as this used to — left a parent committee unable to see
    anything reporting to it.
    """
    relations = []

    outgoing = (
        db.session.query(GovernanceGroup)
        .join(GroupRelationship, GroupRelationship.target_group_id == GovernanceGroup.id)
        .join(
            RelationshipType,
            RelationshipType.id == GroupRelationship.relationship_type_id,
        )
        .filter(GroupRelationship.source_group_id == group_id)
        .filter(RelationshipType.type_name == REPORT_TO_TYPE_NAME)
        .all()
    )
    for target in outgoing:
        relations.append(
            {
                "uuid": target.uuid,
                "group_name": target.group_name,
                "relation_type": REPORT_TO_TYPE_NAME,
                "direction": "reports_to",
            }
        )

    incoming = (
        db.session.query(GovernanceGroup)
        .join(GroupRelationship, GroupRelationship.source_group_id == GovernanceGroup.id)
        .join(
            RelationshipType,
            RelationshipType.id == GroupRelationship.relationship_type_id,
        )
        .filter(GroupRelationship.target_group_id == group_id)
        .filter(RelationshipType.type_name == REPORT_TO_TYPE_NAME)
        .all()
    )
    for source in incoming:
        relations.append(
            {
                "uuid": source.uuid,
                "group_name": source.group_name,
                "relation_type": REPORT_TO_TYPE_NAME,
                "direction": "reported_to_by",
            }
        )

    return relations


def _reference_links(group_id: int) -> list[dict]:
    """External / RAMS / SharePoint links attached to the group."""
    return [
        {"title": link.title, "url": link.url}
        for link in GroupReferenceLink.query.filter_by(group_id=group_id).all()
    ]


def _role_holder_name(group_id: int, role_name: str) -> str | None:
    """Full name of the person holding ``role_name`` in this group, or None.

    Joins the same ``Membership -> MembershipRole -> MembershipRoleType`` chain as
    ``_membership()``. When several people hold the role, the one with the
    lowest ``Person.uuid`` is chosen so the result is deterministic.
    """
    person = (
        db.session.query(Person)
        .join(Membership, Membership.person_id == Person.id)
        .join(MembershipRole, MembershipRole.membership_id == Membership.id)
        .join(MembershipRoleType, MembershipRoleType.id == MembershipRole.role_type_id)
        .filter(Membership.group_id == group_id)
        .filter(MembershipRoleType.type_name == role_name)
        .order_by(Person.uuid)
        .first()
    )
    if person is None:
        return None
    return f"{person.first_name} {person.last_name}"


def list_organisations(name_query: str | None = None) -> list[dict]:
    """Return governance groups as ``organisation_list`` items.

    Each item is ``{uuid, group_name, status, chair, secretariat}`` where
    ``chair`` and ``secretariat`` are the role holders' display names, or
    ``None`` when the group has no such role holder. ``status`` lets the ToR
    form tell a formally registered group (which blocks re-registration) from a
    ``proposed`` one (which the submitter is allowed to adopt).

    ``name_query`` filters by case-insensitive substring, backing the group
    search box. Ordered by group name so results read predictably.
    """
    query = GovernanceGroup.query
    if name_query and name_query.strip():
        query = query.filter(GovernanceGroup.group_name.ilike(f"%{name_query.strip()}%"))

    groups = query.order_by(GovernanceGroup.group_name).all()
    return [
        {
            "uuid": group.uuid,
            "group_name": group.group_name,
            "status": group.status.value.lower(),
            "chair": _role_holder_name(group.id, "Chair"),
            "secretariat": _role_holder_name(group.id, "Secretariat"),
        }
        for group in groups
    ]


def _viewer_is_member(group_id: int, viewer_email: str | None) -> bool:
    """True when the logged-in account corresponds to someone on this group.

    Login accounts (``users``) and people (``persons``) are separate tables with
    no foreign key between them, so email is the only available join.
    """
    if not viewer_email:
        return False

    return (
        db.session.query(Membership.id)
        .join(Person, Person.id == Membership.person_id)
        .filter(Membership.group_id == group_id)
        .filter(db.func.lower(Person.email) == viewer_email.strip().lower())
        .first()
        is not None
    )


def get_group_detail(
    group_uuid: str,
    viewer_email: str | None = None,
    privileged: bool = False,
) -> dict | None:
    """Return one governance group's ``organisation`` DTO, shaped by the viewer.

    Resolves the group by its public UUID and assembles metadata, membership,
    reporting lines, and external reference links. ``status`` is the lower-cased
    server enum and ``entity_type`` is the group's type name.

    Meeting details (cadence, duration and the reference links that point at
    minutes) are **only** included for a superuser or for someone who sits on
    the group. ``can_view_meetings`` tells the frontend which case it is, so it
    can hide the section rather than render an empty one.

    Args:
        group_uuid: The public UUID of the governance group.
        viewer_email: Email of the logged-in account, or None when anonymous.
        privileged: True when the caller is a SUPER_USER.

    Returns:
        The ``organisation`` DTO dict, or ``None`` if no group matches.
    """
    group = GovernanceGroup.query.filter_by(uuid=group_uuid).first()
    if group is None:
        return None

    group_type = db.session.get(GroupType, group.group_type_id)
    can_view_meetings = privileged or _viewer_is_member(group.id, viewer_email)

    detail = {
        "uuid": group.uuid,
        "group_name": group.group_name,
        "entity_type": group_type.type_name if group_type else None,
        "status": group.status.value.lower(),
        "purpose": group.purpose,
        "responsibilities": group.responsibilities,
        "membership": _membership(group.id),
        "relations": _relations(group.id),
        "start_date": group.start_date.isoformat() if group.start_date else None,
        "review_date": group.review_date.isoformat() if group.review_date else None,
        "created_timestamp": (group.created_at.isoformat() if group.created_at else None),
        "can_view_meetings": can_view_meetings,
    }

    if can_view_meetings:
        detail.update(
            {
                "meeting_frequency_per_year": group.meeting_frequency_per_year,
                "meeting_duration_hour": (
                    float(group.meeting_duration_hour)
                    if group.meeting_duration_hour is not None
                    else None
                ),
                "reference_links": _reference_links(group.id),
            }
        )

    return detail
