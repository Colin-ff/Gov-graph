"""Public user registration endpoint."""

from flask import request
from flask_restx import Namespace, Resource

from app.services import register_service


def register(api, M) -> None:
    ns = Namespace("register", path="/register", description="User self-registration")

    @ns.route("")
    class Register(Resource):
        @ns.doc("register_user")
        @ns.expect(M["register_request"], validate=False)
        @ns.response(201, "Staff account registered", M["login_response"])
        @ns.response(202, "Admin registration submitted", M["admin_registration_pending"])
        @ns.response(400, "Validation failed")
        def post(self):
            payload = request.get_json(silent=True) or {}
            body, status = register_service.register_user(payload)
            return body, status

    api.add_namespace(ns)
