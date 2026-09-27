"""Self-declared group-to-group relationships and configurable relation types."""

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db

# The one relation the registry models. A ``GroupRelationship`` row always means
# ``source reports to target`` — i.e. the *target* governs the *source*.
# Analytics, the graph service and the ToR write path all key off this exact
# string, so it lives here rather than being re-typed at each call site.
REPORT_TO_TYPE_NAME = "Report to"


class RelationshipType(db.Model):
    """Configurable relationship type.

    Only ``REPORT_TO_TYPE_NAME`` is seeded and created in practice; the table
    stays configurable so a later sprint can reintroduce other relation kinds
    without a migration.
    """

    __tablename__ = "relationship_types"

    id: Mapped[int] = mapped_column(primary_key=True)
    type_name: Mapped[str] = mapped_column(String(120), unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    is_directed: Mapped[bool] = mapped_column(default=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "typeName": self.type_name,
            "description": self.description,
            "isDirected": self.is_directed,
        }


class GroupRelationship(db.Model):
    __tablename__ = "group_relationships"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_group_id: Mapped[int] = mapped_column(ForeignKey("governance_groups.id"))
    target_group_id: Mapped[int] = mapped_column(ForeignKey("governance_groups.id"))
    relationship_type_id: Mapped[int] = mapped_column(ForeignKey("relationship_types.id"))
    description: Mapped[str] = mapped_column(Text, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source_group_id": self.source_group_id,
            "target_group_id": self.target_group_id,
            "relationship_type_id": self.relationship_type_id,
            "description": self.description,
        }
