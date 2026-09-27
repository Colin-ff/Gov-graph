"""Tests for self-registration (POST /api/register) and the admin review queue.

Staff accounts are created immediately; SUPER_USER requests are queued as
``admin_registration_requests`` rows for a superuser to approve or reject.
"""

from app.db_schema import AdminRegistrationStatus, Role, Users
from app.extensions import db

STAFF_PAYLOAD = {
    "email": "new.staff@unsw.edu.au",
    "displayName": "New Staff",
    "password": "staff-pass",
    "userRole": "STAFF",
}
ADMIN_PAYLOAD = {
    "email": "new.admin@unsw.edu.au",
    "displayName": "New Admin",
    "password": "admin-pass",
    "userRole": "SUPER_USER",
}


def _register(client, payload, **overrides):
    return client.post("/api/register", json={**payload, **overrides})


def test_register_staff_creates_active_account(app, client):
    resp = _register(client, STAFF_PAYLOAD)

    assert resp.status_code == 201, resp.get_data(as_text=True)
    body = resp.get_json()
    assert body["email"] == "new.staff@unsw.edu.au"
    assert body["userRole"] == "STAFF"
    assert body["token"]
    # The password must never be echoed back to the client.
    assert "password" not in body

    with app.app_context():
        user = Users.query.filter_by(email="new.staff@unsw.edu.au").one()
        assert user.is_active is True
        # Stored hashed, never in plaintext.
        assert user.password != STAFF_PAYLOAD["password"]


def test_registered_staff_can_log_in(client):
    _register(client, STAFF_PAYLOAD)

    resp = client.post(
        "/api/auth/login",
        json={"email": STAFF_PAYLOAD["email"], "password": STAFF_PAYLOAD["password"]},
    )

    assert resp.status_code == 200, resp.get_data(as_text=True)


def test_register_then_login_is_case_insensitive(client):
    """Registration lower-cases the email, so login must normalise it too.

    Otherwise anyone signing up with a capitalised address is locked out of the
    account they just created.
    """
    _register(client, STAFF_PAYLOAD, email="New.Staff@UNSW.edu.au")

    resp = client.post(
        "/api/auth/login",
        json={"email": "New.Staff@UNSW.edu.au", "password": STAFF_PAYLOAD["password"]},
    )

    assert resp.status_code == 200, resp.get_data(as_text=True)
    assert resp.get_json()["email"] == "new.staff@unsw.edu.au"


def test_registered_token_authenticates_protected_endpoint(client):
    """The token handed back by registration should satisfy the auth guard."""
    body = _register(client, STAFF_PAYLOAD).get_json()

    headers = {"X-User-Email": body["email"], "X-Token": body["token"]}
    # Empty body -> reaches validation (400), proving auth passed (not 401).
    resp = client.post("/api/tor", json={}, headers=headers)
    assert resp.status_code == 400


def test_register_duplicate_email_is_rejected(client):
    _register(client, STAFF_PAYLOAD)

    resp = _register(client, STAFF_PAYLOAD)

    assert resp.status_code == 400
    assert "email" in resp.get_json()["details"]


def test_register_rejects_invalid_payloads(client):
    cases = {
        "email": {"email": "not-an-email"},
        "displayName": {"displayName": "  "},
        "password": {"password": "12345"},
        "userRole": {"userRole": "WIZARD"},
    }
    for field, override in cases.items():
        resp = _register(client, STAFF_PAYLOAD, **override)
        assert resp.status_code == 400, f"{field}: {resp.get_data(as_text=True)}"
        assert field in resp.get_json()["details"]


def test_register_admin_is_queued_not_created(app, client):
    resp = _register(client, ADMIN_PAYLOAD)

    assert resp.status_code == 202, resp.get_data(as_text=True)
    body = resp.get_json()
    assert body["status"] == "pending_review"
    assert body["request"]["status"] == "pending_review"
    assert body["request"]["requestedRole"] == "SUPER_USER"

    with app.app_context():
        # No account exists until a superuser approves it.
        assert Users.query.filter_by(email=ADMIN_PAYLOAD["email"]).first() is None


def test_pending_admin_cannot_log_in(client):
    _register(client, ADMIN_PAYLOAD)

    resp = client.post(
        "/api/auth/login",
        json={"email": ADMIN_PAYLOAD["email"], "password": ADMIN_PAYLOAD["password"]},
    )

    assert resp.status_code == 401


def test_duplicate_admin_request_is_rejected(client):
    _register(client, ADMIN_PAYLOAD)

    resp = _register(client, ADMIN_PAYLOAD)

    assert resp.status_code == 400
    assert "email" in resp.get_json()["details"]


def test_admin_registration_queue_requires_superuser(client, staff_headers):
    assert client.get("/api/admin-registrations").status_code == 401
    assert client.get("/api/admin-registrations", headers=staff_headers).status_code == 403


def test_approve_admin_registration_creates_account(app, client, admin_headers):
    request_id = _register(client, ADMIN_PAYLOAD).get_json()["request"]["id"]

    resp = client.post(f"/api/admin-registrations/{request_id}/approve", headers=admin_headers)

    assert resp.status_code == 200, resp.get_data(as_text=True)
    body = resp.get_json()
    assert body["status"] == "approved"
    assert body["reviewedBy"] == admin_headers["X-User-Email"]

    with app.app_context():
        user = Users.query.filter_by(email=ADMIN_PAYLOAD["email"]).one()
        assert user.user_role == Role.SUPER_USER
        assert user.is_active is True

    # The approved admin can now log in with the password they registered with.
    login = client.post(
        "/api/auth/login",
        json={"email": ADMIN_PAYLOAD["email"], "password": ADMIN_PAYLOAD["password"]},
    )
    assert login.status_code == 200, login.get_data(as_text=True)
    assert login.get_json()["userRole"] == "SUPER_USER"


def test_reject_admin_registration_requires_a_comment(client, admin_headers):
    request_id = _register(client, ADMIN_PAYLOAD).get_json()["request"]["id"]

    resp = client.post(
        f"/api/admin-registrations/{request_id}/reject",
        json={"adminComment": "   "},
        headers=admin_headers,
    )

    assert resp.status_code == 400
    assert "adminComment" in resp.get_json()["details"]


def test_reject_admin_registration_records_reason(app, client, admin_headers):
    request_id = _register(client, ADMIN_PAYLOAD).get_json()["request"]["id"]

    resp = client.post(
        f"/api/admin-registrations/{request_id}/reject",
        json={"adminComment": "Not a governance owner."},
        headers=admin_headers,
    )

    assert resp.status_code == 200, resp.get_data(as_text=True)
    body = resp.get_json()
    assert body["status"] == "rejected"
    assert body["adminComment"] == "Not a governance owner."

    with app.app_context():
        assert Users.query.filter_by(email=ADMIN_PAYLOAD["email"]).first() is None


def test_reviewed_request_cannot_be_reviewed_again(client, admin_headers):
    request_id = _register(client, ADMIN_PAYLOAD).get_json()["request"]["id"]
    client.post(f"/api/admin-registrations/{request_id}/approve", headers=admin_headers)

    again = client.post(f"/api/admin-registrations/{request_id}/approve", headers=admin_headers)
    rejected = client.post(
        f"/api/admin-registrations/{request_id}/reject",
        json={"adminComment": "changed my mind"},
        headers=admin_headers,
    )

    assert again.status_code == 409
    assert rejected.status_code == 409


def test_unknown_request_id_is_404(client, admin_headers):
    resp = client.post("/api/admin-registrations/999/approve", headers=admin_headers)

    assert resp.status_code == 404


def test_queue_scopes_split_pending_and_history(client, admin_headers):
    pending_id = _register(client, ADMIN_PAYLOAD).get_json()["request"]["id"]
    other_id = _register(client, ADMIN_PAYLOAD, email="second.admin@unsw.edu.au").get_json()[
        "request"
    ]["id"]
    client.post(f"/api/admin-registrations/{other_id}/approve", headers=admin_headers)

    pending = client.get(
        "/api/admin-registrations?scope=pending", headers=admin_headers
    ).get_json()["requests"]
    history = client.get(
        "/api/admin-registrations?scope=history", headers=admin_headers
    ).get_json()["requests"]

    assert [r["id"] for r in pending] == [pending_id]
    assert [r["id"] for r in history] == [other_id]


def test_unknown_scope_is_rejected(client, admin_headers):
    resp = client.get("/api/admin-registrations?scope=nonsense", headers=admin_headers)

    assert resp.status_code == 400
    assert "scope" in resp.get_json()["details"]


def test_inactive_account_cannot_log_in(app, client):
    _register(client, STAFF_PAYLOAD)
    with app.app_context():
        user = Users.query.filter_by(email=STAFF_PAYLOAD["email"]).one()
        user.is_active = False
        db.session.commit()

    resp = client.post(
        "/api/auth/login",
        json={"email": STAFF_PAYLOAD["email"], "password": STAFF_PAYLOAD["password"]},
    )

    assert resp.status_code == 401


def test_pending_request_does_not_leak_password_hash(client):
    body = _register(client, ADMIN_PAYLOAD).get_json()

    assert "password" not in body["request"]
    assert AdminRegistrationStatus(body["request"]["status"]) is (
        AdminRegistrationStatus.PENDING_REVIEW
    )
