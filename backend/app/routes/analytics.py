"""Governance analytics endpoints.

Read-only insight endpoints over the governance graph, covering the six
analytics themes:
- governance burden,
- effort concentration,
- unusual relations,
- overlapping members,
- diversity,
- chain-of-command intelligence.

All are restricted to SUPER_USER accounts,
matching the superuser-facing analytics dashboard.

The computations live in ``app.analytics``; this layer only validates
inputs (400 for bad query params, 404 for unknown people/groups) and shapes the
response DTOs. The resources map one-to-one to the analytics user stories.
"""

from flask import request
from flask_restx import Namespace, Resource

from app.analytics import (
    get_all_multiple_reporting_line_groups,
    get_all_orphan_groups,
    get_chain_of_command,
    get_gender_distribution_of_a_group,
    get_member_representation_of_a_group,
    get_number_of_governance_groups_under_control,
    get_number_of_governance_hours_of_a_group,
    get_number_of_groups_a_person_belongs,
    get_number_of_shared_members_between_two_groups,
    get_percentage_of_membership_overlapping_relevant_to_group_a,
    get_shared_members_between_two_groups,
    get_top_groups_by_governance_hours,
    get_top_groups_by_under_control_count,
    get_top_people_by_group_count,
    get_top_people_by_meeting_hours,
    get_total_meeting_hours_for_a_person,
    group_exists,
    person_exists,
)
from app.auth import require_role
from app.db_schema import Person, Role


def _parse_positive_int(raw: str | None, default: int | None = None) -> int | None:
    """Parse a query-string integer, returning ``default`` when absent.

    Returns ``None`` for anything that is not a strictly-positive integer so the
    caller can distinguish "invalid" from a valid value.
    """
    if raw is None:
        return default
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def register(api, M) -> None:
    ns = Namespace("analytics", path="/analytics", description="Governance analytics")

    def _require_group(group_uuid: str) -> None:
        """Abort 404 when no governance group has this uuid."""
        if not group_exists(group_uuid):
            ns.abort(404, "Group not found")

    def _two_group_args() -> tuple[str, str]:
        """Read + validate the ``group_a`` / ``group_b`` query params.

        Aborts 400 when either is missing and 404 when either does not resolve.
        """
        group_a = request.args.get("group_a")
        group_b = request.args.get("group_b")
        if not group_a or not group_b:
            ns.abort(400, "Query parameters 'group_a' and 'group_b' are required.")
        for group_uuid in (group_a, group_b):
            if not group_exists(group_uuid):
                ns.abort(404, f"Group not found: {group_uuid}")
        return group_a, group_b

    # ----- Governance burden --------------------------------------------

    @ns.route("/people/<string:person_uuid>/governance-load")
    @ns.param("person_uuid", "Public UUID of the person")
    class PersonGovernanceLoad(Resource):
        @ns.doc("person_governance_load")
        @ns.response(200, "Yearly governance load in meeting hours", M["analytics_person_load"])
        @ns.response(404, "Person not found")
        @require_role(Role.SUPER_USER)
        def get(self, person_uuid: str):
            """Return one person's yearly governance load (total meeting hours)."""
            if not person_exists(person_uuid):
                ns.abort(404, "Person not found")
            return {
                "uuid": person_uuid,
                "meeting_hours": get_total_meeting_hours_for_a_person(person_uuid),
            }

    @ns.route("/people/top-governance-load")
    class TopPeopleByLoad(Resource):
        @ns.doc("top_people_by_governance_load")
        @ns.param("n", "How many people to return (positive integer, default 10)")
        @ns.response(200, "People ranked by yearly meeting hours", M["analytics_top_people"])
        @ns.response(400, "Invalid 'n' query parameter")
        @require_role(Role.SUPER_USER)
        def get(self):
            """Return the top ``n`` people by yearly governance meeting hours."""
            n = _parse_positive_int(request.args.get("n"), default=10)
            if n is None:
                ns.abort(400, "Query parameter 'n' must be a positive integer.")
            return {"people": get_top_people_by_meeting_hours(n)}

    @ns.route("/people/top-group-count")
    class TopPeopleByGroupCount(Resource):
        @ns.doc("top_people_by_group_count")
        @ns.param("n", "How many people to return (positive integer, default 10)")
        @ns.response(200, "People ranked by number of groups", M["analytics_top_people"])
        @ns.response(400, "Invalid 'n' query parameter")
        @require_role(Role.SUPER_USER)
        def get(self):
            """Return the top ``n`` people by number of governance groups they sit on."""
            n = _parse_positive_int(request.args.get("n"), default=10)
            if n is None:
                ns.abort(400, "Query parameter 'n' must be a positive integer.")
            return {"people": get_top_people_by_group_count(n)}

    @ns.route("/people/<string:person_uuid>/group-count")
    @ns.param("person_uuid", "Public UUID of the person")
    class PersonGroupCount(Resource):
        @ns.doc("person_group_count")
        @ns.response(
            200, "Number of groups the person belongs to", M["analytics_person_group_count"]
        )
        @ns.response(404, "Person not found")
        @require_role(Role.SUPER_USER)
        def get(self, person_uuid: str):
            """Return how many governance groups a person belongs to."""
            if not person_exists(person_uuid):
                ns.abort(404, "Person not found")
            return {
                "uuid": person_uuid,
                "group_count": get_number_of_groups_a_person_belongs(person_uuid),
            }

    # ----- Governance effort concentration ------------------------------

    @ns.route("/groups/<string:group_uuid>/governed-group-count")
    @ns.param("group_uuid", "Public UUID of the governing group")
    class GroupGovernedCount(Resource):
        @ns.doc("group_governed_count")
        @ns.response(200, "Governance groups this group governs", M["analytics_governed_count"])
        @ns.response(404, "Group not found")
        @require_role(Role.SUPER_USER)
        def get(self, group_uuid: str):
            """Return how many groups report to (are governed by) this group."""
            _require_group(group_uuid)
            return {
                "uuid": group_uuid,
                "governed_group_count": (get_number_of_governance_groups_under_control(group_uuid)),
            }

    @ns.route("/groups/<string:group_uuid>/governance-hours")
    @ns.param("group_uuid", "Public UUID of the group")
    class GroupGovernanceHours(Resource):
        @ns.doc("group_governance_hours")
        @ns.response(200, "Yearly governance hours for this group", M["analytics_group_hours"])
        @ns.response(404, "Group not found")
        @require_role(Role.SUPER_USER)
        def get(self, group_uuid: str):
            """Return the yearly meeting hours this group must dedicate."""
            _require_group(group_uuid)
            return {
                "uuid": group_uuid,
                "governance_hours": get_number_of_governance_hours_of_a_group(group_uuid),
            }

    @ns.route("/groups/top-governed-group-count")
    class TopGroupsByGovernedCount(Resource):
        @ns.doc("top_groups_by_governed_count")
        @ns.param("n", "How many groups to return (positive integer, default 10)")
        @ns.response(200, "Groups ranked by how many groups they govern", M["analytics_top_groups"])
        @ns.response(400, "Invalid 'n' query parameter")
        @require_role(Role.SUPER_USER)
        def get(self):
            """Return the top ``n`` groups by number of groups that report to them."""
            n = _parse_positive_int(request.args.get("n"), default=10)
            if n is None:
                ns.abort(400, "Query parameter 'n' must be a positive integer.")
            return {"groups": get_top_groups_by_under_control_count(n)}

    @ns.route("/groups/top-governance-hours")
    class TopGroupsByGovernanceHours(Resource):
        @ns.doc("top_groups_by_governance_hours")
        @ns.param("n", "How many groups to return (positive integer, default 10)")
        @ns.response(200, "Groups ranked by yearly meeting hours", M["analytics_top_groups"])
        @ns.response(400, "Invalid 'n' query parameter")
        @require_role(Role.SUPER_USER)
        def get(self):
            """Return the top ``n`` groups by yearly governance meeting hours."""
            n = _parse_positive_int(request.args.get("n"), default=10)
            if n is None:
                ns.abort(400, "Query parameter 'n' must be a positive integer.")
            return {"groups": get_top_groups_by_governance_hours(n)}

    # ----- Unusual governance relations ---------------------------------

    @ns.route("/orphan-groups")
    class OrphanGroups(Resource):
        @ns.doc("orphan_groups")
        @ns.response(200, "Groups that report to no other group", M["analytics_orphan_groups"])
        @require_role(Role.SUPER_USER)
        def get(self):
            """Return every group with no outgoing 'Report to' relationship."""
            return {"groups": get_all_orphan_groups()}

    @ns.route("/multiple-reporting-line-groups")
    class MultipleReportingLineGroups(Resource):
        @ns.doc("multiple_reporting_line_groups")
        @ns.response(
            200,
            "Groups with two or more reporting lines",
            M["analytics_multiple_reporting_groups"],
        )
        @require_role(Role.SUPER_USER)
        def get(self):
            """Return groups with two or more outgoing 'Report to' relationships."""
            return {"groups": get_all_multiple_reporting_line_groups()}

    # ----- Inefficient overlapping members ------------------------------

    @ns.route("/overlap/shared-members")
    class SharedMembers(Resource):
        @ns.doc("overlap_shared_members")
        @ns.param("group_a", "Public UUID of the first group")
        @ns.param("group_b", "Public UUID of the second group")
        @ns.response(200, "Members shared by the two groups", M["analytics_shared_members"])
        @ns.response(400, "Missing group_a / group_b query parameter")
        @ns.response(404, "One of the groups was not found")
        @require_role(Role.SUPER_USER)
        def get(self):
            """Return the number of members shared between two groups."""
            group_a, group_b = _two_group_args()
            return {
                "group_a_uuid": group_a,
                "group_b_uuid": group_b,
                "shared_member_count": (
                    get_number_of_shared_members_between_two_groups(group_a, group_b)
                ),
            }

    @ns.route("/overlap/shared-member-list")
    class SharedMemberList(Resource):
        @ns.doc("overlap_shared_member_list")
        @ns.param("group_a", "Public UUID of the first group")
        @ns.param("group_b", "Public UUID of the second group")
        @ns.response(200, "The people shared by the two groups", M["analytics_shared_member_list"])
        @ns.response(400, "Missing group_a / group_b query parameter")
        @ns.response(404, "One of the groups was not found")
        @require_role(Role.SUPER_USER)
        def get(self):
            """Return the people who belong to both groups, resolved to profiles.

            Complements ``/overlap/shared-members`` (which returns only the
            count) by naming each shared member. ``get_shared_members_between_two_groups``
            returns internal person ids, which are resolved to public uuids here.
            """
            group_a, group_b = _two_group_args()
            shared_ids = get_shared_members_between_two_groups(group_a, group_b)
            people = (
                Person.query.filter(Person.id.in_(shared_ids)).order_by(Person.uuid).all()
                if shared_ids
                else []
            )
            return {
                "group_a_uuid": group_a,
                "group_b_uuid": group_b,
                "shared_member_count": len(shared_ids),
                "shared_members": [
                    {
                        "uuid": person.uuid,
                        "first_name": person.first_name,
                        "last_name": person.last_name,
                    }
                    for person in people
                ],
            }

    @ns.route("/overlap/percentage")
    class OverlapPercentage(Resource):
        @ns.doc("overlap_percentage")
        @ns.param("group_a", "Public UUID of the first group")
        @ns.param("group_b", "Public UUID of the second (denominator) group")
        @ns.response(
            200, "Overlap relative to group_b's members", M["analytics_overlap_percentage"]
        )
        @ns.response(400, "Missing group_a / group_b query parameter")
        @ns.response(404, "One of the groups was not found")
        @require_role(Role.SUPER_USER)
        def get(self):
            """Return the membership overlap as a percentage of group_b's members.

            The denominator is the *latter* group (``group_b``): a result of 80
            reads as "80% of group B's members are also in group A".
            """
            group_a, group_b = _two_group_args()
            # The helper divides by its first argument's member count, so pass
            # group_b first to make it the denominator.
            percentage = get_percentage_of_membership_overlapping_relevant_to_group_a(
                group_b, group_a
            )
            shared = get_number_of_shared_members_between_two_groups(group_a, group_b)
            return {
                "group_a_uuid": group_a,
                "group_b_uuid": group_b,
                "shared_member_count": shared,
                "overlap_percentage": percentage,
                "relative_to": "group_b",
                "description": f"{percentage:.1f}% of group B's members are also in group A.",
            }

    # ----- Diversity ----------------------------------------------------

    @ns.route("/groups/<string:group_uuid>/gender-distribution")
    @ns.param("group_uuid", "Public UUID of the group")
    class GroupGenderDistribution(Resource):
        @ns.doc("group_gender_distribution")
        @ns.response(200, "Gender split of the group's members", M["analytics_gender_distribution"])
        @ns.response(404, "Group not found")
        @require_role(Role.SUPER_USER)
        def get(self, group_uuid: str):
            """Return the gender distribution (percentages) of a group's members."""
            _require_group(group_uuid)
            return {
                "uuid": group_uuid,
                "distribution": get_gender_distribution_of_a_group(group_uuid),
            }

    @ns.route("/groups/<string:group_uuid>/member-representation")
    @ns.param("group_uuid", "Public UUID of the group")
    class GroupMemberRepresentation(Resource):
        @ns.doc("group_member_representation")
        @ns.response(
            200,
            "Student / faculty / external representation split",
            M["analytics_member_representation"],
        )
        @ns.response(404, "Group not found")
        @require_role(Role.SUPER_USER)
        def get(self, group_uuid: str):
            """Return the student / faculty / external representation percentages."""
            _require_group(group_uuid)
            return {
                "uuid": group_uuid,
                "representation": get_member_representation_of_a_group(group_uuid),
            }

    # ----- Chain-of-command intelligence --------------------------------

    @ns.route("/chain-of-command")
    class ChainOfCommand(Resource):
        @ns.doc("chain_of_command")
        @ns.param("from", "Public UUID of the first group")
        @ns.param("to", "Public UUID of the second group")
        @ns.response(
            200, "Reporting chain between the groups (or null)", M["analytics_chain_of_command"]
        )
        @ns.response(400, "Missing 'from' / 'to' query parameter")
        @ns.response(404, "One of the groups was not found")
        @require_role(Role.SUPER_USER)
        def get(self):
            """Return the reporting chain linking two groups, or null when none.

            The chain is ordered most-powerful first, e.g. ``[A, C, D, B]`` when
            A governs B through C and D. ``connected`` is False (and ``chain`` is
            null) when neither group reports to the other.
            """
            from_uuid = request.args.get("from")
            to_uuid = request.args.get("to")
            if not from_uuid or not to_uuid:
                ns.abort(400, "Query parameters 'from' and 'to' are required.")
            for group_uuid in (from_uuid, to_uuid):
                if not group_exists(group_uuid):
                    ns.abort(404, f"Group not found: {group_uuid}")

            chain = get_chain_of_command(from_uuid, to_uuid)
            return {
                "from_uuid": from_uuid,
                "to_uuid": to_uuid,
                "connected": chain is not None,
                "chain": chain,
            }

    api.add_namespace(ns)
