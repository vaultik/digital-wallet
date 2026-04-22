# app/models/user.py
import uuid
from datetime import datetime as dt

from sqlalchemy import DateTime, UUID, func
from sqlalchemy.orm import (
    DeclarativeBase, Mapped,
    declared_attr, mapped_column,
)


class Base(DeclarativeBase):
    """Base class for all models."""

    @declared_attr
    def __tablename__(self) -> str:
        """Generates a table name from the class name."""
        return self.__name__.lower()

    def __repr__(self) -> str:
        return f'{type(self).__name__} id={self.id}'


class IdTimeMixin:
    """Mixin with timestamps and ID."""

    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        primary_key=True,
        default=uuid.uuid4
    )
    created_at: Mapped[dt] = mapped_column(
        DateTime(timezone=True),
        index=True,
        server_default=func.timezone('utc', func.now())
    )
    updated_at: Mapped[dt] = mapped_column(
        DateTime(timezone=True),
        index=True,
        server_default=func.timezone('utc', func.now()),
        onupdate=func.now()
    )
