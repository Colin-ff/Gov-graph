"""Behavioural tests for the group- and person-list endpoints.

``GET /api/groups``  -> the ``organisation_list`` DTO (any authenticated
                        caller; feeds the frontend group search bar).
``GET /api/person``  -> the ``person_list`` DTO (any authenticated caller;
                        feeds the person search bar).

Both back the analytics dashboard's typeahead pickers, which is why they live
outside the SUPER_USER-only ``/api/analytics`` namespace.
"""

import pytest

from app.db_schema import (
    GovernanceGroup,
    GroupType,
    Membership,
    MembershipRole,
    MembershipRoleType,
    Person,
)
from app.extensions import db


@pytest.fixture
def people_and_groups(app):
    """Seed two groups (one with Chair+Secretariat, one with neither), a
    zero-membership person, and return the public uuids keyed by label.
    """
    with app.app_context():
        group_type = GroupType.query.first()
        chair_type = MembershipRoleType.query.filter_by(type_name="Chair").first()
        sec_type = MembershipRoleType.query.filter_by(type_name="Secretariat").first()

        audit = GovernanceGroup(group_name="Audit Committee", group_type_id=group_type.id)
        bare = GovernanceGroup(group_name="Bare Working Group", group_type_id=group_type.id)
        db.session.add_all([audit, bare])
        db.session.flush()

        def make_person(first, last) -> Person:
            person = Person(
                first_name=first,
                last_name=last,
                email=f"{first.lower()}.{last.lower()}@example.com",
            )
            db.session.add(person)
            db.session.flush()
            return person

        chair = make_person("Abrik", "Bay")
        secretariat = make_person("Sharica", "Blue")
        # A person with no memberships at all — must still appear in the list.
        loner = make_person("Zoe", "Zephyr")

        def add_member(group, person, role_type=None) -> None:
            membership = Membership(group_id=group.id, person_id=person.id)
            db.session.add(membership)
            db.session.flush()
            if role_type is not None:
                db.session.add(
                    MembershipRole(membership_id=membership.id, role_type_id=role_type.id)
                )

        add_member(audit, chair, chair_type)
        add_member(audit, secretariat, sec_type)
        # bare group gets no members at all.

        db.session.commit()

        return {
            "audit": audit.uuid,
            "bare": bare.uuid,
            "chair": chair.uuid,
            "secretariat": secretariat.uuid,
            "loner": loner.uuid,
        }


# ----- GET /api/groups ---------------------------------------------------


def test_group_list_requires_auth(client, people_and_groups):
    resp = client.get("/api/groups")
    assert resp.status_code == 401


def test_group_list_shape_and_role_resolution(client, staff_headers, people_and_groups):
    resp = client.get("/api/groups", headers=staff_headers)
    assert resp.status_code == 200
    body = resp.get_json()
    assert "organisations" in body
    by_uuid = {org["uuid"]: org for org in body["organisations"]}

    audit = by_uuid[people_and_groups["audit"]]
    assert audit["group_name"] == "Audit Committee"
    assert audit["chair"] == "Abrik Bay"
    assert audit["secretariat"] == "Sharica Blue"
    # status lets the ToR form tell registered groups from proposed ones.
    assert audit["status"] == "active"


def test_group_list_null_chair_when_unassigned(client, staff_headers, people_and_groups):
    body = client.get("/api/groups", headers=staff_headers).get_json()
    by_uuid = {org["uuid"]: org for org in body["organisations"]}
    bare = by_uuid[people_and_groups["bare"]]
    assert bare["chair"] is None
    assert bare["secretariat"] is None


def test_group_list_empty_db(client, staff_headers):
    resp = client.get("/api/groups", headers=staff_headers)
    assert resp.status_code == 200
    assert resp.get_json() == {"organisations": []}


def test_group_list_filters_by_name(client, staff_headers, people_and_groups):
    """``?name=`` is a case-insensitive substring match, backing the search box."""
    body = client.get("/api/groups?name=audit", headers=staff_headers).get_json()
    names = [org["group_name"] for org in body["organisations"]]
    assert names == ["Audit Committee"]


# ----- GET /api/person ---------------------------------------------------


def test_person_list_requires_auth(client, people_and_groups):
    resp = client.get("/api/person")
    assert resp.status_code == 401


def test_person_list_with_staff(client, staff_headers, people_and_groups):
    resp = client.get("/api/person", headers=staff_headers)
    assert resp.status_code == 200
    body = resp.get_json()
    assert "people" in body
    by_uuid = {p["uuid"]: p for p in body["people"]}
    # The zero-membership person is present.
    assert people_and_groups["loner"] in by_uuid
    # Identity + name + email are exposed, so same-name people can be told
    # apart in search dropdowns.
    sample = body["people"][0]
    assert set(sample.keys()) == {"uuid", "first_name", "last_name", "email"}
    assert by_uuid[people_and_groups["chair"]]["email"] == "abrik.bay@example.com"


def test_person_list_ordered_by_last_name(client, staff_headers, people_and_groups):
    body = client.get("/api/person", headers=staff_headers).get_json()
    last_names = [p["last_name"] for p in body["people"]]
    assert last_names == sorted(last_names)
