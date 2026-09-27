"""ToR review lifecycle: draft -> pending_review -> approved | rejected."""

from app.db_schema import (
    GovernanceGroup,
    GroupRelationship,
    GroupStatus,
    Membership,
    TorSubmission,
    TorSubmissionStatus,
)
from tests.test_tor import _valid_payload


def test_staff_submit_creates_proposed_group_and_pending_submission(app, client, staff_headers):
    """A common user's submission awaits review: the group is only Proposed."""
    resp = client.post("/api/tor", json=_valid_payload(), headers=staff_headers)

    assert resp.status_code == 201, resp.get_data(as_text=True)
    body = resp.get_json()
    assert body["message"] == "ToR submitted for review."

    with app.app_context():
        group = GovernanceGroup.query.filter_by(uuid=body["uuid"]).first()
        assert group is not None
        assert group.status == GroupStatus.PROPOSED

        submission = TorSubmission.query.filter_by(uuid=body["submission_uuid"]).first()
        assert submission is not None
        assert submission.status == TorSubmissionStatus.PENDING_REVIEW
        assert submission.group_uuid == group.uuid
        assert submission.submitted_by_email == "staff@unsw.edu.au"
        assert submission.submitted_at is not None
        assert submission.reviewed_at is None
        assert submission.form_json_data["group_name"] == "Audit Working Group"


def test_superuser_submit_creates_active_group_and_approved_submission(app, client, admin_headers):
    """A superuser bypasses review, but the submission is still recorded."""
    resp = client.post("/api/tor", json=_valid_payload(), headers=admin_headers)

    assert resp.status_code == 201, resp.get_data(as_text=True)
    body = resp.get_json()

    with app.app_context():
        group = GovernanceGroup.query.filter_by(uuid=body["uuid"]).first()
        assert group.status == GroupStatus.ACTIVE

        submission = TorSubmission.query.filter_by(uuid=body["submission_uuid"]).first()
        assert submission.status == TorSubmissionStatus.APPROVED
        assert submission.submitted_by_email == "admin@unsw.edu.au"
        assert submission.reviewed_by == "admin@unsw.edu.au"
        assert submission.reviewed_at is not None


def test_second_submission_for_a_pending_name_is_rejected(app, client, staff_headers):
    """The pending-review guard: B must not silently overwrite A's submission.

    Without it the second submission would *adopt* the Proposed group the first
    created, wiping its members while A's row still claimed pending_review.
    """
    first = client.post("/api/tor", json=_valid_payload(), headers=staff_headers)
    assert first.status_code == 201, first.get_data(as_text=True)

    second = client.post("/api/tor", json=_valid_payload(), headers=staff_headers)

    assert second.status_code == 400, second.get_data(as_text=True)
    assert "awaiting review" in second.get_json()["details"]["group_name"]


def test_proposed_stub_is_still_adoptable(app, client, staff_headers):
    """A Proposed group with no submission behind it is an empty stub.

    It must stay adoptable — the pending-review guard keys off a submission
    row, not the group's status, precisely so this path keeps working.
    """
    parent = _valid_payload(
        group_name="Academic Board",
        relations=[],
    )
    child = _valid_payload(
        group_name="Teaching Committee",
        relations=[{"existing_group": False, "group_name": "Research Board"}],
    )
    assert client.post("/api/tor", json=parent, headers=staff_headers).status_code == 201
    assert client.post("/api/tor", json=child, headers=staff_headers).status_code == 201

    # "Research Board" now exists only as a stub minted by the child's ToR.
    resp = client.post(
        "/api/tor", json=_valid_payload(group_name="Research Board"), headers=staff_headers
    )

    assert resp.status_code == 201, resp.get_data(as_text=True)
    with app.app_context():
        assert GovernanceGroup.query.filter_by(group_name="Research Board").count() == 1
        # The child's reporting line still points at the adopted row.
        assert GroupRelationship.query.count() >= 1


# --------------------------------------------------------------------------
# Drafts
# --------------------------------------------------------------------------


def _save_draft(client, headers, form=None):
    """Create a draft and return its response body."""
    resp = client.post(
        "/api/tor-submissions",
        json={"form_json_data": form if form is not None else {"group_name": "Half Typed"}},
        headers=headers,
    )
    assert resp.status_code == 201, resp.get_data(as_text=True)
    return resp.get_json()


def test_save_draft_persists_partial_form_without_touching_the_graph(app, client, staff_headers):
    """The important half: a draft writes no group, however incomplete it is."""
    with app.app_context():
        before = GovernanceGroup.query.count()

    body = _save_draft(client, staff_headers, {"group_name": "Half Typed", "purpose": "TBC"})

    assert body["status"] == "draft"
    assert body["group_name"] == "Half Typed"
    assert body["submitted_at"] is None
    assert body["group_uuid"] is None

    with app.app_context():
        assert GovernanceGroup.query.count() == before
        submission = TorSubmission.query.filter_by(uuid=body["uuid"]).first()
        assert submission.form_json_data["purpose"] == "TBC"


def test_update_draft_overwrites_form_json(app, client, staff_headers):
    draft = _save_draft(client, staff_headers)

    resp = client.put(
        f"/api/tor-submissions/{draft['uuid']}",
        json={"form_json_data": {"group_name": "Renamed Group", "purpose": "Settled."}},
        headers=staff_headers,
    )

    assert resp.status_code == 200, resp.get_data(as_text=True)
    body = resp.get_json()
    assert body["group_name"] == "Renamed Group"
    assert body["form_json_data"]["purpose"] == "Settled."


def test_submitting_an_incomplete_draft_fails_and_leaves_it_a_draft(app, client, staff_headers):
    draft = _save_draft(client, staff_headers)

    resp = client.post(f"/api/tor-submissions/{draft['uuid']}/submit", headers=staff_headers)

    assert resp.status_code == 400, resp.get_data(as_text=True)
    assert "entity_type" in resp.get_json()["details"]
    with app.app_context():
        assert (
            TorSubmission.query.filter_by(uuid=draft["uuid"]).first().status
            == TorSubmissionStatus.DRAFT
        )


def test_submitting_a_complete_draft_creates_a_proposed_group(app, client, staff_headers):
    draft = _save_draft(client, staff_headers, _valid_payload())

    resp = client.post(f"/api/tor-submissions/{draft['uuid']}/submit", headers=staff_headers)

    assert resp.status_code == 200, resp.get_data(as_text=True)
    body = resp.get_json()
    assert body["status"] == "pending_review"
    assert body["submitted_at"] is not None

    with app.app_context():
        group = GovernanceGroup.query.filter_by(uuid=body["group_uuid"]).first()
        assert group.status == GroupStatus.PROPOSED


def test_draft_can_be_deleted_by_its_owner(app, client, staff_headers):
    draft = _save_draft(client, staff_headers)

    resp = client.delete(f"/api/tor-submissions/{draft['uuid']}", headers=staff_headers)

    assert resp.status_code == 200, resp.get_data(as_text=True)
    with app.app_context():
        assert TorSubmission.query.filter_by(uuid=draft["uuid"]).first() is None


# --------------------------------------------------------------------------
# Review
# --------------------------------------------------------------------------


def _pending(client, staff_headers, **overrides):
    """A staff submission sitting in pending_review."""
    resp = client.post("/api/tor", json=_valid_payload(**overrides), headers=staff_headers)
    assert resp.status_code == 201, resp.get_data(as_text=True)
    return resp.get_json()


def test_approve_flips_the_proposed_group_to_active_in_place(
    app, client, staff_headers, admin_headers
):
    submitted = _pending(client, staff_headers)

    resp = client.post(
        f"/api/tor-submissions/{submitted['submission_uuid']}/approve",
        json={"admin_comment": "Looks good."},
        headers=admin_headers,
    )

    assert resp.status_code == 200, resp.get_data(as_text=True)
    body = resp.get_json()
    assert body["status"] == "approved"
    assert body["reviewed_by"] == "admin@unsw.edu.au"
    # Same group, not a duplicate — this is what group_uuid adoption protects.
    assert body["group_uuid"] == submitted["uuid"]

    with app.app_context():
        assert GovernanceGroup.query.filter_by(group_name="Audit Working Group").count() == 1
        group = GovernanceGroup.query.filter_by(uuid=submitted["uuid"]).first()
        assert group.status == GroupStatus.ACTIVE


def test_approve_preserves_inbound_reporting_edges(app, client, staff_headers, admin_headers):
    """The regression uuid-based adoption exists to prevent.

    A child names "Ethics Board" as its reporting line, minting a Proposed stub.
    A ToR for that board is then submitted and approved; the child's edge must
    survive, which it only does if approval updates the same row.
    """
    child = _valid_payload(
        group_name="Teaching Committee",
        relations=[{"existing_group": False, "group_name": "Ethics Board"}],
    )
    assert client.post("/api/tor", json=child, headers=staff_headers).status_code == 201

    submitted = _pending(client, staff_headers, group_name="Ethics Board")
    resp = client.post(
        f"/api/tor-submissions/{submitted['submission_uuid']}/approve",
        json={},
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.get_data(as_text=True)

    with app.app_context():
        board = GovernanceGroup.query.filter_by(group_name="Ethics Board").one()
        assert board.status == GroupStatus.ACTIVE
        teaching = GovernanceGroup.query.filter_by(group_name="Teaching Committee").one()
        edge = GroupRelationship.query.filter_by(
            source_group_id=teaching.id, target_group_id=board.id
        ).first()
        assert edge is not None


def test_reject_removes_the_group_from_the_graph(app, client, staff_headers, admin_headers):
    submitted = _pending(client, staff_headers)

    resp = client.post(
        f"/api/tor-submissions/{submitted['submission_uuid']}/reject",
        json={"admin_comment": "Duplicates the Audit Committee."},
        headers=admin_headers,
    )

    assert resp.status_code == 200, resp.get_data(as_text=True)
    body = resp.get_json()
    assert body["status"] == "rejected"
    assert body["admin_comment"] == "Duplicates the Audit Committee."
    # The ToR itself survives as the record.
    assert body["form_json_data"]["group_name"] == "Audit Working Group"

    with app.app_context():
        assert GovernanceGroup.query.filter_by(uuid=submitted["uuid"]).first() is None


def test_reject_keeps_a_stub_when_another_group_reports_to_it(
    app, client, staff_headers, admin_headers
):
    """Deleting outright would destroy an edge the *other* group declared."""
    child = _valid_payload(
        group_name="Teaching Committee",
        relations=[{"existing_group": False, "group_name": "Ethics Board"}],
    )
    assert client.post("/api/tor", json=child, headers=staff_headers).status_code == 201

    submitted = _pending(client, staff_headers, group_name="Ethics Board")
    resp = client.post(
        f"/api/tor-submissions/{submitted['submission_uuid']}/reject",
        json={"admin_comment": "Not required."},
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.get_data(as_text=True)

    with app.app_context():
        board = GovernanceGroup.query.filter_by(group_name="Ethics Board").one()
        assert board.status == GroupStatus.PROPOSED
        assert board.purpose is None
        assert Membership.query.filter_by(group_id=board.id).count() == 0


def test_the_group_name_is_reusable_after_a_rejection(app, client, staff_headers, admin_headers):
    """Rejection is terminal, so the submitter must be able to start again."""
    submitted = _pending(client, staff_headers)
    client.post(
        f"/api/tor-submissions/{submitted['submission_uuid']}/reject",
        json={"admin_comment": "No."},
        headers=admin_headers,
    )

    resp = client.post("/api/tor", json=_valid_payload(), headers=staff_headers)

    assert resp.status_code == 201, resp.get_data(as_text=True)


def test_reject_requires_a_reason(app, client, staff_headers, admin_headers):
    submitted = _pending(client, staff_headers)

    resp = client.post(
        f"/api/tor-submissions/{submitted['submission_uuid']}/reject",
        json={"admin_comment": "   "},
        headers=admin_headers,
    )

    assert resp.status_code == 400, resp.get_data(as_text=True)
    assert "admin_comment" in resp.get_json()["details"]


def test_review_actions_require_a_superuser(app, client, staff_headers):
    submitted = _pending(client, staff_headers)
    uuid = submitted["submission_uuid"]

    approve = client.post(f"/api/tor-submissions/{uuid}/approve", json={}, headers=staff_headers)
    reject = client.post(
        f"/api/tor-submissions/{uuid}/reject", json={"admin_comment": "x"}, headers=staff_headers
    )

    assert approve.status_code == 403, approve.get_data(as_text=True)
    assert reject.status_code == 403, reject.get_data(as_text=True)


def test_approving_twice_conflicts(app, client, staff_headers, admin_headers):
    submitted = _pending(client, staff_headers)
    uuid = submitted["submission_uuid"]
    assert (
        client.post(
            f"/api/tor-submissions/{uuid}/approve", json={}, headers=admin_headers
        ).status_code
        == 200
    )

    second = client.post(f"/api/tor-submissions/{uuid}/approve", json={}, headers=admin_headers)

    assert second.status_code == 409, second.get_data(as_text=True)


# --------------------------------------------------------------------------
# Scoping
# --------------------------------------------------------------------------


def test_staff_cannot_read_another_users_draft(app, client, staff_headers, admin_headers):
    """404 rather than 403 — a 403 would confirm the draft exists."""
    draft = _save_draft(client, admin_headers)

    resp = client.get(f"/api/tor-submissions/{draft['uuid']}", headers=staff_headers)

    assert resp.status_code == 404, resp.get_data(as_text=True)


def test_scope_mine_excludes_other_users_submissions(app, client, staff_headers, admin_headers):
    _save_draft(client, admin_headers)
    mine = _save_draft(client, staff_headers)

    resp = client.get("/api/tor-submissions?scope=mine", headers=staff_headers)

    assert resp.status_code == 200, resp.get_data(as_text=True)
    uuids = [s["uuid"] for s in resp.get_json()["submissions"]]
    assert uuids == [mine["uuid"]]


def test_staff_cannot_request_the_superuser_scopes(app, client, staff_headers):
    for scope in ("history", "pending"):
        resp = client.get(f"/api/tor-submissions?scope={scope}", headers=staff_headers)
        assert resp.status_code == 403, resp.get_data(as_text=True)


def test_history_holds_resolved_submissions_and_never_drafts(
    app, client, staff_headers, admin_headers
):
    _save_draft(client, staff_headers)
    rejected = _pending(client, staff_headers, group_name="Rejected Group")
    client.post(
        f"/api/tor-submissions/{rejected['submission_uuid']}/reject",
        json={"admin_comment": "No."},
        headers=admin_headers,
    )
    approved = _pending(client, staff_headers, group_name="Approved Group")
    client.post(
        f"/api/tor-submissions/{approved['submission_uuid']}/approve",
        json={},
        headers=admin_headers,
    )
    pending = _pending(client, staff_headers, group_name="Pending Group")

    resp = client.get("/api/tor-submissions?scope=history", headers=admin_headers)

    assert resp.status_code == 200, resp.get_data(as_text=True)
    returned = {s["uuid"]: s["status"] for s in resp.get_json()["submissions"]}
    assert returned[rejected["submission_uuid"]] == "rejected"
    assert returned[approved["submission_uuid"]] == "approved"
    assert pending["submission_uuid"] not in returned
    assert "draft" not in returned.values()


def test_pending_scope_lists_submissions_awaiting_review(app, client, staff_headers, admin_headers):
    pending = _pending(client, staff_headers)

    resp = client.get("/api/tor-submissions?scope=pending", headers=admin_headers)

    assert resp.status_code == 200, resp.get_data(as_text=True)
    uuids = [s["uuid"] for s in resp.get_json()["submissions"]]
    assert uuids == [pending["submission_uuid"]]


def test_list_responses_omit_the_form_json(app, client, staff_headers):
    _save_draft(client, staff_headers)

    resp = client.get("/api/tor-submissions?scope=mine", headers=staff_headers)

    assert "form_json_data" not in resp.get_json()["submissions"][0]


# --------------------------------------------------------------------------
# GET /api/tor/<uuid> — previously untested
# --------------------------------------------------------------------------


def test_get_tor_form_404_when_no_submission_exists(app, client, admin_headers):
    resp = client.get("/api/tor/does-not-exist", headers=admin_headers)

    assert resp.status_code == 404, resp.get_data(as_text=True)


def test_get_tor_form_returns_the_stored_json_for_a_group(app, client, admin_headers):
    created = client.post("/api/tor", json=_valid_payload(), headers=admin_headers).get_json()

    resp = client.get(f"/api/tor/{created['uuid']}", headers=admin_headers)

    assert resp.status_code == 200, resp.get_data(as_text=True)
    assert resp.get_json()["group_name"] == "Audit Working Group"
