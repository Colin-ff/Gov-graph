"""Terms of Reference (ToR) form endpoints (T18BBANANA-23).

POST /api/tor                    -> submit a ToR form (create/update or review)
GET  /api/tor/<group_uuid>       -> the stored ToR form JSON for a ToR/group UUID
POST /api/tor/check-duplicates   -> embedding-similarity pre-check, read-only
"""

from flask import request
from flask_restx import Namespace, Resource

from app.auth import get_current_user, require_role
from app.db_schema import Role
from app.services import tor_service


def register(api, M) -> None:
    ns = Namespace("tor", path="/tor", description="Terms of Reference form")

    @ns.route("")
    class TorCollection(Resource):
        @ns.doc("submit_tor")
        @ns.expect(M["tor_form"], validate=False)
        @ns.response(201, "Group created")
        @ns.response(400, "Validation failed")
        @require_role(Role.STAFF, Role.SUPER_USER)
        def post(self):
            """Validate and persist a submitted ToR form (T18BBANANA-23).

            Acceptance criteria:
              - Validate + normalise the transport DTO into person/membership/
                group/relationship records (match-or-create persons by
                uuid->zID->email) inside one transaction.
              - Strip server-owned provenance/audit fields; re-validate URL
                schemes; enforce free-text length limits.
              - Every valid submission creates the group and a matching
                ``tor_submissions`` row (201). A superuser bypasses review:
                group ``Active``, submission ``approved``. Everyone else gets
                a ``Proposed`` group and a ``pending_review`` submission.
                Return 400 on validation failure.
            """
            payload = request.get_json(silent=True) or {}
            body, status = tor_service.submit_tor_form(payload, get_current_user())
            return body, status

    @ns.route("/check-duplicates")
    class TorDuplicateCheck(Resource):
        @ns.doc("check_tor_duplicates")
        @ns.expect(M["tor_duplicate_check_request"], validate=False)
        @ns.response(200, "Possible duplicate groups", M["tor_duplicate_check_response"])
        @ns.response(400, "Validation failed")
        @require_role(Role.STAFF, Role.SUPER_USER)
        def post(self):
            """Embed a draft ToR and return existing groups it resembles.

            Read-only: nothing is persisted. The frontend calls this before the
            real submission so the user can see a duplicate warning and decide
            whether to proceed; ``POST /api/tor`` also runs this same check and
            returns it as ``possible_duplicates`` alongside the created group.
            """
            payload = request.get_json(silent=True) or {}
            body, status = tor_service.check_duplicates(payload)
            return body, status

    @ns.route("/<string:group_uuid>")
    @ns.param("group_uuid", "Public UUID of the group to edit")
    class TorItem(Resource):
        @ns.doc("get_tor")
        @ns.response(200, "Editable ToR form for the group", M["tor_form"])
        @ns.response(401, "Authentication required")
        @ns.response(404, "Group not found")
        @require_role(Role.STAFF, Role.SUPER_USER)
        def get(self, group_uuid: str):
            """Return the editable ToR form JSON from ``tor_submissions``.

            Acceptance criteria:
              - 200 with the stored ``tor_form`` DTO JSON.
              - 404 when no ToR submission matches the UUID.
            """
            form = tor_service.get_tor_form(group_uuid)
            if form is None:
                ns.abort(404, "ToR submission not found")
            return form

    api.add_namespace(ns)
