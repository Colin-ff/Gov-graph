"""Person read endpoint (T18BBANANA-41).

GET /api/person/<person_uuid> -> person profile, shaped by the caller's authority:
  - SUPER_USER / ADMIN  -> person_details_superuser (full contact details)
  - everyone else       -> person_public_reference (minimal)
"""

from flask_restx import Namespace, Resource

from app.auth import get_current_user, is_privileged_superuser, require_role
from app.db_schema import Role
from app.services import person_service


def register(api, M) -> None:
    ns = Namespace("person", path="/person", description="Person profiles")

    @ns.route("")
    class PersonCollection(Resource):
        @ns.doc("list_people")
        @ns.response(200, "All people (search list)", M["person_list"])
        @ns.response(401, "Authentication required")
        @require_role(Role.STAFF, Role.SUPER_USER)
        def get(self):
            """Return every person as a ``person_list`` item.

            Feeds the frontend person search/typeahead controls. Requires an
            authenticated caller (any role) — enumerating everyone is more
            sensitive than a single lookup — but returns only uuid + name.
            """
            return {"people": person_service.list_people()}

    @ns.route("/<string:person_uuid>")
    @ns.param("person_uuid", "Public UUID of the person")
    class PersonItem(Resource):
        @ns.doc("get_person")
        @ns.response(200, "Public reference (default view)", M["person_public"])
        @ns.response(200, "Superuser details (privileged view)", M["person_superuser"])
        @ns.response(401, "Authentication required")
        @ns.response(404, "Person not found")
        @require_role(Role.STAFF, Role.SUPER_USER)
        def get(self, person_uuid: str):
            """Return one person and the groups they sit on.

            Acceptance criteria:
              - Privileged caller (SUPER_USER/ADMIN, resolved via the auth seam)
                receives ``person_details_superuser`` (gender, is_student, email,
                phone, zID + affiliated groups).
              - Any other caller receives ``person_public_reference`` (name +
                affiliated groups only).
              - 404 when no person matches the UUID.
              - ``affiliated_groups[]`` carries ``{group_uuid, group_name, roles}``.
            """
            privileged = is_privileged_superuser(get_current_user())
            person = person_service.get_person_info(person_uuid, privileged)
            if person is None:
                ns.abort(404, "Person not found")
            return person, 200

    api.add_namespace(ns)
