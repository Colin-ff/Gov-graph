"""Flask application factory."""

from flask import Flask
from flask_cors import CORS

from app.config import Config
from app.extensions import db
from app.routes import register_blueprints


def create_app(config_object: type[Config] = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_object)

    db.init_app(app)
    CORS(app, origins=app.config["CORS_ORIGINS"])

    # Import schemas so SQLAlchemy is aware of them before create_all().
    from app import db_schema  # noqa: F401

    register_blueprints(app)

    with app.app_context():
        # PoC convenience: auto-create tables. Swap for migrations (Alembic)
        # when the schema stabilises.
        db.create_all()

        from app.db_init_seed import seed_initial_types, seed_initial_users

        seed_initial_types()
        # Tests seed their own accounts (see conftest), so skip dev users there
        # to avoid primary-key/email collisions.
        if not app.config.get("TESTING"):
            seed_initial_users()

    return app
