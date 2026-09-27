"""People who sit on governance groups."""

import uuid

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


class Person(db.Model):
    __tablename__ = "persons"

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(String(36), unique=True, default=lambda: str(uuid.uuid4()))
    first_name: Mapped[str] = mapped_column(String(120))
    last_name: Mapped[str] = mapped_column(String(120))
    gender: Mapped[str] = mapped_column(String(32), nullable=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    phone: Mapped[str] = mapped_column(String(50), nullable=True)
    z_id: Mapped[str] = mapped_column(String(16), unique=True, index=True, nullable=True)

    # these three booleans are mutually exclusive
    is_student: Mapped[bool] = mapped_column(default=False)
    is_external: Mapped[bool] = mapped_column(default=False)
    is_faculty: Mapped[bool] = mapped_column(default=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "uuid": self.uuid,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "gender": self.gender,
            "email": self.email,
            "phone": self.phone,
            "zID": self.z_id,
            "is_student": self.is_student,
            "is_external": self.is_external,
            "is_faculty": self.is_faculty,
        }
