"""Graph visualisation endpoint (T18BBANANA-25).

GET /api/graph -> nodes + relations for the governance structure visualisation.
"""

from flask_restx import Namespace, Resource

from app.auth import require_role
from app.db_schema import Role
from app.services import graph_service


def register(api, M) -> None:
    ns = Namespace("graph", path="/graph", description="Governance graph visualisation")

    @ns.route("")
    class Graph(Resource):
        @ns.doc("get_graph")
        @ns.response(200, "Nodes and relations for the graph", M["graph"])
        @ns.response(401, "Authentication required")
        @require_role(Role.STAFF, Role.SUPER_USER)
        def get(self):
            """Return all groups as nodes and reporting lines as edges.

            Acceptance criteria:
              - 200 with ``{"nodes": [...], "relations": [...]}``; empty DB yields
                empty lists.
              - Each node is ``{uuid, group_name, status, entity_type}`` so the
                frontend can distinguish registered from proposed groups.
              - Only ``Report to`` relations are returned, each reading
                ``source reports to target``.
            """
            return graph_service.get_graph_data()

    api.add_namespace(ns)
