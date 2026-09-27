"""Seed-data integrity for the configurable type tables.

``seed_initial_types`` runs automatically inside ``create_app``; these tests
assert the defaults land and that re-seeding does not duplicate rows.
"""

from app.db_init_seed import (
    GROUP_TYPES,
    MEMBER_ROLE_TYPES,
    RELATIONSHIP_TYPES,
    seed_initial_types,
)
from app.db_schema import GroupType, MembershipRoleType, RelationshipType
from app.extensions import db
from app.services import type_service


def test_group_types_seeded(session):
    names = {group_type.type_name for group_type in GroupType.query.all()}
    assert set(GROUP_TYPES).issubset(names)


def test_member_role_types_seeded(session):
    names = {t.type_name for t in MembershipRoleType.query.all()}
    assert set(MEMBER_ROLE_TYPES).issubset(names)


def test_relationship_types_seeded(session):
    names = {t.type_name for t in RelationshipType.query.all()}
    expected = {r["type_name"] for r in RELATIONSHIP_TYPES}
    assert expected.issubset(names)


def test_reseeding_does_not_duplicate(session):
    before = GroupType.query.count()

    seed_initial_types()  # skips names that already exist

    assert GroupType.query.count() == before


def test_entity_types_prescribed_first_then_user_defined(session):
    """The ToR form needs prescribed types on top, user-added ones below."""
    # Add a user-defined type whose name sorts before some prescribed ones, so a
    # plain alphabetical sort would wrongly interleave it.
    db.session.add(GroupType(type_name="Aardvark Council"))
    db.session.commit()

    result = type_service.list_entity_types()

    # Prescribed types appear first, in their curated seed order.
    assert result["prescribed_entity_types"] == GROUP_TYPES
    assert result["entity_types"][: len(GROUP_TYPES)] == GROUP_TYPES
    # The user-defined type follows the prescribed block, never inside it.
    assert result["entity_types"][len(GROUP_TYPES) :] == ["Aardvark Council"]
