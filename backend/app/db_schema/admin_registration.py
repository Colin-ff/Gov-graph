"""Admin account registration requests awaiting superuser review."""

import enum
from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db_schema.user import Role
from app.extensions import db


class AdminRegistrationStatus(enum.Enum):
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class AdminRegistrationRequest(db.Model):
    __tablename__ = "admin_registration_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), index=True)
    display_name: Mapped[str] = mapped_column(String(255))
    password: Mapped[str] = mapped_column(String(255))
    requested_role: Mapped[Role] = mapped_column(default=Role.SUPER_USER)
    status: Mapped[AdminRegistrationStatus] = mapped_column(
        default=AdminRegistrationStatus.PENDING_REVIEW,
        server_default=AdminRegistrationStatus.PENDING_REVIEW.name,
    )
    admin_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "email": self.email,
            "displayName": self.display_name,
            "requestedRole": self.requested_role.value,
            "status": self.status.value,
            "adminComment": self.admin_comment,
            "reviewedBy": self.reviewed_by,
            "reviewedAt": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
        }
