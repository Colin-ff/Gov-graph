from typing import Any


def _title_case(value: str) -> str:
    """Mirror tor_service._title_case: capitalise each word's first letter
    only, so role names normalised by the backend (e.g. "Note taker" ->
    "Note Taker") compare correctly against what was submitted.
    """
    return " ".join(word[:1].upper() + word[1:] for word in value.split())


def test_register_group_returns_201_and_persists(client, admin_headers):
    """
    Submit a ToR form and check that it's persisted in the database.
    :param client:
    :param admin_headers: dev auth header for a privileged (ADMIN) caller.
    :return:
    """
    # The first relation below reports to an existing parent group, so that
    # group has to actually exist first — create it before the main payload.
    parent_payload = _group_payload(
        [
            _member("Parent", "Chair", ["Chair"], "parent.chair@unsw.edu.au"),
            _member("Parent", "Secretariat", ["Secretariat"], "parent.sec@unsw.edu.au"),
        ]
    )
    parent_payload["group_name"] = "UNSW Audit Committee"
    parent_response = client.post("/api/tor", json=parent_payload, headers=admin_headers)
    assert parent_response.status_code == 201, parent_response.get_data(as_text=True)
    parent_uuid = parent_response.get_json()["uuid"]

    # reference tor_form.json
    payload: dict[str, Any] = {
        "group_name": "Audit working group",    # backend should process group_name as Title Case
        "entity_type": "Working group",     # backend should process entity_type as Title Case
        "purpose": (
            "Review the effectiveness of internal audit recommendations and track "
            "their implementation across faculties; report quarterly to the UNSW "
            "Audit Committee on outstanding remediation items."
        ),
        "responsibilities": (
            "Maintain the audit action register; follow up with control owners on "
            "overdue items; prepare summary papers for the parent committee; and "
            "escalate unresolved high-risk findings to the Chief Audit Executive."
        ),
        "members": [
            {
                # member is not previously existed in the database
                "uuid": None,
                "first_name": "Ashley",
                "last_name": "Clay",
                "gender": "female",
                "email": "a.clay2@unsw.edu.au",
                "phone": "0438 902 715",
                "zID": "z5298471",
                "roles": [
                    "Note taker",   # backend should process roles as Title Case
                    "Treasurer"
                ],
                "is_student": False,
                "is_faculty": True,
                "is_external": False
            },
            {
                "uuid": None,
                "first_name": "Alex",
                "last_name": "Li",
                "gender": "male",
                "email": "a.li4@unsw.edu.au",
                "phone": "0451 326 880",
                "zID": "z5347016",
                "roles": [
                    "Chair",
                    "Secretariat"
                ],
                "is_student": True,
                "is_external": False
            },
            {
                "uuid": None,
                "first_name": "Grace",
                "last_name": "Tan",
                "gender": "other",
                "email": "grace.tan@deloitte.com.au",
                "phone": "0407 213 558",
                "zID": None,
                "roles": [
                    "Consultant"
                ],
                "is_student": False,
                "is_external": True
            },
            {
                "uuid": None,
                "first_name": "Owen",
                "last_name": "Hart",
                "gender": "male",
                "email": "owen.hart@kpmg.com.au",
                "phone": "0419 884 027",
                "zID": None,
                "roles": [
                    "External Advisor"
                ],
                "is_student": False,
                "is_external": True
            }
        ],
        "relations": [
            {
                "group_uuid": parent_uuid,
                "relation_type": "Subgroup",
                "existing_group": True,
                "note": "Reports to the UNSW Audit Committee as its parent governance body."
            },
            {
                "group_name": "Data Governance Steering Group",
                "relation_type": "Affiliation",
                "existing_group": False,
                "chair_first_name": "Priya",
                "chair_last_name": "Nair",
                "chair_email": "p.nair@unsw.edu.au",
                "secretariat_first_name": "Marcus",
                "secretariat_last_name": "Webb",
                "secretariat_email": "m.webb@unsw.edu.au",
                "note": "Proposed new group; shares membership on data-related audit findings."
            }
        ],
        "meeting_frequency_per_year": 6,
        "meeting_duration_hour": 2,
        "reference_links": [
            {
                "title": "ToR",
                "url": "https://www.unsw.edu.au/governance/audit-working-group/terms-of-reference"
            },
            {
                "title": "Meeting Minutes (RAMS)",
                "url": "https://rams.unsw.edu.au/audit-working-group/minutes"
            }
        ],
        "start_date": "2024-06-01",
        "review_date": "2026-06-01"
    }

    # Group creation flows through POST /api/tor. A privileged caller edits the
    # graph directly and gets 201 Created (common staff would get 202 Accepted).
    post_tor_response = client.post("/api/tor", json=payload, headers=admin_headers)
    assert post_tor_response.status_code == 201, post_tor_response.get_data(as_text=True)

    # The backend owns the group's UUID and returns it so the frontend can fetch
    # the new group; the frontend never invents the UUID itself.
    post_tor_response_json = post_tor_response.get_json()
    group_uuid = post_tor_response_json["uuid"]
    assert group_uuid

    # follow-up requests to prove information is persisted
    # 1. validate group information (reference organisation.json)
    group_info_response = client.get(f"/api/groups/{group_uuid}", headers=admin_headers)
    assert group_info_response.status_code == 200
    org_info_json = group_info_response.get_json()

    assert org_info_json["uuid"] == group_uuid
    # group_name / entity_type are normalised to Title Case by the backend.
    assert org_info_json["group_name"] == "Audit Working Group"
    assert org_info_json["entity_type"] == "Working Group"
    assert org_info_json["status"] == "active"  # server default, lower-cased enum
    assert org_info_json["purpose"] == payload["purpose"]
    assert org_info_json["responsibilities"] == payload["responsibilities"]
    assert org_info_json["meeting_frequency_per_year"] == payload["meeting_frequency_per_year"]
    assert org_info_json["meeting_duration_hour"] == payload["meeting_duration_hour"]
    assert org_info_json["start_date"] == payload["start_date"]
    assert org_info_json["review_date"] == payload["review_date"]
    assert org_info_json["reference_links"] == payload["reference_links"]

    # 2. validate group members are persisted
    submitted_by_name = {
        (member["first_name"], member["last_name"]): member for member in payload["members"]
    }
    assert len(org_info_json["membership"]) == len(payload["members"])

    for entry in org_info_json["membership"]:
        original = submitted_by_name[(entry["first_name"], entry["last_name"])]
        # roles recorded on the membership match what was submitted, modulo
        # the backend's Title Case normalisation.
        assert sorted(entry["roles"]) == sorted(_title_case(r) for r in original["roles"])

        # full person profile (privileged view) is persisted and self-consistent
        member_info_response = client.get(
            f"/api/person/{entry['uuid']}", headers=admin_headers
        )
        assert member_info_response.status_code == 200
        member_info_json = member_info_response.get_json()

        assert member_info_json["uuid"] == entry["uuid"]
        assert member_info_json["first_name"] == original["first_name"]
        assert member_info_json["last_name"] == original["last_name"]
        assert member_info_json["gender"] == original["gender"]
        assert member_info_json["is_student"] == original["is_student"]
        assert member_info_json["is_external"] == original["is_external"]
        assert member_info_json["email"] == original["email"]
        assert member_info_json["phone"] == original["phone"]
        assert member_info_json["zID"] == original["zID"]

        # the person is linked back to this group with the submitted roles
        affiliation = next(
            group
            for group in member_info_json["affiliated_groups"]
            if group["group_uuid"] == group_uuid
        )
        assert sorted(affiliation["roles"]) == sorted(_title_case(r) for r in original["roles"])


def _member(first_name, last_name, roles, email):
    """Minimal member object in the ToR transport shape."""
    return {
        "uuid": None,
        "first_name": first_name,
        "last_name": last_name,
        "gender": "other",
        "email": email,
        "phone": None,
        "zID": "z1234567",  # required for internal (non-external) members
        "roles": roles,
        # Exactly one representation flag must be set.
        "is_student": False,
        "is_faculty": True,
        "is_external": False,
    }


def _group_payload(members):
    return {
        "group_name": "Ghost WG",
        "entity_type": "Working Group",
        "purpose": "Placeholder purpose.",
        "responsibilities": "Placeholder responsibilities.",
        "members": members,
        "start_date": "2024-06-01",
        "review_date": "2026-06-01",
    }


def test_register_group_missing_chair_is_rejected(client, admin_headers):
    # No member holds the Chair role -> validation failure (chair is compulsory).
    payload = _group_payload([_member("Sam", "Lee", ["Secretariat"], "s.lee@unsw.edu.au")])
    resp = client.post("/api/tor", json=payload, headers=admin_headers)
    assert resp.status_code == 400


def test_register_group_missing_secretariat_is_rejected(client, admin_headers):
    # No member holds the Secretariat role -> validation failure.
    payload = _group_payload([_member("Sam", "Lee", ["Chair"], "s.lee@unsw.edu.au")])
    resp = client.post("/api/tor", json=payload, headers=admin_headers)
    assert resp.status_code == 400


def test_chair_may_equal_secretariat(client, admin_headers):
    # Client said the two roles CAN be the same person — lock that in.
    payload = _group_payload(
        [_member("Sam", "Lee", ["Chair", "Secretariat"], "s.lee@unsw.edu.au")]
    )
    resp = client.post("/api/tor", json=payload, headers=admin_headers)
    assert resp.status_code == 201
