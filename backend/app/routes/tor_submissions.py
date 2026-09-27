"""ToR submission lifecycle endpoints.

GET    /api/tor-submissions?scope=      -> role-scoped list (summaries only)
POST   /api/tor-submissions             -> create a draft
GET    /api/tor-submissions/<uuid>      -> one submission, incl. its form JSON
PUT    /api/tor-submissions/<uuid>      -> save a draft / a reviewer's edits
DELETE /api/tor-submissions/<uuid>      -> delete a draft
POST   /api/tor-submissions/<uuid>/submit   -> draft -> pending review (or live)
POST   /api/tor-submissions/<uuid>/approve  -> superuser only
POST   /api/tor-submissions/<uuid>/reject   -> superuser only

Ownership and visibility live in the service, checked against the authenticated
user, so no endpoint here can be widened by a client passing a different scope.
"""

from flask import request
from flask_restx import Namespace, Resource

from app.auth import get_current_user, require_role
from app.db_schema import Role
from app.services import tor_submission_service


def register(api, M) -> None:
    ns = Namespace(
        "tor-submissions",
        path="/tor-submissions",
        description="ToR draft, review and approval lifecycle",
    )

    @ns.route("")
    class SubmissionCollection(Resource):
        @ns.doc("list_tor_submissions")
        @ns.param(
            "scope",
            "mine (default for staff) | history | pending (superuser only)",
        )
        @ns.response(200, "Submissions", M["tor_submission_list"])
        @ns.response(403, "Scope not permitted for this role")
        @require_role(Role.STAFF, Role.SUPER_USER)
        def get(self):
            """List submissions visible to the caller.

            ``mine`` is every stage of the caller's own forms. ``history`` and
            ``pending`` are superuser-only and org-wide; drafts are never
            org-wide, so they appear in neither.
            """
            body, status = tor_submission_service.list_submissions(
                get_current_user(), request.args.get("scope")
            )
            return body, status

        @ns.doc("create_tor_draft")
        @ns.expect(M["tor_draft_request"], validate=False)
        @ns.response(201, "Draft created", M["tor_submission"])
        @ns.response(400, "Malformed form data")
        @require_role(Role.STAFF, Role.SUPER_USER)
        def post(self):
            """Save a partially-completed ToR form as a draft.

            The full ToR validation is deliberately **not** run here — a draft
            is partial by definition. Only the JSON shape and a size cap are
            enforced; the real validation happens on submit.
            """
            payload = request.get_json(silent=True) or {}
            body, status = tor_submission_service.create_draft(get_current_user(), payload)
            return body, status

    @ns.route("/<string:uuid>")
    @ns.param("uuid", "Public UUID of the ToR submission")
    class SubmissionItem(Resource):
        @ns.doc("get_tor_submission")
        @ns.response(200, "The submission", M["tor_submission"])
        @ns.response(404, "Not found, or not visible to this caller")
        @require_role(Role.STAFF, Role.SUPER_USER)
        def get(self, uuid: str):
            """One submission including its stored form JSON.

            A submission the caller may not see returns 404 rather than 403 —
            a 403 would confirm that it exists.
            """
            body, status = tor_submission_service.get_submission(get_current_user(), uuid)
            return body, status

        @ns.doc("update_tor_submission")
        @ns.expect(M["tor_draft_request"], validate=False)
        @ns.response(200, "Saved", M["tor_submission"])
        @ns.response(409, "Not in an editable state")
        @require_role(Role.STAFF, Role.SUPER_USER)
        def put(self, uuid: str):
            """Save a draft (its owner) or a form under review (a superuser)."""
            payload = request.get_json(silent=True) or {}
            body, status = tor_submission_service.update_submission(
                get_current_user(), uuid, payload
            )
            return body, status

        @ns.doc("delete_tor_draft")
        @ns.response(200, "Deleted")
        @ns.response(409, "Only a draft can be deleted")
        @require_role(Role.STAFF, Role.SUPER_USER)
        def delete(self, uuid: str):
            """Delete one of the caller's own drafts."""
            body, status = tor_submission_service.delete_draft(get_current_user(), uuid)
            return body, status

    @ns.route("/<string:uuid>/submit")
    @ns.param("uuid", "Public UUID of the ToR submission")
    class SubmissionSubmit(Resource):
        @ns.doc("submit_tor_draft")
        @ns.response(200, "Submitted", M["tor_submission"])
        @ns.response(400, "Validation failed")
        @require_role(Role.STAFF, Role.SUPER_USER)
        def post(self, uuid: str):
            """Send a draft for review, running the full ToR validation.

            A staff submission creates a ``Proposed`` group; a superuser's
            bypasses review and goes straight to ``Active``.
            """
            body, status = tor_submission_service.submit_submission(get_current_user(), uuid)
            return body, status

    @ns.route("/<string:uuid>/approve")
    @ns.param("uuid", "Public UUID of the ToR submission")
    class SubmissionApprove(Resource):
        @ns.doc("approve_tor_submission")
        @ns.expect(M["tor_review_request"], validate=False)
        @ns.response(200, "Approved", M["tor_submission"])
        @ns.response(409, "Not awaiting review")
        @require_role(Role.SUPER_USER)
        def post(self, uuid: str):
            """Approve a pending ToR, flipping its group to ``Active`` in place."""
            payload = request.get_json(silent=True) or {}
            body, status = tor_submission_service.approve_submission(
                get_current_user(), uuid, payload.get("admin_comment")
            )
            return body, status

    @ns.route("/<string:uuid>/reject")
    @ns.param("uuid", "Public UUID of the ToR submission")
    class SubmissionReject(Resource):
        @ns.doc("reject_tor_submission")
        @ns.expect(M["tor_review_request"], validate=False)
        @ns.response(200, "Rejected", M["tor_submission"])
        @ns.response(400, "A reason is required")
        @ns.response(409, "Not awaiting review")
        @require_role(Role.SUPER_USER)
        def post(self, uuid: str):
            """Reject a pending ToR.

            ``admin_comment`` is required: rejection is terminal, so this is the
            only chance to tell the submitter why. The group is removed from the
            graph and its name becomes reusable.
            """
            payload = request.get_json(silent=True) or {}
            body, status = tor_submission_service.reject_submission(
                get_current_user(), uuid, payload.get("admin_comment")
            )
            return body, status

    api.add_namespace(ns)
