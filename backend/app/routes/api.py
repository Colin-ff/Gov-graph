"""flask-restx Api bootstrap.

Mounts a single ``Api`` on the ``/api`` blueprint with Swagger UI at
``/api/docs`` (and the spec at ``/api/swagger.json``). All shared swagger models
are registered once, then each namespace module wires its own resources.
"""

from flask import Blueprint
from flask_restx import Api

from app.routes import (
    admin_registrations,
    analytics,
    auth,
    graph,
    groups,
    person,
    register,
    tor,
    tor_autofill,
    tor_submissions,
    types,
)
from app.routes.swagger_models import register_models

api_bp = Blueprint("api", __name__)

api = Api(
    api_bp,
    version="1.0",
    title="GovGraph API",
    description="Governance registry: ToR forms, graph, groups, people, types.",
    doc="/docs",
)

# Register shared swagger models once, then let each namespace add its resources.
_models = register_models(api)
for module in (
    auth,
    register,
    admin_registrations,
    tor,
    tor_autofill,
    tor_submissions,
    types,
    graph,
    groups,
    person,
    analytics,
):
    module.register(api, _models)
