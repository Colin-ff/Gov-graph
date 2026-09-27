"""User registration and admin-account review workflow."""

import re
import uuid
from datetime import datetime, timezone

from werkzeug.security import generate_password_hash

from app.db_schema import (
    AdminRegistrationRequest,
    AdminRegistrationStatus,
    Role,
    Users,
)
from app.extensions import db

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_HISTORY = (AdminRegistrationStatus.APPROVED, AdminRegistrationStatus.REJECTED)


def _auth_profile(user: Users) -> dict:
    return {
        "email": user.email,
        "displayName": user.display_name,
        "userRole": user.user_role.value,
        "token": user.temp_token,
    }


def _parse_role(value: str | None) -> Role | None:
    if value == Role.STAFF.value:
        return Role.STAFF
    if value == Role.SUPER_USER.value:
        return Role.SUPER_USER
    return None


def _validate_registration(payload: dict) -> tuple[dict[str, str], dict]:
    cleaned = {
        "email": (payload.get("email") or "").strip().lower(),
        "display_name": (payload.get("displayName") or payload.get("display_name") or "").strip(),
        "password": payload.get("password") or "",
        "role": _parse_role(payload.get("userRole") or payload.get("user_role")),
    }
    errors: dict[str, str] = {}

    if not cleaned["email"]:
        errors["email"] = "Email is required."
    elif not _EMAIL_RE.match(cleaned["email"]):
        errors["email"] = "Must be a valid email address."

    if not cleaned["display_name"]:
        errors["displayName"] = "Display name is required."

    if not cleaned["password"]:
        errors["password"] = "Password is required."
    elif len(cleaned["password"]) < 6:
        errors["password"] = "Password must be at least 6 characters."

    if cleaned["role"] is None:
        errors["userRole"] = "Must be STAFF or SUPER_USER."

    return errors, cleaned


def _pending_admin_request(email: str) -> AdminRegistrationRequest | None:
    return AdminRegistrationRequest.query.filter_by(
        email=email,
        status=AdminRegistrationStatus.PENDING_REVIEW,
    ).first()


def register_user(payload: dict) -> tuple[dict, int]:
    """Register staff immediately; queue admin accounts for superuser review."""
    errors, cleaned = _validate_registration(payload)
    if errors:
        return {"error": "Validation failed", "details": errors}, 400

    email = cleaned["email"]
    if Users.query.filter_by(email=email).first() is not None:
        return {
            "error": "Validation failed",
            "details": {"email": "An account with this email already exists."},
        }, 400

    if cleaned["role"] == Role.SUPER_USER:
        if _pending_admin_request(email) is not None:
            return {
                "error": "Validation failed",
                "details": {"email": "An admin registration is already awaiting review."},
            }, 400

        request_row = AdminRegistrationRequest(
            email=email,
            display_name=cleaned["display_name"],
            password=generate_password_hash(cleaned["password"]),
            requested_role=Role.SUPER_USER,
            status=AdminRegistrationStatus.PENDING_REVIEW,
        )
        db.session.add(request_row)
        db.session.commit()
        return {
            "status": "pending_review",
            "message": "Admin registration submitted for review.",
            "request": request_row.to_dict(),
        }, 202

    user = Users(
        email=email,
        display_name=cleaned["display_name"],
        password=generate_password_hash(cleaned["password"]),
        user_role=Role.STAFF,
        is_active=True,
        temp_token=str(uuid.uuid4()),
    )
    db.session.add(user)
    db.session.commit()
    return _auth_profile(user), 201


def list_admin_registration_requests(scope: str | None) -> tuple[dict, int]:
    """Return pending or resolved admin registration requests."""
    scope = scope or "pending"
    if scope == "pending":
        query = AdminRegistrationRequest.query.filter_by(
            status=AdminRegistrationStatus.PENDING_REVIEW
        )
    elif scope == "history":
        query = AdminRegistrationRequest.query.filter(
            AdminRegistrationRequest.status.in_(_HISTORY)
        )
    else:
        return {
            "error": "Validation failed",
            "details": {"scope": "Must be one of: pending, history."},
        }, 400

    rows = query.order_by(AdminRegistrationRequest.updated_at.desc()).all()
    return {"requests": [row.to_dict() for row in rows]}, 200


def approve_admin_registration(request_id: int, reviewer: Users) -> tuple[dict, int]:
    """Approve a pending admin registration and create the active account."""
    request_row = db.session.get(AdminRegistrationRequest, request_id)
    if request_row is None:
        return {"error": "Admin registration request not found"}, 404
    if request_row.status != AdminRegistrationStatus.PENDING_REVIEW:
        return {"error": "Only pending admin registrations can be approved."}, 409
    if Users.query.filter_by(email=request_row.email).first() is not None:
        return {
            "error": "Validation failed",
            "details": {"email": "An account with this email already exists."},
        }, 400

    user = Users(
        email=request_row.email,
        display_name=request_row.display_name,
        password=request_row.password,
        user_role=request_row.requested_role,
        is_active=True,
        temp_token=str(uuid.uuid4()),
    )
    request_row.status = AdminRegistrationStatus.APPROVED
    request_row.reviewed_by = reviewer.email
    request_row.reviewed_at = datetime.now(timezone.utc)
    request_row.admin_comment = None
    db.session.add(user)
    db.session.commit()
    return request_row.to_dict(), 200


def reject_admin_registration(
    request_id: int, reviewer: Users, admin_comment: str | None
) -> tuple[dict, int]:
    """Reject a pending admin registration; a reviewer comment is required."""
    comment = (admin_comment or "").strip()
    if not comment:
        return {
            "error": "Validation failed",
            "details": {"adminComment": "A rejection reason is required."},
        }, 400

    request_row = db.session.get(AdminRegistrationRequest, request_id)
    if request_row is None:
        return {"error": "Admin registration request not found"}, 404
    if request_row.status != AdminRegistrationStatus.PENDING_REVIEW:
        return {"error": "Only pending admin registrations can be rejected."}, 409

    request_row.status = AdminRegistrationStatus.REJECTED
    request_row.admin_comment = comment
    request_row.reviewed_by = reviewer.email
    request_row.reviewed_at = datetime.now(timezone.utc)
    db.session.commit()
    return request_row.to_dict(), 200
