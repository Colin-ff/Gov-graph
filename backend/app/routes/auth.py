"""Authentication endpoints.

POST /api/auth/login -> verify email + password, return the caller's profile and
persistent token. The frontend stores the token and replays it as ``X-Token``
(with ``X-User-Email``) on subsequent protected calls (see ``app/auth.py``).
"""

from flask import request
from flask_restx import Namespace, Resource

from app.services import auth_service


def register(api, M) -> None:
    ns = Namespace("auth", path="/auth", description="Authentication")

    @ns.route("/login")
    class Login(Resource):
        @ns.doc("login")
        @ns.expect(M["login_request"], validate=False)
        @ns.response(200, "Authenticated", M["login_response"])
        @ns.response(401, "Invalid credentials")
        def post(self):
            """Validate credentials and return the auth profile + token."""
            payload = request.get_json(silent=True) or {}
            result = auth_service.authenticate(
                payload.get("email"), payload.get("password")
            )
            if result is None:
                ns.abort(401, "Invalid email or password")
            return result

    api.add_namespace(ns)
