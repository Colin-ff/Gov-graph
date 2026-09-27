"""Governance group read endpoints (T18BBANANA-24).

GET /api/groups              -> the ``organisation_list`` search DTO.
GET /api/groups/<group_uuid> -> the ``organisation`` DTO, shaped by the viewer.

(The old POST /api/groups + GET /api/groups/<int> skeletons are superseded:
group creation now flows through POST /api/tor, and groups are addressed by their
public UUID.)
"""

from flask import request
from flask_restx import Namespace, Resource

from app.auth import get_current_user, is_privileged_superuser, require_role
from app.db_schema import Role
from app.services import group_service


def register(api, M) -> None:
    ns = Namespace("groups", path="/groups", description="Governance group details")

    @ns.route("")
    class GroupCollection(Resource):
        @ns.doc("list_groups", params={"name": "Case-insensitive substring to search on"})
        @ns.response(200, "Governance groups (search list)", M["organisation_list"])
        @ns.response(401, "Authentication required")
        @require_role(Role.STAFF, Role.SUPER_USER)
        def get(self):
            """Return groups as ``organisation_list`` items.

            Feeds the frontend group search/typeahead controls. Accepts an
            optional ``?name=`` substring filter, and carries ``status`` so the
            ToR form can tell a registered group from a merely proposed one.
            """
            return {"organisations": group_service.list_organisations(request.args.get("name"))}

    @ns.route("/<string:group_uuid>")
    @ns.param("group_uuid", "Public UUID of the governance group")
    class GroupItem(Resource):
        @ns.doc("get_group")
        @ns.response(200, "Organisation details", M["organisation"])
        @ns.response(401, "Authentication required")
        @ns.response(404, "Group not found")
        @require_role(Role.STAFF, Role.SUPER_USER)
        def get(self, group_uuid: str):
            """Return one group's details (members, reporting lines, references).

            Acceptance criteria:
              - 200 with the ``organisation`` DTO when the UUID resolves.
              - 404 when no group matches the UUID.
              - ``status`` is the lower-cased server enum; ``entity_type`` is the
                group's type name; actor UUIDs are omitted.
              - Meeting details are included only for a superuser or a member of
                the group; ``can_view_meetings`` reports which.
            """
            user = get_current_user()
            group = group_service.get_group_detail(
                group_uuid,
                viewer_email=user.email if user else None,
                privileged=is_privileged_superuser(user),
            )
            if group is None:
                ns.abort(404, "Group not found")
            return group

    api.add_namespace(ns)
