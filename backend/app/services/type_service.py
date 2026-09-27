"""Configurable type/role/relation lookups for the ToR form.

GET paths read the configurable lists straight from the type tables.
"""

from app.db_schema import GroupType, MembershipRoleType, RelationshipType
from app.extensions import db


def _normalise_type_name(type_name: str) -> str:
    """Trim a submitted type name and reject blank values."""
    cleaned = type_name.strip()
    if not cleaned:
        raise ValueError("type_name must not be blank")
    return cleaned


# Resolve or create a configurable governance group type.
def get_or_create_group_type(type_name: str, description: str | None = None) -> int:
    """Return a group type id, creating the type when it does not exist."""
    cleaned = _normalise_type_name(type_name)
    group_type = GroupType.query.filter_by(type_name=cleaned).first()
    if group_type is None:
        group_type = GroupType(type_name=cleaned, description=description)
        db.session.add(group_type)
        db.session.flush()
    return group_type.id


# Resolve or create a configurable relationship type.
def get_or_create_relation_type(
    type_name: str,
    description: str | None = None,
    is_directed: bool = True,
) -> int:
    """Return a relationship type id, creating the type when it does not exist."""
    cleaned = _normalise_type_name(type_name)
    relation_type = RelationshipType.query.filter_by(type_name=cleaned).first()
    if relation_type is None:
        relation_type = RelationshipType(
            type_name=cleaned,
            description=description,
            is_directed=is_directed,
        )
        db.session.add(relation_type)
        db.session.flush()
    return relation_type.id


# Resolve or create a configurable membership role type.
def get_or_create_member_role_type(
    type_name: str,
    description: str | None = None,
) -> int:
    """Return a member role type id, creating the type when it does not exist."""
    cleaned = _normalise_type_name(type_name)
    member_role_type = MembershipRoleType.query.filter_by(type_name=cleaned).first()
    if member_role_type is None:
        member_role_type = MembershipRoleType(
            type_name=cleaned,
            description=description,
        )
        db.session.add(member_role_type)
        db.session.flush()
    return member_role_type.id


def list_entity_types() -> dict:
    """Group entity types (``entity_types_tor.json``).

    The prescribed (seeded) types are returned first in their curated seed
    order, then any user-added types alphabetically. ``prescribed_entity_types``
    names the seeded set so the form can draw a divider between the two groups.
    """
    # Imported lazily to avoid a circular import at module load: db_init_seed
    # imports the type helpers defined in this module.
    from app.db_init_seed import GROUP_TYPES

    existing = {t.type_name for t in GroupType.query.all()}
    prescribed = [name for name in GROUP_TYPES if name in existing]
    user_defined = sorted(existing - set(prescribed))
    return {
        "entity_types": prescribed + user_defined,
        "prescribed_entity_types": prescribed,
    }


def list_member_roles() -> dict:
    """Member role types (``member_roles.json``).

    Returns the full configurable list under ``member_types``. NOTE: the curated
    ``member_types_tor`` DTO deliberately excludes ``Chair``/``Secretariat`` (the
    form adds those itself) and external roles, but the ``membership_role_types``
    table has no category column to filter on, so that curation is currently a
    frontend concern. Flagged as a known gap.
    """
    names = [
        t.type_name for t in MembershipRoleType.query.order_by(MembershipRoleType.type_name).all()
    ]
    return {"member_types": names}


def list_relation_types() -> dict:
    """Group-to-group relation types (``group_relation_types.json``)."""
    names = [t.type_name for t in RelationshipType.query.order_by(RelationshipType.type_name).all()]
    return {"relation_types": names}
