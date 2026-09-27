"""Service functions for person-related operations.

Implements the authority-branched person read used by ``GET /api/person/<uuid>``.
"""

from app.db_schema import (
    GovernanceGroup,
    Membership,
    MembershipRole,
    MembershipRoleType,
    Person,
)
from app.extensions import db


def _affiliated_groups(person_id: int) -> list[dict]:
    """All groups this person sits on, each with their role list in that group."""
    groups = []
    for m in Membership.query.filter_by(person_id=person_id).all():
        group = db.session.get(GovernanceGroup, m.group_id)
        if group is None:
            continue
        rows = (
            db.session.query(MembershipRoleType.type_name)
            .join(MembershipRole, MembershipRole.role_type_id == MembershipRoleType.id)
            .filter(MembershipRole.membership_id == m.id)
            .order_by(MembershipRoleType.type_name)
            .all()
        )
        groups.append(
            {
                "group_uuid": group.uuid,
                "group_name": group.group_name,
                "roles": [name for (name,) in rows],
            }
        )
    return groups


def list_people() -> list[dict]:
    """Return every person as a ``person_list`` item ``{uuid, first_name, last_name, email}``.

    Ordered by last name then first name. Includes people with **zero**
    memberships (their governance burden legitimately reads 0). Email is
    included so same-name people can be told apart in search dropdowns;
    phone, zID and gender stay off this list.
    """
    people = Person.query.order_by(Person.last_name, Person.first_name).all()
    return [
        {
            "uuid": person.uuid,
            "first_name": person.first_name,
            "last_name": person.last_name,
            "email": person.email,
        }
        for person in people
    ]


def member_representation(person: Person) -> str:
    """Which of the three sources this person is drawn from.

    Mirrors the precedence in ``analytics.get_member_representation_of_a_group``
    so the profile and the diversity chart never disagree: external wins, then
    student, and anyone else counts as faculty.
    """
    if person.is_external:
        return "external"
    if person.is_student:
        return "student"
    return "faculty"


def get_person_info(person_uuid: str, privileged: bool) -> dict | None:
    """Return a person profile, shaped by the caller's authority.

    ``privileged`` (SUPER_USER / ADMIN) yields ``person_details_superuser``;
    otherwise the minimal ``person_public_reference``. Returns ``None`` when no
    person matches (caller maps that to 404).
    """
    person = Person.query.filter_by(uuid=person_uuid).first()
    if person is None:
        return None

    profile = {
        "uuid": person.uuid,
        "first_name": person.first_name,
        "last_name": person.last_name,
        "affiliated_groups": _affiliated_groups(person.id),
    }

    if privileged:
        profile.update(
            {
                "gender": person.gender,
                "is_student": person.is_student,
                "is_external": person.is_external,
                "is_faculty": person.is_faculty,
                "member_representation": member_representation(person),
                "email": person.email,
                "phone": person.phone,
                "zID": person.z_id,
            }
        )

    return profile
