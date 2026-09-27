"""Tests for the login endpoint (POST /api/auth/login)."""

from werkzeug.security import generate_password_hash

from app.db_schema import Role, Users
from app.extensions import db


def _seed_user(app, *, email, password, token, role=Role.STAFF):
    with app.app_context():
        db.session.add(
            Users(
                email=email,
                display_name="Test User",
                password=generate_password_hash(password),
                user_role=role,
                temp_token=token,
            )
        )
        db.session.commit()


def test_login_success_returns_token_and_profile(app, client):
    _seed_user(
        app,
        email="staff@unsw.edu.au",
        password="staff-pass",
        token="tok-staff",
        role=Role.STAFF,
    )

    resp = client.post(
        "/api/auth/login",
        json={"email": "staff@unsw.edu.au", "password": "staff-pass"},
    )

    assert resp.status_code == 200, resp.get_data(as_text=True)
    body = resp.get_json()
    assert body["email"] == "staff@unsw.edu.au"
    assert body["token"] == "tok-staff"
    assert body["userRole"] == "STAFF"
    # The password must never be echoed back to the client.
    assert "password" not in body


def test_login_wrong_password_is_rejected(app, client):
    _seed_user(app, email="a@unsw.edu.au", password="right", token="t")

    resp = client.post(
        "/api/auth/login", json={"email": "a@unsw.edu.au", "password": "wrong"}
    )

    assert resp.status_code == 401


def test_login_unknown_user_is_rejected(client):
    resp = client.post(
        "/api/auth/login", json={"email": "nobody@unsw.edu.au", "password": "x"}
    )

    assert resp.status_code == 401


def test_login_token_authenticates_protected_endpoint(app, client):
    """The token from login should satisfy the POST /api/tor auth guard."""
    _seed_user(
        app,
        email="boss@unsw.edu.au",
        password="boss-pass",
        token="tok-boss",
        role=Role.SUPER_USER,
    )

    login = client.post(
        "/api/auth/login",
        json={"email": "boss@unsw.edu.au", "password": "boss-pass"},
    ).get_json()

    headers = {"X-User-Email": login["email"], "X-Token": login["token"]}
    # Empty body -> reaches validation (400), proving auth passed (not 401).
    resp = client.post("/api/tor", json={}, headers=headers)
    assert resp.status_code == 400
