"""Submitted ToR form JSON moving through the review lifecycle.

A row here is the *submission*, not the group. It carries the form JSON through
``draft -> pending_review -> approved | rejected`` and keeps the audit trail
(who submitted, who reviewed, why it was rejected) that ``governance_groups``
deliberately does not hold.
"""

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


class TorSubmissionStatus(enum.Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class TorSubmission(db.Model):
    __tablename__ = "tor_submissions"

    uuid: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # The group this submission maps to, once it has produced one. Deliberately
    # a separate column rather than reusing the PK: a submission may *adopt* a
    # Proposed group whose uuid was minted earlier by another group's ToR, so
    # submission.uuid == group.uuid cannot be relied on. Null while a draft,
    # because a draft never touches the graph.
    group_uuid: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)

    # Nullable because a draft may be saved before the user has typed a name.
    group_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Identity is the submitter's email rather than a uuid: ``users`` has no
    # uuid column and no link to ``persons``, and email is already unique,
    # indexed, and carried on the session. Mirrors the ``viewer_email`` scoping
    # convention in ``group_service``. Tradeoff: changing a user's email would
    # orphan their submissions (there is no change-email feature today).
    submitted_by_email: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)

    status: Mapped[TorSubmissionStatus] = mapped_column(
        default=TorSubmissionStatus.DRAFT,
        server_default=TorSubmissionStatus.DRAFT.name,
    )
    form_json_data: Mapped[Any] = mapped_column(JSON, nullable=False)

    # Review outcome. ``admin_comment`` is required on reject (enforced at the
    # route) so a submitter is never left without a reason.
    admin_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Three distinct timestamps: a draft has been created but not submitted, so
    # "when was this submitted" cannot be derived from created_at.
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def to_summary_dict(self) -> dict:
        """Everything except the form JSON — what list endpoints return.

        The form blob is many KB per row; returning it for a whole registry
        listing is a real payload problem.
        """
        return {
            "uuid": self.uuid,
            "group_uuid": self.group_uuid,
            "group_name": self.group_name,
            "status": self.status.value,
            "submitted_by_email": self.submitted_by_email,
            "admin_comment": self.admin_comment,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
        }

    def to_dict(self) -> dict:
        return {**self.to_summary_dict(), "form_json_data": self.form_json_data}
