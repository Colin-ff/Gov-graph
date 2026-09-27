"""Governance groups and their configurable type/reference data."""

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import JSON, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


class GroupStatus(enum.Enum):
    ACTIVE = "Active"
    INACTIVE = "Inactive"
    ARCHIVED = "Archived"
    PROPOSED = "Proposed"


class GroupType(db.Model):
    """Configurable governance group type, e.g. Committee or Working Group."""

    __tablename__ = "group_types"

    id: Mapped[int] = mapped_column(primary_key=True)
    type_name: Mapped[str] = mapped_column(String(120), unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "typeName": self.type_name,
            "description": self.description,
        }


class GovernanceGroup(db.Model):
    __tablename__ = "governance_groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(
        String(36), unique=True, default=lambda: str(uuid.uuid4())
    )
    group_name: Mapped[str] = mapped_column(String(255))
    group_type_id: Mapped[int] = mapped_column(ForeignKey("group_types.id"))
    status: Mapped[GroupStatus] = mapped_column(default=GroupStatus.ACTIVE)
    purpose: Mapped[str] = mapped_column(Text, nullable=True)
    responsibilities: Mapped[str] = mapped_column(Text, nullable=True)
    meeting_frequency_per_year: Mapped[int] = mapped_column(nullable=True)
    meeting_duration_hour: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=True)
    start_date: Mapped[date] = mapped_column(nullable=True)
    review_date: Mapped[date] = mapped_column(nullable=True)

    # Distilled purpose/responsibilities/reporting-line text that was embedded,
    # and the resulting vector — used for duplicate-group detection at ToR
    # submission time. See app/services/embedding_service.py.
    embedding_text: Mapped[str] = mapped_column(Text, nullable=True)
    embedding: Mapped[list[float]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "uuid": self.uuid,
            "group_name": self.group_name,
            "group_type_id": self.group_type_id,
            "status": self.status.value,
            "purpose": self.purpose,
            "responsibilities": self.responsibilities,
            "meeting_frequency_per_year": self.meeting_frequency_per_year,
            "meeting_duration_hour": (
                float(self.meeting_duration_hour)
                if self.meeting_duration_hour is not None
                else None
            ),
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "review_date": self.review_date.isoformat() if self.review_date else None,
            "created_timestamp": self.created_at.isoformat() if self.created_at else None,
            "last_modified_timestamp": (
                self.updated_at.isoformat() if self.updated_at else None
            ),
        }


class GroupReferenceLink(db.Model):
    """Multi-value external/reference links for a governance group."""

    __tablename__ = "group_reference_links"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("governance_groups.id"))
    title: Mapped[str] = mapped_column(String(255))
    url: Mapped[str] = mapped_column(String(1024))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "group_id": self.group_id,
            "title": self.title,
            "url": self.url,
        }
