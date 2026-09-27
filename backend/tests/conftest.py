import hashlib
import re

import numpy as np
import pytest

from app import create_app
from app.config import TestConfig
from app.db_schema import Role, Users
from app.extensions import db
from app.services import embedding_service

_FAKE_EMBEDDING_DIM = 32


def _fake_embed(text: str) -> list[float]:
    """Deterministic bag-of-words stand-in for the real sentence-transformers model.

    Keeps the whole test suite off torch/network: cosine similarity still
    tracks word overlap (similar text -> high score, unrelated text -> low),
    which is all ``embedding_service.find_similar_groups`` needs to be
    exercised meaningfully.
    """
    vec = np.zeros(_FAKE_EMBEDDING_DIM)
    for word in re.findall(r"\w+", text.lower()):
        idx = int(hashlib.md5(word.encode()).hexdigest(), 16) % _FAKE_EMBEDDING_DIM
        vec[idx] += 1.0
    norm = np.linalg.norm(vec)
    return (vec / norm if norm > 0 else vec).tolist()


@pytest.fixture(autouse=True)
def _stub_embeddings(monkeypatch):
    monkeypatch.setattr(embedding_service, "embed_text", _fake_embed)


@pytest.fixture
def app():
    return create_app(TestConfig)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def admin_headers(app):
    """Seed an ADMIN account and return the dev auth headers that resolve to it.

    ``app.auth.get_current_user`` requires *both* ``X-User-Email`` and
    ``X-Token`` (matching ``users.temp_token``) to resolve a caller. A
    privileged caller takes the 201 create path on POST /api/tor and sees the
    full ``person_details_superuser`` view on GET /api/person.
    """
    email = "admin@unsw.edu.au"
    token = "test-token-superuser"
    with app.app_context():
        db.session.add(
            Users(
                id=1,
                email=email,
                display_name="Test Admin",
                password="superuser-test1",
                user_role=Role.SUPER_USER,
                temp_token=token,
            )
        )
        db.session.commit()
    return {"X-User-Email": email, "X-Token": token}


@pytest.fixture
def staff_headers(app):
    """Seed a STAFF account and return its dev auth headers (for 401/403 checks)."""
    email = "staff@unsw.edu.au"
    token = "test-token-staff"
    with app.app_context():
        db.session.add(
            Users(
                id=2,
                email=email,
                display_name="Test Staff",
                password="staff-test1",
                user_role=Role.STAFF,
                temp_token=token,
            )
        )
        db.session.commit()
    return {"X-User-Email": email, "X-Token": token}


@pytest.fixture
def app_context(app):
    """Push an app context so tests can use db.session / Model.query directly."""
    with app.app_context():
        yield


@pytest.fixture
def session(app_context):
    """The SQLAlchemy session, for tests that insert/query rows directly."""
    return db.session
