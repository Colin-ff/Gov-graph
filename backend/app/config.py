"""Application configuration, loaded from environment variables."""

import os


def _database_url() -> str:
    """Resolve the SQLAlchemy database URL.

    Prefers an explicit DATABASE_URL; otherwise composes one from the
    individual POSTGRES_* variables (the same ones docker-compose uses).
    """
    explicit = os.environ.get("DATABASE_URL")
    if explicit:
        return explicit

    user = os.environ.get("POSTGRES_USER", "govgraph")
    password = os.environ.get("POSTGRES_PASSWORD", "govgraph")
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    name = os.environ.get("POSTGRES_DB", "govgraph")
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}"


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = _database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    CORS_ORIGINS = [
        origin.strip()
        for origin in os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")
        if origin.strip()
    ]
    # Used by the ToR autofill feature (POST /api/tor/autofill) to call Gemini.
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
    # Optional override if the free-tier model lineup changes.
    GEMINI_MODEL = os.environ.get("GEMINI_MODEL")


class TestConfig(Config):
    """In-memory SQLite so tests need no running Postgres."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
