"""Blueprint registration."""

from app.routes.api import api_bp
from app.routes.health import health_bp


def register_blueprints(app) -> None:
    app.register_blueprint(health_bp)
    # flask-restx Api (Swagger UI at /api/docs) — serves /api/tor, /api/graph,
    # /api/groups, /api/person and the configurable type endpoints.
    app.register_blueprint(api_bp, url_prefix="/api")
