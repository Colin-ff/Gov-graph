"""Behavioural tests for the /api/analytics endpoints.

Each test seeds a small governance graph (groups linked with "Report to"
relationships plus people/memberships), then queries an analytics endpoint and
asserts the key output. The seeded numbers are chosen so every expected value is
easy to derive by hand:

Groups (meeting frequency x duration = yearly hours):
    Board          4 x 3   = 12h
    Committee A    10 x 2  = 20h
    Committee B    5 x 1   = 5h
    Working Group  6 x 0.5 = 3h
    Orphan Group   2 x 1   = 2h   (reports to nobody)
    Joint Cmte     1 x 1   = 1h   (reports to TWO groups)

Reporting lines (source -> target):
    Committee A  -> Board
    Committee B  -> Board
    Working Grp  -> Committee A
    Joint Cmte   -> Board
    Joint Cmte   -> Committee A     (two lines => multiple-reporting group)

Memberships:
    Committee A: Stu(student,f), Ext(external,m), Fac(faculty,m), Shared(f), Busy(?)
    Committee B: Shared, Busy
    Board:       Busy
"""

import pytest

from app.db_schema import (
    GovernanceGroup,
    GroupRelationship,
    GroupType,
    Membership,
    Person,
    RelationshipType,
)
from app.extensions import db


@pytest.fixture
def graph(app):
    """Seed the governance graph and return the public uuids keyed by label."""
    with app.app_context():
        group_type = GroupType.query.first()
        report_to = RelationshipType.query.filter_by(type_name="Report to").first()

        def make_group(name: str, freq: int, dur: float) -> GovernanceGroup:
            group = GovernanceGroup(
                group_name=name,
                group_type_id=group_type.id,
                meeting_frequency_per_year=freq,
                meeting_duration_hour=dur,
            )
            db.session.add(group)
            db.session.flush()
            return group

        board = make_group("Board", 4, 3)  # 12h
        comm_a = make_group("Committee A", 10, 2)  # 20h
        comm_b = make_group("Committee B", 5, 1)  # 5h
        wg = make_group("Working Group", 6, 0.5)  # 3h
        orphan = make_group("Orphan Group", 2, 1)  # 2h
        joint = make_group("Joint Committee", 1, 1)  # 1h

        def reports_to(source: GovernanceGroup, target: GovernanceGroup) -> None:
            db.session.add(
                GroupRelationship(
                    source_group_id=source.id,
                    target_group_id=target.id,
                    relationship_type_id=report_to.id,
                )
            )

        reports_to(comm_a, board)
        reports_to(comm_b, board)
        reports_to(wg, comm_a)
        reports_to(joint, board)
        reports_to(joint, comm_a)

        def make_person(first, gender=None, student=False, external=False) -> Person:
            person = Person(
                first_name=first,
                last_name="X",
                email=f"{first.lower()}@example.com",
                gender=gender,
                is_student=student,
                is_external=external,
            )
            db.session.add(person)
            db.session.flush()
            return person

        stu = make_person("Stu", gender="female", student=True)
        ext = make_person("Ext", gender="male", external=True)
        fac = make_person("Fac", gender="male")
        shared = make_person("Shared", gender="female")
        busy = make_person("Busy", gender=None)

        def add_member(group: GovernanceGroup, person: Person) -> None:
            db.session.add(Membership(group_id=group.id, person_id=person.id))

        for person in (stu, ext, fac, shared, busy):
            add_member(comm_a, person)
        add_member(comm_b, shared)
        add_member(comm_b, busy)
        add_member(board, busy)

        db.session.commit()

        return {
            "board": board.uuid,
            "comm_a": comm_a.uuid,
            "comm_b": comm_b.uuid,
            "wg": wg.uuid,
            "orphan": orphan.uuid,
            "joint": joint.uuid,
            "stu": stu.uuid,
            "ext": ext.uuid,
            "fac": fac.uuid,
            "shared": shared.uuid,
            "busy": busy.uuid,
        }


def _get(client, url, headers):
    resp = client.get(url, headers=headers)
    return resp.status_code, resp.get_json()


# ----- Governance burden -------------------------------------------------


def test_person_governance_load(client, admin_headers, graph):
    # Busy sits on Board(12) + Committee A(20) + Committee B(5) = 37h.
    status, body = _get(
        client, f"/api/analytics/people/{graph['busy']}/governance-load", admin_headers
    )
    assert status == 200
    assert body["uuid"] == graph["busy"]
    assert body["meeting_hours"] == pytest.approx(37.0)


def test_person_governance_load_unknown_person_404(client, admin_headers, graph):
    status, _ = _get(client, "/api/analytics/people/does-not-exist/governance-load", admin_headers)
    assert status == 404


def test_top_people_by_governance_load_ranks_by_hours(client, admin_headers, graph):
    status, body = _get(client, "/api/analytics/people/top-governance-load?n=3", admin_headers)
    assert status == 200
    people = body["people"]
    assert len(people) == 3
    # Busy(37) then Shared(20+5=25); the remaining three are Committee-A-only (20).
    assert people[0]["uuid"] == graph["busy"]
    assert people[0]["count"] == pytest.approx(37.0)
    assert people[1]["uuid"] == graph["shared"]
    assert people[1]["count"] == pytest.approx(25.0)


def test_top_people_invalid_n_is_400(client, admin_headers, graph):
    for bad in ("0", "-2", "abc"):
        status, _ = _get(
            client, f"/api/analytics/people/top-governance-load?n={bad}", admin_headers
        )
        assert status == 400, bad


def test_person_group_count(client, admin_headers, graph):
    status, body = _get(client, f"/api/analytics/people/{graph['busy']}/group-count", admin_headers)
    assert status == 200
    assert body["group_count"] == 3

    _, shared_body = _get(
        client, f"/api/analytics/people/{graph['shared']}/group-count", admin_headers
    )
    assert shared_body["group_count"] == 2


def test_top_people_by_group_count_ranks_by_group_membership(client, admin_headers, graph):
    status, body = _get(client, "/api/analytics/people/top-group-count?n=5", admin_headers)
    assert status == 200
    people = body["people"]
    # Busy sits on 3 groups, Shared on 2, the other three on Committee A only (1).
    assert people[0]["uuid"] == graph["busy"]
    assert people[0]["count"] == 3
    assert people[1]["uuid"] == graph["shared"]
    assert people[1]["count"] == 2
    assert [p["count"] for p in people] == [3, 2, 1, 1, 1]


def test_top_people_by_group_count_invalid_n_is_400(client, admin_headers, graph):
    status, _ = _get(client, "/api/analytics/people/top-group-count?n=0", admin_headers)
    assert status == 400


# ----- Governance effort concentration -----------------------------------


def test_group_governed_count(client, admin_headers, graph):
    # Committee A, Committee B and Joint report to Board -> 3.
    status, body = _get(
        client, f"/api/analytics/groups/{graph['board']}/governed-group-count", admin_headers
    )
    assert status == 200
    assert body["governed_group_count"] == 3

    # Working Group and Joint report to Committee A -> 2.
    _, comm_a_body = _get(
        client, f"/api/analytics/groups/{graph['comm_a']}/governed-group-count", admin_headers
    )
    assert comm_a_body["governed_group_count"] == 2

    # Nobody reports to Committee B -> 0.
    _, comm_b_body = _get(
        client, f"/api/analytics/groups/{graph['comm_b']}/governed-group-count", admin_headers
    )
    assert comm_b_body["governed_group_count"] == 0


def test_group_governance_hours(client, admin_headers, graph):
    status, body = _get(
        client, f"/api/analytics/groups/{graph['comm_a']}/governance-hours", admin_headers
    )
    assert status == 200
    assert body["governance_hours"] == pytest.approx(20.0)

    _, board_body = _get(
        client, f"/api/analytics/groups/{graph['board']}/governance-hours", admin_headers
    )
    assert board_body["governance_hours"] == pytest.approx(12.0)


def test_group_governance_hours_unknown_group_404(client, admin_headers, graph):
    status, _ = _get(client, "/api/analytics/groups/nope/governance-hours", admin_headers)
    assert status == 404


def test_top_groups_by_governed_count_ranks_by_subordinates(client, admin_headers, graph):
    status, body = _get(client, "/api/analytics/groups/top-governed-group-count?n=2", admin_headers)
    assert status == 200
    groups = body["groups"]
    assert len(groups) == 2
    # Board governs 3 (A, B, Joint); Committee A governs 2 (Working Group, Joint).
    assert groups[0]["name"] == "Board"
    assert groups[0]["count"] == 3
    assert groups[1]["name"] == "Committee A"
    assert groups[1]["count"] == 2


def test_top_groups_by_governance_hours_ranks_by_hours(client, admin_headers, graph):
    status, body = _get(client, "/api/analytics/groups/top-governance-hours?n=3", admin_headers)
    assert status == 200
    groups = body["groups"]
    # Committee A(20) > Board(12) > Committee B(5).
    assert [(g["name"], g["count"]) for g in groups] == [
        ("Committee A", pytest.approx(20.0)),
        ("Board", pytest.approx(12.0)),
        ("Committee B", pytest.approx(5.0)),
    ]


def test_top_groups_invalid_n_is_400(client, admin_headers, graph):
    for url in (
        "/api/analytics/groups/top-governed-group-count?n=-1",
        "/api/analytics/groups/top-governance-hours?n=abc",
    ):
        status, _ = _get(client, url, admin_headers)
        assert status == 400, url


# ----- Unusual governance relations --------------------------------------


def test_orphan_groups(client, admin_headers, graph):
    # Only Board and Orphan Group have no outgoing "Report to" relationship.
    status, body = _get(client, "/api/analytics/orphan-groups", admin_headers)
    assert status == 200
    names = {g["name"] for g in body["groups"]}
    assert names == {"Board", "Orphan Group"}


def test_multiple_reporting_line_groups(client, admin_headers, graph):
    status, body = _get(client, "/api/analytics/multiple-reporting-line-groups", admin_headers)
    assert status == 200
    groups = body["groups"]
    assert len(groups) == 1
    assert groups[0]["name"] == "Joint Committee"
    assert groups[0]["count"] == 2


# ----- Inefficient overlapping members -----------------------------------


def test_shared_members(client, admin_headers, graph):
    # Committee A and Committee B share Shared + Busy = 2.
    status, body = _get(
        client,
        f"/api/analytics/overlap/shared-members?group_a={graph['comm_a']}&group_b={graph['comm_b']}",
        admin_headers,
    )
    assert status == 200
    assert body["shared_member_count"] == 2


def test_shared_member_list_names_the_shared_people(client, admin_headers, graph):
    status, body = _get(
        client,
        f"/api/analytics/overlap/shared-member-list?group_a={graph['comm_a']}&group_b={graph['comm_b']}",
        admin_headers,
    )
    assert status == 200
    assert body["shared_member_count"] == 2
    shared_uuids = {m["uuid"] for m in body["shared_members"]}
    assert shared_uuids == {graph["shared"], graph["busy"]}


def test_shared_member_list_missing_argument_is_400(client, admin_headers, graph):
    status, _ = _get(
        client,
        f"/api/analytics/overlap/shared-member-list?group_a={graph['comm_a']}",
        admin_headers,
    )
    assert status == 400


def test_shared_member_list_unknown_group_is_404(client, admin_headers, graph):
    status, _ = _get(
        client,
        f"/api/analytics/overlap/shared-member-list?group_a={graph['comm_a']}&group_b=nope",
        admin_headers,
    )
    assert status == 404


def test_overlap_percentage_is_relative_to_latter_group(client, admin_headers, graph):
    # Denominator is group_b. B has 2 members, both shared -> 100%.
    status, body = _get(
        client,
        f"/api/analytics/overlap/percentage?group_a={graph['comm_a']}&group_b={graph['comm_b']}",
        admin_headers,
    )
    assert status == 200
    assert body["relative_to"] == "group_b"
    assert body["shared_member_count"] == 2
    assert body["overlap_percentage"] == pytest.approx(100.0)

    # Swap the order: A has 5 members, 2 shared -> 40%.
    _, swapped = _get(
        client,
        f"/api/analytics/overlap/percentage?group_a={graph['comm_b']}&group_b={graph['comm_a']}",
        admin_headers,
    )
    assert swapped["overlap_percentage"] == pytest.approx(40.0)


def test_overlap_missing_argument_is_400(client, admin_headers, graph):
    status, _ = _get(
        client, f"/api/analytics/overlap/shared-members?group_a={graph['comm_a']}", admin_headers
    )
    assert status == 400


def test_overlap_unknown_group_is_404(client, admin_headers, graph):
    status, _ = _get(
        client,
        f"/api/analytics/overlap/shared-members?group_a={graph['comm_a']}&group_b=nope",
        admin_headers,
    )
    assert status == 404


# ----- Diversity ---------------------------------------------------------


def test_gender_distribution(client, admin_headers, graph):
    # Committee A: female {Stu, Shared}=40%, male {Ext, Fac}=40%, unknown {Busy}=20%.
    status, body = _get(
        client, f"/api/analytics/groups/{graph['comm_a']}/gender-distribution", admin_headers
    )
    assert status == 200
    dist = body["distribution"]
    assert dist["female"] == pytest.approx(40.0)
    assert dist["male"] == pytest.approx(40.0)
    assert dist["unknown"] == pytest.approx(20.0)


def test_member_representation(client, admin_headers, graph):
    # Committee A: student {Stu}=20%, external {Ext}=20%, faculty {Fac,Shared,Busy}=60%.
    status, body = _get(
        client, f"/api/analytics/groups/{graph['comm_a']}/member-representation", admin_headers
    )
    assert status == 200
    rep = body["representation"]
    assert rep["student"] == pytest.approx(20.0)
    assert rep["external"] == pytest.approx(20.0)
    assert rep["faculty"] == pytest.approx(60.0)


# ----- Chain-of-command intelligence -------------------------------------


def test_chain_of_command_connected(client, admin_headers, graph):
    # Board governs Committee A governs Working Group.
    status, body = _get(
        client,
        f"/api/analytics/chain-of-command?from={graph['board']}&to={graph['wg']}",
        admin_headers,
    )
    assert status == 200
    assert body["connected"] is True
    # Ordered most-powerful first.
    assert body["chain"] == [graph["board"], graph["comm_a"], graph["wg"]]


def test_chain_of_command_reports_regardless_of_argument_order(client, admin_headers, graph):
    # Asking from the weaker end still returns the chain most-powerful first.
    status, body = _get(
        client,
        f"/api/analytics/chain-of-command?from={graph['wg']}&to={graph['board']}",
        admin_headers,
    )
    assert status == 200
    assert body["chain"][0] == graph["board"]
    assert body["chain"][-1] == graph["wg"]


def test_chain_of_command_no_reporting_line(client, admin_headers, graph):
    # Orphan Group has no reporting line to Board (or vice versa).
    status, body = _get(
        client,
        f"/api/analytics/chain-of-command?from={graph['orphan']}&to={graph['board']}",
        admin_headers,
    )
    assert status == 200
    assert body["connected"] is False
    assert body["chain"] is None


def test_chain_of_command_missing_argument_is_400(client, admin_headers, graph):
    status, _ = _get(
        client, f"/api/analytics/chain-of-command?from={graph['board']}", admin_headers
    )
    assert status == 400


# ----- Authorisation -----------------------------------------------------


def test_analytics_requires_authentication(client, graph):
    resp = client.get("/api/analytics/orphan-groups")
    assert resp.status_code == 401


def test_analytics_forbidden_for_staff(client, staff_headers, graph):
    resp = client.get("/api/analytics/orphan-groups", headers=staff_headers)
    assert resp.status_code == 403
