"""Shared extension instances, created here to avoid circular imports."""

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """SQLAlchemy 2.0 declarative base.

    Using an explicit ``DeclarativeBase`` (rather than the legacy implicit
    base) lets the models declare columns with ``Mapped[...]`` /
    ``mapped_column(...)``. SQLAlchemy then synthesises a fully typed
    ``__init__`` for each model, so type checkers stop flagging keyword
    arguments and validate the values too.
    """


db = SQLAlchemy(model_class=Base)
