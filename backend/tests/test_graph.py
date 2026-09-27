"""Behavioural tests for ``GET /api/graph`` and the viewer-shaped group detail.

The graph is the registry's headline view, so its contract matters: it must show
exactly the reporting lines, mark which groups are only proposed, and never leak
meeting details to someone outside the group.
"""

import pytest

from app.db_schema import (
    REPORT_TO_TYPE_NAME,
    GovernanceGroup,
    GroupRelationship,
    GroupStatus,
    GroupType,
    Membership,
    Person,
    RelationshipType,
)
from app.extensions import db


@pytest.fixture
def reporting_graph(app):
    """Board <- Committee, plus a proposed group and an unconnected one."""
    with app.app_context():
        group_type = GroupType.query.first()
        report_to = RelationshipType.query.filter_by(type_name=REPORT_TO_TYPE_NAME).first()

        board = GovernanceGroup(group_name="Academic Board", group_type_id=group_type.id)
        committee = GovernanceGroup(group_name="Audit Committee", group_type_id=group_type.id)
        # Named by someone else's ToR but never formally registered.
        proposed = GovernanceGroup(
            group_name="Data Steering Group",
            group_type_id=group_type.id,
            status=GroupStatus.PROPOSED,
        )
        loner = GovernanceGroup(group_name="Lone Panel", group_type_id=group_type.id)
        db.session.add_all([board, committee, proposed, loner])
        db.session.flush()

        db.session.add(
            GroupRelationship(
                source_group_id=committee.id,
                target_group_id=board.id,
                relationship_type_id=report_to.id,
            )
        )

        member = Person(
            first_name="Ashley",
            last_name="Clay",
            email="staff@unsw.edu.au",  # matches the staff_headers login account
        )
        outsider = Person(first_name="Zoe", last_name="Zephyr", email="zoe.zephyr@unsw.edu.au")
        db.session.add_all([member, outsider])
        db.session.flush()
        db.session.add(Membership(group_id=committee.id, person_id=member.id))

        committee.meeting_frequency_per_year = 6
        committee.meeting_duration_hour = 2

        db.session.commit()
        return {
            "board": board.uuid,
            "committee": committee.uuid,
            "proposed": proposed.uuid,
            "loner": loner.uuid,
        }


def test_graph_requires_authentication(client, reporting_graph):
    assert client.get("/api/graph").status_code == 401


def test_graph_empty_db(client, staff_headers):
    resp = client.get("/api/graph", headers=staff_headers)
    assert resp.status_code == 200
    assert resp.get_json() == {"nodes": [], "relations": []}


def test_graph_nodes_expose_status_and_type(client, staff_headers, reporting_graph):
    """Without status the frontend cannot tell a real group from a proposed one."""
    body = client.get("/api/graph", headers=staff_headers).get_json()
    by_uuid = {n["uuid"]: n for n in body["nodes"]}

    assert len(body["nodes"]) == 4
    assert by_uuid[reporting_graph["board"]]["status"] == "active"
    assert by_uuid[reporting_graph["proposed"]]["status"] == "proposed"
    assert by_uuid[reporting_graph["board"]]["entity_type"] is not None


def test_graph_relations_are_directed_report_to(client, staff_headers, reporting_graph):
    """An edge reads source-reports-to-target: the target is the governing body."""
    body = client.get("/api/graph", headers=staff_headers).get_json()

    assert len(body["relations"]) == 1
    edge = body["relations"][0]
    assert edge["source_uuid"] == reporting_graph["committee"]
    assert edge["target_uuid"] == reporting_graph["board"]
    assert edge["relation_type"] == REPORT_TO_TYPE_NAME
    assert edge["directed"] is True


def test_graph_excludes_other_relation_types(app, client, staff_headers, reporting_graph):
    """Only reporting lines are drawn, whatever else exists in the table."""
    with app.app_context():
        other = RelationshipType(type_name="Work with", is_directed=False)
        db.session.add(other)
        db.session.flush()
        board = GovernanceGroup.query.filter_by(uuid=reporting_graph["board"]).first()
        loner = GovernanceGroup.query.filter_by(uuid=reporting_graph["loner"]).first()
        db.session.add(
            GroupRelationship(
                source_group_id=loner.id,
                target_group_id=board.id,
                relationship_type_id=other.id,
            )
        )
        db.session.commit()

    body = client.get("/api/graph", headers=staff_headers).get_json()
    assert len(body["relations"]) == 1


# ----- group detail: reporting lines and meeting gating -------------------


def test_group_detail_shows_both_relation_directions(client, staff_headers, reporting_graph):
    """A parent must be able to see what reports to it, not just what it reports to."""
    board = client.get(f"/api/groups/{reporting_graph['board']}", headers=staff_headers).get_json()
    committee = client.get(
        f"/api/groups/{reporting_graph['committee']}", headers=staff_headers
    ).get_json()

    assert [r["direction"] for r in board["relations"]] == ["reported_to_by"]
    assert board["relations"][0]["uuid"] == reporting_graph["committee"]
    assert [r["direction"] for r in committee["relations"]] == ["reports_to"]
    assert committee["relations"][0]["uuid"] == reporting_graph["board"]


def test_superuser_sees_meeting_details(client, admin_headers, reporting_graph):
    body = client.get(
        f"/api/groups/{reporting_graph['committee']}", headers=admin_headers
    ).get_json()

    assert body["can_view_meetings"] is True
    assert body["meeting_frequency_per_year"] == 6


def test_member_sees_meeting_details_of_own_group(client, staff_headers, reporting_graph):
    """staff@unsw.edu.au is a member of the committee, matched by email."""
    body = client.get(
        f"/api/groups/{reporting_graph['committee']}", headers=staff_headers
    ).get_json()

    assert body["can_view_meetings"] is True
    assert body["meeting_frequency_per_year"] == 6


def test_non_member_cannot_see_meeting_details(client, staff_headers, reporting_graph):
    """The staff account sits on the committee but not the board."""
    body = client.get(f"/api/groups/{reporting_graph['board']}", headers=staff_headers).get_json()

    assert body["can_view_meetings"] is False
    assert "meeting_frequency_per_year" not in body
    assert "meeting_duration_hour" not in body
    # Reference links can point at minutes, so they are gated with the rest.
    assert "reference_links" not in body
