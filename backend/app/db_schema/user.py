"""Authentication/authorisation accounts and their single role (US-7, US-9)."""

import enum
from datetime import datetime

from sqlalchemy import String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


class Role(enum.Enum):
    STAFF = "STAFF"
    SUPER_USER = "SUPER_USER"


class Users(db.Model):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(255))
    # Hashed with werkzeug.security.generate_password_hash.
    password: Mapped[str] = mapped_column(String(255))
    # Each account has exactly one role (T18BBANANA-7).
    user_role: Mapped[Role] = mapped_column(default=Role.STAFF)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    # TODO: easy authentication token to identify users.
    #  We assume token is persistent (even it is named temp_token) in sprint 1
    temp_token: Mapped[str] = mapped_column(String(255), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "email": self.email,
            "displayName": self.display_name,
            "userRole": self.user_role.value,
            "token": self.temp_token,
            "isActive": self.is_active,
        }
