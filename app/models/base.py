"""Base model with common columns."""

from datetime import datetime

from sqlalchemy import DateTime, Text, TypeDecorator, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class JSONB(TypeDecorator):
    """JSONB that renders as TEXT on SQLite, JSONB on PostgreSQL.

    Usage: replace `from sqlalchemy.dialects.postgresql import JSONB` with
    `from app.models.base import JSONB` in all model files.
    """

    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "sqlite":
            return dialect.type_descriptor(Text())
        if dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import JSONB as PGJSONB

            return dialect.type_descriptor(PGJSONB())
        from sqlalchemy import JSON

        return dialect.type_descriptor(JSON())

    def process_bind_param(self, value, dialect):
        if dialect.name == "sqlite":
            import json

            return json.dumps(value) if value is not None else None
        return value

    def process_result_value(self, value, dialect):
        if dialect.name == "sqlite":
            import json

            return json.loads(value) if isinstance(value, str) else value
        return value


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


class TimestampMixin:
    """Mixin that adds created_at and updated_at columns."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
