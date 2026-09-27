"""Superuser review endpoints for admin account registrations."""

from flask import request
from flask_restx import Namespace, Resource

from app.auth import get_current_user, require_role
from app.db_schema import Role
from app.services import register_service


def register(api, M) -> None:
    ns = Namespace(
        "admin-registrations",
        path="/admin-registrations",
        description="Admin account registration review",
    )

    @ns.route("")
    class AdminRegistrationCollection(Resource):
        @ns.doc("list_admin_registrations")
        @ns.param("scope", "pending | history")
        @ns.response(200, "Admin registration requests", M["admin_registration_list"])
        @require_role(Role.SUPER_USER)
        def get(self):
            body, status = register_service.list_admin_registration_requests(
                request.args.get("scope")
            )
            return body, status

    @ns.route("/<int:request_id>/approve")
    @ns.param("request_id", "Admin registration request id")
    class AdminRegistrationApprove(Resource):
        @ns.doc("approve_admin_registration")
        @ns.response(200, "Approved", M["admin_registration_request"])
        @require_role(Role.SUPER_USER)
        def post(self, request_id: int):
            body, status = register_service.approve_admin_registration(
                request_id, get_current_user()
            )
            return body, status

    @ns.route("/<int:request_id>/reject")
    @ns.param("request_id", "Admin registration request id")
    class AdminRegistrationReject(Resource):
        @ns.doc("reject_admin_registration")
        @ns.expect(M["admin_registration_review_request"], validate=False)
        @ns.response(200, "Rejected", M["admin_registration_request"])
        @require_role(Role.SUPER_USER)
        def post(self, request_id: int):
            payload = request.get_json(silent=True) or {}
            body, status = register_service.reject_admin_registration(
                request_id, get_current_user(), payload.get("adminComment")
            )
            return body, status

    api.add_namespace(ns)
