from app.db_schema import (
    GovernanceGroup,
    GroupReferenceLink,
    GroupRelationship,
    GroupStatus,
    Membership,
    MembershipRole,
    MembershipRoleType,
    Person,
)
from app.extensions import db


def _valid_payload(**overrides):
    payload = {
        "group_name": "Audit Working Group",
        "entity_type": "Working Group",
        "purpose": "Review internal audit recommendations.",
        "responsibilities": "Maintain the audit action register.",
        "members": [
            {
                "uuid": None,
                "first_name": "Ashley",
                "last_name": "Clay",
                "gender": "female",
                "email": "a.clay@unsw.edu.au",
                "phone": "0438 902 715",
                "zID": "z5298471",
                "roles": ["Chair"],
                "is_student": False,
                "is_faculty": True,
                "is_external": False,
            },
            {
                "uuid": None,
                "first_name": "Alex",
                "last_name": "Li",
                "gender": "male",
                "email": "a.li@unsw.edu.au",
                "phone": "0451 326 880",
                "zID": "z5347016",
                "roles": ["Secretariat"],
                "is_student": True,
                "is_external": False,
            },
        ],
        "relations": [],
        "reference_links": [
            {"title": "ToR", "url": "https://www.unsw.edu.au/governance/audit-wg/tor"},
        ],
        "meeting_frequency_per_year": 6,
        "meeting_duration_hour": 2,
        "start_date": "2024-06-01",
        "review_date": "2026-06-01",
    }
    payload.update(overrides)
    return payload


def test_submit_tor_form_success(app, client, admin_headers):
    resp = client.post("/api/tor", json=_valid_payload(), headers=admin_headers)

    assert resp.status_code == 201, resp.get_data(as_text=True)
    body = resp.get_json()
    assert body["message"] == "Group created successfully."
    assert isinstance(body["uuid"], str)

    with app.app_context():
        group = GovernanceGroup.query.filter_by(uuid=body["uuid"]).first()
        assert group is not None
        assert group.group_name == "Audit Working Group"
        assert group.responsibilities == "Maintain the audit action register."
        assert group.status == GroupStatus.ACTIVE


def test_submit_tor_form_normalises_title_case(app, client, admin_headers):
    payload = _valid_payload(group_name="UNSW audit working group", entity_type="working group")

    resp = client.post("/api/tor", json=payload, headers=admin_headers)

    assert resp.status_code == 201, resp.get_data(as_text=True)
    with app.app_context():
        group = GovernanceGroup.query.filter_by(uuid=resp.get_json()["uuid"]).first()
        # Acronyms survive (UNSW stays UNSW); other words get capitalised.
        assert group.group_name == "UNSW Audit Working Group"


def test_submit_tor_form_missing_required_fields(client, admin_headers):
    resp = client.post("/api/tor", json={}, headers=admin_headers)

    assert resp.status_code == 400
    body = resp.get_json()
    assert body["error"] == "Validation failed"
    assert "group_name" in body["details"]
    assert "entity_type" in body["details"]
    assert "purpose" in body["details"]
    assert "responsibilities" in body["details"]
    assert "members" in body["details"]


def test_submit_tor_form_requires_authentication(client):
    resp = client.post("/api/tor", json=_valid_payload())

    assert resp.status_code == 401


def test_submit_tor_form_invalid_relationship_target(client, admin_headers):
    payload = _valid_payload(
        relations=[
            {
                "group_uuid": "00000000-0000-0000-0000-000000000000",
                "relation_type": "Subgroup",
                "existing_group": True,
            }
        ]
    )

    resp = client.post("/api/tor", json=payload, headers=admin_headers)

    assert resp.status_code == 400
    body = resp.get_json()
    assert body["error"] == "Validation failed"
    assert body["details"]["relations[0].group_uuid"] == (
        "No governance group exists with this uuid."
    )


def test_submit_tor_form_with_proposed_relation(app, client, admin_headers):
    """Naming an unregistered reporting line needs only the group's name."""
    payload = _valid_payload(
        relations=[
            {
                "group_name": "Data Governance Steering Group",
                "existing_group": False,
                "note": "Escalates data-related findings.",
            }
        ]
    )

    resp = client.post("/api/tor", json=payload, headers=admin_headers)

    assert resp.status_code == 201, resp.get_data(as_text=True)

    with app.app_context():
        assert GovernanceGroup.query.count() == 2
        proposed = GovernanceGroup.query.filter_by(
            group_name="Data Governance Steering Group"
        ).first()
        assert proposed is not None
        assert proposed.status == GroupStatus.PROPOSED


def _reports_to(group_name):
    return [{"group_name": group_name, "existing_group": False}]


def _distinct(member, tag):
    """A copy of ``member`` that resolves to a different person.

    People are matched by uuid -> zID -> email, so a second group needs members
    whose email *and* zID both differ, or the write path will reuse the person
    from the first group and the test will not exercise what it claims to.
    """
    return dict(
        member,
        email=f"{tag}.{member['email']}",
        zID=None,
        is_student=False,
        is_faculty=False,
        is_external=True,
    )


def test_proposed_target_is_reused_not_duplicated(app, client, admin_headers):
    """Two groups naming the same parent share one node, not one each.

    This is the bug that made the visualisation unreadable: each submission used
    to mint its own Proposed row, so one real body appeared several times.
    """
    first = _valid_payload(relations=_reports_to("Academic Board"))
    second = _valid_payload(
        group_name="Research Working Group",
        # Same parent, different capitalisation — must still match.
        relations=_reports_to("academic board"),
        members=[_distinct(m, "second") for m in _valid_payload()["members"]],
    )

    assert client.post("/api/tor", json=first, headers=admin_headers).status_code == 201
    resp = client.post("/api/tor", json=second, headers=admin_headers)
    assert resp.status_code == 201, resp.get_data(as_text=True)

    with app.app_context():
        boards = GovernanceGroup.query.filter(
            db.func.lower(GovernanceGroup.group_name) == "academic board"
        ).all()
        assert len(boards) == 1
        # Both submitting groups now report to that single node.
        assert GroupRelationship.query.filter_by(target_group_id=boards[0].id).count() == 2


def test_registering_a_proposed_group_adopts_it(app, client, admin_headers):
    """Registering a previously-named group keeps its uuid and inbound edges."""
    client.post(
        "/api/tor",
        json=_valid_payload(relations=_reports_to("Academic Board")),
        headers=admin_headers,
    )

    with app.app_context():
        proposed = GovernanceGroup.query.filter_by(group_name="Academic Board").first()
        proposed_uuid = proposed.uuid
        assert proposed.status == GroupStatus.PROPOSED

    resp = client.post(
        "/api/tor",
        json=_valid_payload(
            group_name="Academic Board",
            members=[_distinct(m, "board") for m in _valid_payload()["members"]],
        ),
        headers=admin_headers,
    )

    assert resp.status_code == 201, resp.get_data(as_text=True)
    # Same row: the uuid other groups already point at is preserved.
    assert resp.get_json()["uuid"] == proposed_uuid

    with app.app_context():
        board = GovernanceGroup.query.filter_by(uuid=proposed_uuid).first()
        assert board.status == GroupStatus.ACTIVE
        assert board.purpose == "Review internal audit recommendations."
        # The reporting line declared before registration survived.
        assert GroupRelationship.query.filter_by(target_group_id=board.id).count() == 1


def test_registering_an_existing_group_name_is_rejected(client, admin_headers):
    client.post("/api/tor", json=_valid_payload(), headers=admin_headers)

    resp = client.post(
        "/api/tor",
        json=_valid_payload(members=[_distinct(m, "dup") for m in _valid_payload()["members"]]),
        headers=admin_headers,
    )

    assert resp.status_code == 400
    assert resp.get_json()["details"]["group_name"] == (
        "A group with this name is already registered."
    )


def test_chair_and_secretariat_same_person_makes_one_membership(app, client, admin_headers):
    """One person holding two positions is one membership with two roles.

    Two membership rows would double-count them in every analytics query.
    """
    member = _valid_payload()["members"][0]
    payload = _valid_payload(
        members=[
            dict(member, roles=["Chair"]),
            dict(member, roles=["Secretariat"]),
        ]
    )

    resp = client.post("/api/tor", json=payload, headers=admin_headers)
    assert resp.status_code == 201, resp.get_data(as_text=True)

    with app.app_context():
        group = GovernanceGroup.query.filter_by(uuid=resp.get_json()["uuid"]).first()
        memberships = Membership.query.filter_by(group_id=group.id).all()
        assert len(memberships) == 1
        roles = {
            row.type_name
            for row in db.session.query(MembershipRoleType.type_name)
            .join(MembershipRole, MembershipRole.role_type_id == MembershipRoleType.id)
            .filter(MembershipRole.membership_id == memberships[0].id)
            .all()
        }
        assert roles == {"Chair", "Secretariat"}


def test_reference_link_url_gets_https_prefix(app, client, admin_headers):
    """A bare domain is fixed up rather than rejected."""
    payload = _valid_payload(
        reference_links=[{"title": "ToR", "url": "www.unsw.edu.au/governance/tor"}]
    )

    resp = client.post("/api/tor", json=payload, headers=admin_headers)
    assert resp.status_code == 201, resp.get_data(as_text=True)

    with app.app_context():
        group = GovernanceGroup.query.filter_by(uuid=resp.get_json()["uuid"]).first()
        link = GroupReferenceLink.query.filter_by(group_id=group.id).first()
        assert link.url == "https://www.unsw.edu.au/governance/tor"


def test_reference_link_rejects_non_http_scheme(client, admin_headers):
    payload = _valid_payload(reference_links=[{"title": "Bad", "url": "javascript:alert(1)"}])

    resp = client.post("/api/tor", json=payload, headers=admin_headers)

    assert resp.status_code == 400
    assert resp.get_json()["details"]["reference_links[0].url"] == (
        "Must be an http:// or https:// URL."
    )


def test_review_date_must_be_after_start_date(client, admin_headers):
    """Equal dates describe a zero-length validity window."""
    payload = _valid_payload(start_date="2025-01-01", review_date="2025-01-01")

    resp = client.post("/api/tor", json=payload, headers=admin_headers)

    assert resp.status_code == 400
    assert resp.get_json()["details"]["review_date"] == "Must be later than the start date."


def test_dates_are_required(client, admin_headers):
    payload = _valid_payload()
    del payload["start_date"]
    del payload["review_date"]

    resp = client.post("/api/tor", json=payload, headers=admin_headers)

    assert resp.status_code == 400
    details = resp.get_json()["details"]
    assert details["start_date"] == "Required."
    assert details["review_date"] == "Required."


def test_past_start_date_is_allowed(client, admin_headers):
    """Groups that have been running for years still need registering."""
    payload = _valid_payload(start_date="2015-01-01", review_date="2030-01-01")

    resp = client.post("/api/tor", json=payload, headers=admin_headers)

    assert resp.status_code == 201, resp.get_data(as_text=True)


def test_member_requires_exactly_one_representation(client, admin_headers):
    payload = _valid_payload()
    payload["members"][0].update(is_student=True, is_faculty=True, is_external=False)

    resp = client.post("/api/tor", json=payload, headers=admin_headers)

    assert resp.status_code == 400
    assert "members[0].member_representation" in resp.get_json()["details"]


def _person_uuid(client, headers, group_uuid, index=0):
    return client.get(f"/api/groups/{group_uuid}", headers=headers).get_json()["membership"][index][
        "uuid"
    ]


def test_existing_member_needs_only_roles(app, client, admin_headers):
    """A member resolved by uuid carries no contact details.

    The write path keeps the stored person and discards everything else, so
    demanding those fields would make the submitter retype data that is then
    thrown away — which is exactly what the picker exists to avoid.
    """
    first = client.post("/api/tor", json=_valid_payload(), headers=admin_headers)
    uuid = _person_uuid(client, admin_headers, first.get_json()["uuid"])

    resp = client.post(
        "/api/tor",
        json=_valid_payload(
            group_name="Second Committee",
            members=[{"uuid": uuid, "roles": ["Chair", "Secretariat"]}],
        ),
        headers=admin_headers,
    )

    assert resp.status_code == 201, resp.get_data(as_text=True)
    with app.app_context():
        # Reused, not duplicated.
        assert Person.query.count() == 2


def test_existing_member_details_are_not_overwritten(app, client, admin_headers):
    """Contradictory details on a resolved member must not touch the record."""
    first = client.post("/api/tor", json=_valid_payload(), headers=admin_headers)
    uuid = _person_uuid(client, admin_headers, first.get_json()["uuid"])

    client.post(
        "/api/tor",
        json=_valid_payload(
            group_name="Third Committee",
            members=[
                {
                    "uuid": uuid,
                    "first_name": "WRONG",
                    "last_name": "WRONG",
                    "gender": "male",
                    "email": "wrong@example.com",
                    "zID": "z9999999",
                    "roles": ["Chair", "Secretariat"],
                    "is_student": True,
                    "is_faculty": False,
                    "is_external": False,
                }
            ],
        ),
        headers=admin_headers,
    )

    with app.app_context():
        person = Person.query.filter_by(uuid=uuid).first()
        assert person.first_name != "WRONG"
        assert person.email != "wrong@example.com"
        assert person.z_id != "z9999999"


def test_unresolvable_uuid_still_validates_typed_fields(client, admin_headers):
    """A uuid that matches nothing must not waive validation.

    Otherwise a stale or invented uuid would smuggle a member past every check.
    """
    resp = client.post(
        "/api/tor",
        json=_valid_payload(
            members=[
                {
                    "uuid": "00000000-0000-0000-0000-000000000000",
                    "roles": ["Chair", "Secretariat"],
                }
            ]
        ),
        headers=admin_headers,
    )

    assert resp.status_code == 400
    details = resp.get_json()["details"]
    assert details["members[0].first_name"] == "Required."
    assert details["members[0].email"] == "Required."


def test_member_requires_gender(client, admin_headers):
    payload = _valid_payload()
    payload["members"][0]["gender"] = ""

    resp = client.post("/api/tor", json=payload, headers=admin_headers)

    assert resp.status_code == 400
    assert resp.get_json()["details"]["members[0].gender"] == "Required."
