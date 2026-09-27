"""Membership links between people, governance groups, and role types."""

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


class MembershipRoleType(db.Model):
    """Configurable member role type, e.g. Chair, Member, or External Advisor."""

    __tablename__ = "membership_role_types"

    id: Mapped[int] = mapped_column(primary_key=True)
    type_name: Mapped[str] = mapped_column(String(120), unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "typeName": self.type_name,
            "description": self.description,
        }


class Membership(db.Model):
    __tablename__ = "memberships"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("governance_groups.id"))
    person_id: Mapped[int] = mapped_column(ForeignKey("persons.id"))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "group_id": self.group_id,
            "person_id": self.person_id,
        }


class MembershipRole(db.Model):
    """Join table allowing one membership to carry multiple role types."""

    __tablename__ = "membership_roles"

    membership_id: Mapped[int] = mapped_column(
        ForeignKey("memberships.id"), primary_key=True
    )
    role_type_id: Mapped[int] = mapped_column(
        ForeignKey("membership_role_types.id"), primary_key=True
    )

    def to_dict(self) -> dict:
        return {
            "membershipId": self.membership_id,
            "roleTypeId": self.role_type_id,
        }
