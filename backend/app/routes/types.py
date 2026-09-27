"""Configurable ToR type/role/relation endpoints.

  GET  /api/tor/entity_types          -> group entity types
  POST /api/tor/entity_types          -> add a group entity type
  GET  /api/tor/member_roles          -> member role types
  POST /api/tor/member_roles          -> add a member role type
  GET  /api/tor/group_relation_types  -> group-to-group relation types

The POST paths back the ToR form's "create a new type" dialogs: a submitter who
needs a type nobody has used before adds it once and every later form can pick
it. Relation types are deliberately read-only — the registry models exactly one
relation (``Report to``).
"""

from flask import request
from flask_restx import Namespace, Resource

from app.auth import require_role
from app.db_schema import Role
from app.extensions import db
from app.services import type_service


def register(api, M) -> None:
    ns = Namespace("tor-types", path="/tor", description="ToR configurable types")

    def _create_type(create, listing):
        """Shared POST body handling for the two creatable type tables."""
        payload = request.get_json(silent=True) or {}
        type_name = payload.get("type_name")
        if not isinstance(type_name, str) or not type_name.strip():
            return {"error": "Validation failed", "details": {"type_name": "Required."}}, 400

        try:
            create(type_name, payload.get("description") or None)
            db.session.commit()
        except ValueError as exc:
            db.session.rollback()
            return {"error": "Validation failed", "details": {"type_name": str(exc)}}, 400
        except Exception:
            db.session.rollback()
            raise

        return listing(), 201

    @ns.route("/entity_types")
    class EntityTypes(Resource):
        @ns.doc("list_entity_types")
        @ns.response(200, "Entity types", M["entity_types_list"])
        @ns.response(401, "Authentication required")
        @require_role(Role.STAFF, Role.SUPER_USER)
        def get(self):
            """List group entity types for filling a ToR."""
            return type_service.list_entity_types()

        @ns.doc("create_entity_type")
        @ns.response(201, "Entity types after the addition", M["entity_types_list"])
        @ns.response(400, "Validation failed")
        @ns.response(401, "Authentication required")
        @require_role(Role.STAFF, Role.SUPER_USER)
        def post(self):
            """Add a group entity type, returning the refreshed list.

            Idempotent by name: submitting an existing type is a no-op rather
            than an error, so a racing second submitter is not punished.
            """
            return _create_type(
                type_service.get_or_create_group_type,
                type_service.list_entity_types,
            )

    @ns.route("/member_roles")
    class MemberRoles(Resource):
        @ns.doc("list_member_roles")
        @ns.response(200, "Member role types", M["member_roles_list"])
        @ns.response(401, "Authentication required")
        @require_role(Role.STAFF, Role.SUPER_USER)
        def get(self):
            """List member role types for filling a ToR."""
            return type_service.list_member_roles()

        @ns.doc("create_member_role")
        @ns.response(201, "Member roles after the addition", M["member_roles_list"])
        @ns.response(400, "Validation failed")
        @ns.response(401, "Authentication required")
        @require_role(Role.STAFF, Role.SUPER_USER)
        def post(self):
            """Add a member role type, returning the refreshed list."""
            return _create_type(
                type_service.get_or_create_member_role_type,
                type_service.list_member_roles,
            )

    @ns.route("/group_relation_types")
    class GroupRelationTypes(Resource):
        @ns.doc("list_group_relation_types")
        @ns.response(200, "Group relation types", M["relation_types_list"])
        @ns.response(401, "Authentication required")
        @require_role(Role.STAFF, Role.SUPER_USER)
        def get(self):
            """List group-to-group relation types for filling a ToR."""
            return type_service.list_relation_types()

    api.add_namespace(ns)
