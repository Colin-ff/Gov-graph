"""Initial seed data for configurable database tables."""

from werkzeug.security import generate_password_hash

from app.db_schema import (
    REPORT_TO_TYPE_NAME,
    GroupType,
    MembershipRoleType,
    RelationshipType,
    Role,
    Users,
)
from app.extensions import db

GROUP_TYPES = [
    "Committee",
    "Board",
    "Working Group",
    "Advisory Panel",
    "Subcommittee",
    "Taskforces",
]

MEMBER_ROLE_TYPES = ["Chair", "Secretariat", "Member"]

# The registry models exactly one group-to-group relation: who a group reports
# to. Earlier sprints also seeded Subgroup / Work with / Advice, but a graph
# mixing several edge meanings is unreadable without governance context, so the
# ToR form and the visualisation now speak only ``REPORT_TO_TYPE_NAME``.
RELATIONSHIP_TYPES = [
    {"type_name": REPORT_TO_TYPE_NAME, "is_directed": True},
]

# Dev accounts so the ToR form (POST /api/tor requires STAFF/SUPER_USER) is
# usable out of the box. The token is the persistent ``temp_token`` the frontend
# replays as ``X-Token``. Replace with real SSO accounts in a later sprint.
SEED_USERS = [
    {
        "email": "admin@unsw.edu.au",
        "display_name": "GovGraph Admin",
        "password": "admin",
        "user_role": Role.SUPER_USER,
        "temp_token": "dev-token-admin",
    },
    {
        "email": "staff@unsw.edu.au",
        "display_name": "GovGraph Staff",
        "password": "staff",
        "user_role": Role.STAFF,
        "temp_token": "dev-token-staff",
    },
]


def seed_initial_types() -> None:
    """Insert default type-table values if they do not already exist."""
    for type_name in GROUP_TYPES:
        if GroupType.query.filter_by(type_name=type_name).first() is None:
            db.session.add(GroupType(type_name=type_name))

    for type_name in MEMBER_ROLE_TYPES:
        if MembershipRoleType.query.filter_by(type_name=type_name).first() is None:
            db.session.add(MembershipRoleType(type_name=type_name))

    for relationship_type in RELATIONSHIP_TYPES:
        type_name = relationship_type["type_name"]
        if RelationshipType.query.filter_by(type_name=type_name).first() is None:
            db.session.add(RelationshipType(**relationship_type))

    db.session.commit()


def seed_initial_users() -> None:
    """Insert default dev accounts if they do not already exist (by email)."""
    for user in SEED_USERS:
        existing = Users.query.filter_by(email=user["email"]).first()
        password_hash = generate_password_hash(user["password"])
        if existing is None:
            db.session.add(Users(**{**user, "password": password_hash, "is_active": True}))
        else:
            existing.is_active = True
            # Upgrade old local dev rows that were seeded before password hashing.
            if existing.password == user["password"]:
                existing.password = password_hash

    db.session.commit()
